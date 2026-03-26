from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "runtime.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class SupervisorDecision:
    task_id: str
    decision: str
    reason: str
    suggested_action: str | None = None


class Supervisor:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def connect(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    def get_all_tasks(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]

    def check_stale_tasks(self) -> list[SupervisorDecision]:
        decisions = []
        ts = now_iso()
        
        with self.connect() as conn:
            stale = conn.execute(
                """SELECT * FROM tasks 
                   WHERE lifecycle_state NOT IN ('done', 'failed')
                   AND (last_progress_at IS NULL OR last_progress_at < datetime('now', '-1 hour'))
                   AND freshness_state = 'fresh'""",
            ).fetchall()
        
        for task in stale:
            decisions.append(SupervisorDecision(
                task_id=task["id"],
                decision="mark_stale",
                reason="No progress for over 1 hour",
                suggested_action="Check with owner or escalate",
            ))
        
        return decisions

    def check_blocked_tasks(self) -> list[SupervisorDecision]:
        decisions = []
        
        with self.connect() as conn:
            blocked = conn.execute(
                """SELECT * FROM tasks 
                   WHERE lifecycle_state = 'blocked' 
                   AND updated_at < datetime('now', '-30 minutes')""",
            ).fetchall()
        
        for task in blocked:
            decisions.append(SupervisorDecision(
                task_id=task["id"],
                decision="escalate_blocker",
                reason=f"Blocked: {task.get('blocker_type')} - {task.get('blocker_detail')}",
                suggested_action="Clear blocker or reassign",
            ))
        
        return decisions

    def check_dependencies(self) -> list[SupervisorDecision]:
        decisions = []
        
        with self.connect() as conn:
            pending_kids = conn.execute(
                """SELECT t.*, p.lifecycle_state as parent_state
                   FROM tasks t
                   JOIN tasks p ON t.parent_id = p.id
                   WHERE t.lifecycle_state = 'queued' 
                   AND p.lifecycle_state != 'done'""",
            ).fetchall()
        
        for task in pending_kids:
            decisions.append(SupervisorDecision(
                task_id=task["id"],
                decision="wait_parent",
                reason=f"Parent task {task['parent_id']} not done",
                suggested_action="Wait for parent to complete",
            ))
        
        return decisions

    def check_completion_rate(self) -> dict[str, Any]:
        tasks = self.get_all_tasks()
        total = len(tasks)
        done = sum(1 for t in tasks if t["lifecycle_state"] == "done")
        failed = sum(1 for t in tasks if t["lifecycle_state"] == "failed")
        
        return {
            "total": total,
            "done": done,
            "failed": failed,
            "completion_rate": done / total if total > 0 else 0,
            "failure_rate": failed / total if total > 0 else 0,
        }

    def generate_status_card(self) -> dict[str, Any]:
        tasks = self.get_all_tasks()
        completion = self.check_completion_rate()
        
        by_state = {}
        by_owner = {}
        by_phase = {}
        
        for task in tasks:
            state = task["lifecycle_state"]
            owner = task["owner_agent"]
            phase = task["phase"]
            
            by_state[state] = by_state.get(state, 0) + 1
            by_owner[owner] = by_owner.get(owner, 0) + 1
            by_phase[phase] = by_phase.get(phase, 0) + 1
        
        stale_decisions = self.check_stale_tasks()
        blocked_decisions = self.check_blocked_tasks()
        
        return {
            "generatedAt": now_iso(),
            "completion": completion,
            "byState": by_state,
            "byOwner": by_owner,
            "byPhase": by_phase,
            "alerts": {
                "stale": len(stale_decisions),
                "blocked": len(blocked_decisions),
                "staleTasks": [d.task_id for d in stale_decisions],
                "blockedTasks": [d.task_id for d in blocked_decisions],
            },
        }

    def supervise(self) -> dict[str, Any]:
        stale = self.check_stale_tasks()
        blocked = self.check_blocked_tasks()
        deps = self.check_dependencies()
        status = self.generate_status_card()
        
        return {
            "status": "ok",
            "timestamp": now_iso(),
            "staleDecisions": [
                {"taskId": d.task_id, "reason": d.reason, "suggestedAction": d.suggested_action}
                for d in stale
            ],
            "blockedDecisions": [
                {"taskId": d.task_id, "reason": d.reason, "suggestedAction": d.suggested_action}
                for d in blocked
            ],
            "dependencyDecisions": [
                {"taskId": d.task_id, "reason": d.reason, "suggestedAction": d.suggested_action}
                for d in deps
            ],
            "statusCard": status,
        }


def run_supervisor():
    import argparse
    parser = argparse.ArgumentParser(description="Supervisor")
    parser.add_argument("--status-card", action="store_true", help="Generate status card")
    parser.add_argument("--check-stale", action="store_true", help="Check stale tasks")
    parser.add_argument("--check-blocked", action="store_true", help="Check blocked tasks")
    args = parser.parse_args()
    
    sup = Supervisor()
    
    if args.status_card:
        print(json.dumps(sup.generate_status_card(), ensure_ascii=False, indent=2))
    elif args.check_stale:
        print(json.dumps({"stale": sup.check_stale_tasks()}, ensure_ascii=False, indent=2))
    elif args.check_blocked:
        print(json.dumps({"blocked": sup.check_blocked_tasks()}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(sup.supervise(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_supervisor()
