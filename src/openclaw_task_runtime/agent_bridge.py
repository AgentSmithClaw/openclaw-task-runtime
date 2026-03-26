from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "runtime.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


VALID_DECISIONS = {"progress", "wait_input", "wait_external", "blocked", "done", "failed"}
VALID_AGENTS = {"picard", "spock", "sulu", "laforge", "worf", "uhura"}


@dataclass
class AgentResult:
    task_id: str
    agent: str
    decision: str
    summary: str
    current_step: str | None = None
    next_action: str | None = None
    feature_id: str | None = None
    artifacts: list[dict[str, Any]] | None = None
    proof: list[str] | None = None
    blockers: list[dict[str, Any]] | None = None
    handoffs: list[dict[str, Any]] | None = None
    needs_signal: str | None = None
    state_patch: dict[str, Any] | None = None


class AgentResultIngestor:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def connect(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def parse_result(self, raw_input: str | dict[str, Any]) -> AgentResult:
        if isinstance(raw_input, str):
            try:
                raw_input = json.loads(raw_input)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON: {raw_input[:200]}")

        required = ["taskId", "agent", "decision", "summary"]
        for field in required:
            if field not in raw_input:
                raise ValueError(f"Missing required field: {field}")

        if raw_input["agent"] not in VALID_AGENTS:
            raise ValueError(f"Invalid agent: {raw_input['agent']}")
        if raw_input["decision"] not in VALID_DECISIONS:
            raise ValueError(f"Invalid decision: {raw_input['decision']}")

        return AgentResult(
            task_id=raw_input["taskId"],
            agent=raw_input["agent"],
            decision=raw_input["decision"],
            summary=raw_input["summary"],
            current_step=raw_input.get("currentStep"),
            next_action=raw_input.get("nextAction"),
            feature_id=raw_input.get("featureId"),
            artifacts=raw_input.get("artifacts"),
            proof=raw_input.get("proof"),
            blockers=raw_input.get("blockers"),
            handoffs=raw_input.get("handoffs"),
            needs_signal=raw_input.get("needsSignal"),
            state_patch=raw_input.get("statePatch"),
        )

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    def _event_type_from_decision(self, decision: str) -> str:
        mapping = {
            "progress": "progress",
            "wait_input": "wait_input",
            "wait_external": "wait",
            "blocked": "block",
            "done": "done",
            "failed": "fail",
        }
        return mapping.get(decision, "progress")

    def ingest_result(self, result: AgentResult) -> dict[str, Any]:
        task = self.get_task(result.task_id)
        if not task:
            raise KeyError(f"Task not found: {result.task_id}")

        ts = now_iso()
        event_type = self._event_type_from_decision(result.decision)

        detail = {
            "decision": result.decision,
            "summary": result.summary,
        }
        if result.current_step:
            detail["current_step"] = result.current_step
        if result.next_action:
            detail["next_action"] = result.next_action
        if result.state_patch:
            detail.update(result.state_patch)

        with self.connect() as conn:
            import uuid
            event_id = f"evt_{uuid.uuid4().hex[:12]}"
            
            conn.execute(
                """INSERT INTO task_events (id, task_id, at, actor, event_type, summary, detail_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event_id, result.task_id, ts, result.agent, event_type, result.summary, json.dumps(detail)),
            )

            lifecycle_state = result.decision if result.decision in {"blocked", "done", "failed"} else task["lifecycle_state"]
            if result.decision in {"progress", "wait_input", "wait_external"}:
                lifecycle_state = "doing" if result.decision == "progress" else result.decision

            fields = {
                "updated_at": ts,
                "lifecycle_state": lifecycle_state,
                "last_progress_at": ts if event_type in {"progress", "done"} else None,
            }
            
            if result.current_step:
                fields["current_step"] = result.current_step
            if result.next_action is not None:
                fields["next_action"] = result.next_action
            if result.decision == "blocked":
                blocker = result.blockers[0] if result.blockers else {}
                fields["blocker_type"] = blocker.get("type", "unspecified")
                fields["blocker_detail"] = blocker.get("summary", result.summary)
            if result.decision in {"done", "failed"}:
                fields["next_action"] = None
                fields["lease_owner"] = None
                fields["lease_until"] = None

            assignments = ", ".join(f"{k} = ?" for k in fields if fields.get(k) is not None)
            params = tuple(v for v in fields.values() if v is not None) + (result.task_id,)
            
            if assignments:
                conn.execute(f"UPDATE tasks SET {assignments} WHERE id = ?", params)

            if result.artifacts:
                for art in result.artifacts:
                    art_id = f"art_{uuid.uuid4().hex[:12]}"
                    conn.execute(
                        """INSERT INTO task_artifacts (id, task_id, kind, path_or_url, metadata_json, created_at, created_by)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (art_id, result.task_id, art.get("kind"), art.get("path"), json.dumps({"description": art.get("description")}), ts, result.agent),
                    )

            if result.handoffs:
                for handoff in result.handoffs:
                    handoff_id = f"handoff_{uuid.uuid4().hex[:12]}"
                    conn.execute(
                        """INSERT INTO task_handoffs (id, task_id, mode, from_agent, to_agent, child_task_id, contract_json, status, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (handoff_id, result.task_id, handoff.get("mode"), result.agent, handoff.get("toAgent"), handoff.get("childTaskId"), json.dumps(handoff.get("contract", {})), "pending", ts),
                    )

            conn.commit()

        return {
            "status": "ingested",
            "taskId": result.task_id,
            "decision": result.decision,
            "eventId": event_id,
        }


def run_ingest():
    import argparse
    parser = argparse.ArgumentParser(description="Agent Result Ingestor")
    parser.add_argument("--result", required=True, help="JSON string or @file.json")
    args = parser.parse_args()

    raw = args.result
    if raw.startswith("@"):
        raw = Path(raw[1:]).read_text(encoding="utf-8")

    ingestor = AgentResultIngestor()
    result = ingestor.parse_result(raw)
    output = ingestor.ingest_result(result)
    
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_ingest()
