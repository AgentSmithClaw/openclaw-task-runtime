from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
SQL_PATH = ROOT / "sql" / "001_task_control_plane.sql"
RUNTIME_DIR = ROOT / "runtime"
DB_PATH = ROOT / "data" / "runtime.db"
BOARD_PATH = RUNTIME_DIR / "boards" / "WORK-BOARD.md"
ROLLUP_PATH = RUNTIME_DIR / "boards" / "ROLLUP.md"
REGISTRY_PATH = RUNTIME_DIR / "tasks" / "registry.json"

LIFECYCLE_STATES = {
    "queued",
    "claimed",
    "doing",
    "waiting_input",
    "waiting_external",
    "blocked",
    "done",
    "failed",
}

PHASES = {"intake", "spec", "delivery", "qa", "rollup", "release", "closed"}
OWNERS = {"picard", "spock", "sulu", "laforge", "worf", "uhura"}
EVENT_TO_STATE = {
    "created": "queued",
    "claimed": "claimed",
    "progress": "doing",
    "wait": "waiting_external",
    "wait_input": "waiting_input",
    "block": "blocked",
    "done": "done",
    "fail": "failed",
    "stale": None,
    "handoff": None,
}
ALLOWED_TRANSITIONS = {
    "queued": {"claimed", "doing", "blocked", "failed"},
    "claimed": {"doing", "waiting_input", "waiting_external", "blocked", "done", "failed"},
    "doing": {"claimed", "waiting_input", "waiting_external", "blocked", "done", "failed"},
    "waiting_input": {"claimed", "doing", "blocked", "failed"},
    "waiting_external": {"claimed", "doing", "blocked", "failed"},
    "blocked": {"claimed", "doing", "failed"},
    "done": set(),
    "failed": set(),
}


@dataclass
class TaskCreate:
    title: str
    owner_agent: str
    requested_by: str
    task_type: str = "epic"
    phase: str = "intake"
    priority: str = "P2"
    current_step: str | None = None
    next_action: str | None = None
    parent_id: str | None = None
    root_id: str | None = None
    artifact_root: str | None = None
    source_session_key: str | None = None
    source_message_ref: str | None = None
    done_criteria_json: dict[str, Any] | list[Any] | None = None
    next_run_at: str | None = None
    deadline_at: str | None = None


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dirs() -> None:
    for p in [
        ROOT / "data",
        RUNTIME_DIR / "boards",
        RUNTIME_DIR / "tasks",
        RUNTIME_DIR / "tasks" / "events",
        RUNTIME_DIR / "events",
    ]:
        p.mkdir(parents=True, exist_ok=True)


def json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, indent=2)


class TaskRuntime:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        ensure_dirs()
        self.init_db()
        self.init_files()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        sql = SQL_PATH.read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.executescript(sql)
            conn.commit()

    def init_files(self) -> None:
        if not REGISTRY_PATH.exists():
            REGISTRY_PATH.write_text(json.dumps({"tasks": []}, ensure_ascii=False, indent=2), encoding="utf-8")
        if not BOARD_PATH.exists():
            BOARD_PATH.write_text("# WORK BOARD\n\n暂无任务。\n", encoding="utf-8")
        if not ROLLUP_PATH.exists():
            ROLLUP_PATH.write_text("# ROLLUP\n\n暂无汇总。\n", encoding="utf-8")

    def _validate_create(self, task: TaskCreate) -> None:
        if task.owner_agent not in OWNERS:
            raise ValueError(f"unsupported owner_agent: {task.owner_agent}")
        if task.phase not in PHASES:
            raise ValueError(f"unsupported phase: {task.phase}")
        if not task.title.strip():
            raise ValueError("title is required")
        if not task.requested_by.strip():
            raise ValueError("requested_by is required")

    def create_task(self, task: TaskCreate) -> str:
        self._validate_create(task)
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        root_id = task.root_id or task_id
        ts = now_iso()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                  id, root_id, parent_id, title, type, owner_agent, requested_by,
                  lifecycle_state, freshness_state, phase, priority, current_step,
                  next_action, done_criteria_json, blocker_type, blocker_detail,
                  source_session_key, source_message_ref, artifact_root, latest_artifact_ref,
                  created_at, updated_at, last_progress_at, next_run_at, deadline_at,
                  lease_owner, lease_until, retry_count, max_retries
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    root_id,
                    task.parent_id,
                    task.title,
                    task.task_type,
                    task.owner_agent,
                    task.requested_by,
                    "queued",
                    "fresh",
                    task.phase,
                    task.priority,
                    task.current_step,
                    task.next_action,
                    json_dumps(task.done_criteria_json),
                    None,
                    None,
                    task.source_session_key,
                    task.source_message_ref,
                    task.artifact_root,
                    None,
                    ts,
                    ts,
                    None,
                    task.next_run_at,
                    task.deadline_at,
                    None,
                    None,
                    0,
                    3,
                ),
            )
            conn.commit()
        self.append_event(task_id, actor=task.requested_by, event_type="created", summary=f"Task created: {task.title}")
        self.materialize_views()
        return task_id

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    def list_tasks(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY CASE lifecycle_state WHEN 'doing' THEN 1 WHEN 'claimed' THEN 2 WHEN 'blocked' THEN 3 WHEN 'waiting_input' THEN 4 WHEN 'waiting_external' THEN 5 WHEN 'queued' THEN 6 WHEN 'done' THEN 7 WHEN 'failed' THEN 8 ELSE 9 END, updated_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def list_events(self, task_id: str | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM task_events"
        params: tuple[Any, ...] = ()
        if task_id:
            sql += " WHERE task_id = ?"
            params = (task_id,)
        sql += " ORDER BY at ASC"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def _assert_transition(self, current: str, target: str) -> None:
        if current == target:
            return
        allowed = ALLOWED_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise ValueError(f"invalid lifecycle transition: {current} -> {target}")

    def update_task_state(
        self,
        task_id: str,
        *,
        lifecycle_state: str | None = None,
        freshness_state: str | None = None,
        current_step: str | None = None,
        next_action: str | None = None,
        blocker_type: str | None = None,
        blocker_detail: str | None = None,
        owner_agent: str | None = None,
        phase: str | None = None,
        next_run_at: str | None = None,
        deadline_at: str | None = None,
        last_progress_at: str | None = None,
    ) -> None:
        task = self.get_task(task_id)
        if not task:
            raise KeyError(f"task not found: {task_id}")
        fields: dict[str, Any] = {"updated_at": now_iso()}
        if lifecycle_state is not None:
            if lifecycle_state not in LIFECYCLE_STATES:
                raise ValueError(f"unsupported lifecycle_state: {lifecycle_state}")
            self._assert_transition(task["lifecycle_state"], lifecycle_state)
            fields["lifecycle_state"] = lifecycle_state
        if freshness_state is not None:
            if freshness_state not in {"fresh", "stale"}:
                raise ValueError(f"unsupported freshness_state: {freshness_state}")
            fields["freshness_state"] = freshness_state
        if current_step is not None:
            fields["current_step"] = current_step
        if next_action is not None:
            fields["next_action"] = next_action
        if blocker_type is not None:
            fields["blocker_type"] = blocker_type
        if blocker_detail is not None:
            fields["blocker_detail"] = blocker_detail
        if owner_agent is not None:
            if owner_agent not in OWNERS:
                raise ValueError(f"unsupported owner_agent: {owner_agent}")
            fields["owner_agent"] = owner_agent
        if phase is not None:
            if phase not in PHASES:
                raise ValueError(f"unsupported phase: {phase}")
            fields["phase"] = phase
        if next_run_at is not None:
            fields["next_run_at"] = next_run_at
        if deadline_at is not None:
            fields["deadline_at"] = deadline_at
        if last_progress_at is not None:
            fields["last_progress_at"] = last_progress_at
        assignments = ", ".join(f"{key} = ?" for key in fields)
        params = tuple(fields.values()) + (task_id,)
        with self.connect() as conn:
            conn.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", params)
            conn.commit()

    def append_event(
        self,
        task_id: str,
        *,
        actor: str,
        event_type: str,
        summary: str,
        detail: dict[str, Any] | None = None,
        update_state: bool = True,
    ) -> str:
        task = self.get_task(task_id)
        if not task:
            raise KeyError(f"task not found: {task_id}")
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        ts = now_iso()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO task_events (id, task_id, at, actor, event_type, summary, detail_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (event_id, task_id, ts, actor, event_type, summary, json_dumps(detail)),
            )
            conn.commit()
        if update_state:
            patch = self._state_patch_from_event(event_type, detail or {}, ts)
            if patch:
                self.update_task_state(task_id, **patch)
        self._append_event_jsonl(task_id, event_id, ts, actor, event_type, summary, detail)
        self.materialize_views()
        return event_id

    def _state_patch_from_event(self, event_type: str, detail: dict[str, Any], ts: str) -> dict[str, Any]:
        patch: dict[str, Any] = {}
        lifecycle_state = detail.get("lifecycle_state") or EVENT_TO_STATE.get(event_type)
        if lifecycle_state is not None:
            patch["lifecycle_state"] = lifecycle_state
        if event_type in {"progress", "claimed", "done"}:
            patch["last_progress_at"] = ts
            patch["freshness_state"] = "fresh"
        if event_type == "stale":
            patch["freshness_state"] = "stale"
        if event_type == "block":
            patch["blocker_type"] = detail.get("blocker_type") or "unspecified"
            patch["blocker_detail"] = detail.get("blocker_detail") or detail.get("summary")
        if event_type in {"progress", "claimed", "wait", "wait_input", "block", "done", "fail"}:
            if "current_step" in detail:
                patch["current_step"] = detail["current_step"]
            if "next_action" in detail:
                patch["next_action"] = detail["next_action"]
            if "phase" in detail:
                patch["phase"] = detail["phase"]
            if "owner_agent" in detail:
                patch["owner_agent"] = detail["owner_agent"]
            if "next_run_at" in detail:
                patch["next_run_at"] = detail["next_run_at"]
            if "deadline_at" in detail:
                patch["deadline_at"] = detail["deadline_at"]
        if event_type in {"done", "fail"} and "next_action" not in patch:
            patch["next_action"] = None
        return patch

    def add_artifact(self, task_id: str, *, kind: str, path_or_url: str, created_by: str, metadata: dict[str, Any] | None = None) -> str:
        task = self.get_task(task_id)
        if not task:
            raise KeyError(f"task not found: {task_id}")
        artifact_id = f"art_{uuid.uuid4().hex[:12]}"
        ts = now_iso()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO task_artifacts (id, task_id, kind, path_or_url, metadata_json, created_at, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (artifact_id, task_id, kind, path_or_url, json_dumps(metadata), ts, created_by),
            )
            conn.execute("UPDATE tasks SET latest_artifact_ref = ?, updated_at = ? WHERE id = ?", (path_or_url, ts, task_id))
            conn.commit()
        self.append_event(task_id, actor=created_by, event_type="progress", summary=f"Artifact added: {kind}", detail={"current_step": f"artifact:{kind}", "next_action": task.get("next_action")}, update_state=True)
        return artifact_id

    def task_state_view(self, task_id: str) -> dict[str, Any]:
        task = self.get_task(task_id)
        if not task:
            raise KeyError(f"task not found: {task_id}")
        with self.connect() as conn:
            children = conn.execute("SELECT id, lifecycle_state FROM tasks WHERE parent_id = ? ORDER BY updated_at DESC", (task_id,)).fetchall()
            artifacts = conn.execute("SELECT kind, path_or_url FROM task_artifacts WHERE task_id = ? ORDER BY created_at DESC", (task_id,)).fetchall()
        blockers = []
        if task.get("blocker_type") or task.get("blocker_detail"):
            blockers.append(
                {
                    "kind": task.get("blocker_type") or "unspecified",
                    "summary": task.get("blocker_detail") or "",
                    "owner": task.get("owner_agent") or "picard",
                }
            )
        return {
            "rootTaskId": task["root_id"],
            "title": task["title"],
            "phase": task["phase"],
            "lifecycleState": task["lifecycle_state"],
            "freshnessState": task["freshness_state"],
            "owner": task["owner_agent"],
            "currentStep": task.get("current_step") or "",
            "nextAction": task.get("next_action") or "",
            "lastProgressAt": task.get("last_progress_at"),
            "nextRunAt": task.get("next_run_at"),
            "deadlineAt": task.get("deadline_at"),
            "blockers": blockers,
            "childStates": {row["id"]: row["lifecycle_state"] for row in children},
            "artifacts": [{"kind": row["kind"], "path": row["path_or_url"]} for row in artifacts],
        }

    def sync_registry(self) -> dict[str, Any]:
        tasks = []
        for task in self.list_tasks():
            tasks.append(
                {
                    "id": task["id"],
                    "rootId": task["root_id"],
                    "parentId": task["parent_id"],
                    "title": task["title"],
                    "type": task["type"],
                    "owner": task["owner_agent"],
                    "phase": task["phase"],
                    "lifecycleState": task["lifecycle_state"],
                    "freshnessState": task["freshness_state"],
                    "currentStep": task["current_step"],
                    "nextAction": task["next_action"],
                    "updatedAt": task["updated_at"],
                    "lastProgressAt": task["last_progress_at"],
                    "latestArtifactRef": task["latest_artifact_ref"],
                }
            )
        payload = {"generatedAt": now_iso(), "taskCount": len(tasks), "tasks": tasks}
        REGISTRY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    def render_work_board(self) -> str:
        tasks = self.list_tasks()
        if not tasks:
            content = "# WORK BOARD\n\n暂无任务。\n"
            BOARD_PATH.write_text(content, encoding="utf-8")
            return content
        buckets = {
            "doing": [],
            "claimed": [],
            "blocked": [],
            "waiting_input": [],
            "waiting_external": [],
            "queued": [],
            "done": [],
            "failed": [],
        }
        for task in tasks:
            buckets.setdefault(task["lifecycle_state"], []).append(task)
        lines = ["# WORK BOARD", "", f"生成时间: {now_iso()}", ""]
        title_map = {
            "doing": "进行中",
            "claimed": "已认领",
            "blocked": "阻塞",
            "waiting_input": "待用户输入",
            "waiting_external": "待外部条件",
            "queued": "排队中",
            "done": "已完成",
            "failed": "已失败",
        }
        for state in ["doing", "claimed", "blocked", "waiting_input", "waiting_external", "queued", "done", "failed"]:
            lines.append(f"## {title_map[state]} ({len(buckets.get(state, []))})")
            if not buckets.get(state):
                lines.append("- 无")
                lines.append("")
                continue
            for task in buckets[state]:
                freshness = "stale" if task["freshness_state"] == "stale" else "fresh"
                step = task.get("current_step") or "-"
                action = task.get("next_action") or "-"
                lines.append(
                    f"- `{task['id']}` [{task['owner_agent']}/{task['phase']}/{freshness}] {task['title']} | step: {step} | next: {action}"
                )
            lines.append("")
        content = "\n".join(lines).rstrip() + "\n"
        BOARD_PATH.write_text(content, encoding="utf-8")
        return content

    def render_rollup(self) -> str:
        tasks = self.list_tasks()
        counts: dict[str, int] = {}
        owner_counts: dict[str, int] = {}
        stale_count = 0
        for task in tasks:
            counts[task["lifecycle_state"]] = counts.get(task["lifecycle_state"], 0) + 1
            owner_counts[task["owner_agent"]] = owner_counts.get(task["owner_agent"], 0) + 1
            if task["freshness_state"] == "stale":
                stale_count += 1
        lines = ["# ROLLUP", "", f"生成时间: {now_iso()}", "", "## 概览"]
        lines.append(f"- 任务总数: {len(tasks)}")
        lines.append(f"- stale 任务: {stale_count}")
        for state in ["queued", "claimed", "doing", "waiting_input", "waiting_external", "blocked", "done", "failed"]:
            lines.append(f"- {state}: {counts.get(state, 0)}")
        lines.extend(["", "## Agent 负载"])
        for owner in sorted(OWNERS):
            lines.append(f"- {owner}: {owner_counts.get(owner, 0)}")
        lines.extend(["", "## Root Tasks"])
        root_tasks = [task for task in tasks if task["id"] == task["root_id"]]
        if not root_tasks:
            lines.append("- 暂无")
        else:
            for task in root_tasks:
                lines.append(
                    f"- `{task['id']}` [{task['lifecycle_state']}] {task['title']} | owner: {task['owner_agent']} | next: {task.get('next_action') or '-'}"
                )
        content = "\n".join(lines).rstrip() + "\n"
        ROLLUP_PATH.write_text(content, encoding="utf-8")
        return content

    def materialize_views(self) -> None:
        self.sync_registry()
        self.render_work_board()
        self.render_rollup()

    def _append_event_jsonl(
        self,
        task_id: str,
        event_id: str,
        ts: str,
        actor: str,
        event_type: str,
        summary: str,
        detail: dict[str, Any] | None,
    ) -> None:
        day = ts[:10]
        path = RUNTIME_DIR / "events" / f"{day}.jsonl"
        row = {
            "id": event_id,
            "taskId": task_id,
            "at": ts,
            "actor": actor,
            "eventType": event_type,
            "summary": summary,
            "detail": detail or {},
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenClaw Task Runtime v1")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize DB and runtime files")
    sub.add_parser("board", help="Render board + rollup + registry")
    
    disp = sub.add_parser("dispatch", help="Dispatch queued tasks")
    disp.add_argument("--dry-run", action="store_true")
    disp.add_argument("--lease-owner", default="dispatcher")
    
    ingest_p = sub.add_parser("ingest", help="Ingest agent result")
    ingest_p.add_argument("--result", required=True)
    
    handoff_p = sub.add_parser("handoff", help="Handoff runtime")
    handoff_p.add_argument("subcommand", nargs="?")
    
    sup = sub.add_parser("supervisor", help="Supervisor checks")
    sup.add_argument("--status-card", action="store_true")
    sup.add_argument("--check-stale", action="store_true")
    sup.add_argument("--check-blocked", action="store_true")

    create = sub.add_parser("create-task", help="Create a task")
    create.add_argument("--title", required=True)
    create.add_argument("--owner", required=True)
    create.add_argument("--requested-by", required=True)
    create.add_argument("--type", default="epic")
    create.add_argument("--phase", default="intake")
    create.add_argument("--priority", default="P2")
    create.add_argument("--current-step")
    create.add_argument("--next-action")
    create.add_argument("--parent-id")
    create.add_argument("--root-id")

    event = sub.add_parser("append-event", help="Append an event to a task")
    event.add_argument("--task-id", required=True)
    event.add_argument("--actor", required=True)
    event.add_argument("--event-type", required=True)
    event.add_argument("--summary", required=True)
    event.add_argument("--detail-json")

    show = sub.add_parser("show-task", help="Show projected task state")
    show.add_argument("--task-id", required=True)

    sub.add_parser("list-tasks", help="List tasks")
    return parser


def main(argv: Iterable[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    runtime = TaskRuntime()

    if args.command == "init":
        runtime.materialize_views()
        print(json.dumps({"status": "ok", "db": str(DB_PATH), "board": str(BOARD_PATH), "rollup": str(ROLLUP_PATH)}, ensure_ascii=False, indent=2))
        return

    if args.command == "board":
        runtime.materialize_views()
        print(json.dumps({"status": "ok", "registry": str(REGISTRY_PATH), "board": str(BOARD_PATH), "rollup": str(ROLLUP_PATH)}, ensure_ascii=False, indent=2))
        return

    if args.command == "create-task":
        task_id = runtime.create_task(
            TaskCreate(
                title=args.title,
                owner_agent=args.owner,
                requested_by=args.requested_by,
                task_type=args.type,
                phase=args.phase,
                priority=args.priority,
                current_step=args.current_step,
                next_action=args.next_action,
                parent_id=args.parent_id,
                root_id=args.root_id,
            )
        )
        print(json.dumps({"status": "ok", "taskId": task_id}, ensure_ascii=False, indent=2))
        return

    if args.command == "append-event":
        detail = json.loads(args.detail_json) if args.detail_json else None
        event_id = runtime.append_event(
            args.task_id,
            actor=args.actor,
            event_type=args.event_type,
            summary=args.summary,
            detail=detail,
        )
        print(json.dumps({"status": "ok", "eventId": event_id}, ensure_ascii=False, indent=2))
        return

    if args.command == "show-task":
        print(json.dumps(runtime.task_state_view(args.task_id), ensure_ascii=False, indent=2))
        return

    if args.command == "list-tasks":
        print(json.dumps(runtime.sync_registry(), ensure_ascii=False, indent=2))
        return

    if args.command == "dispatch":
        from openclaw_task_runtime.dispatcher import run_dispatch
        sys.argv = ['dispatch', '--lease-owner', args.lease_owner]
        if args.dry_run:
            sys.argv.append('--dry-run')
        run_dispatch()
        return

    if args.command == "ingest":
        from openclaw_task_runtime.agent_bridge import run_ingest
        sys.argv = ['ingest', '--result', args.result]
        run_ingest()
        return

    if args.command == "handoff":
        from openclaw_task_runtime.handoff import run_handoff
        run_handoff()
        return

    if args.command == "supervisor":
        from openclaw_task_runtime.supervisor import run_supervisor
        run_supervisor()
        return

    parser.error(f"unsupported command: {args.command}")


if __name__ == "__main__":
    main()
