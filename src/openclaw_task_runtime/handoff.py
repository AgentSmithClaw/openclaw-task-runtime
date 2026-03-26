from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "runtime.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


VALID_MODES = {"delegate", "transfer", "review", "escalate"}
VALID_STATUS = {"pending", "accepted", "done", "rejected"}
VALID_AGENTS = {"picard", "spock", "sulu", "laforge", "worf", "uhura"}


@dataclass
class HandoffRequest:
    task_id: str
    mode: str
    from_agent: str
    to_agent: str
    child_task_id: str | None = None
    contract: dict[str, Any] | None = None


class HandoffRuntime:
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

    def create_handoff(self, request: HandoffRequest) -> dict[str, Any]:
        if request.mode not in VALID_MODES:
            raise ValueError(f"Invalid mode: {request.mode}")
        if request.to_agent not in VALID_AGENTS:
            raise ValueError(f"Invalid to_agent: {request.to_agent}")

        task = self.get_task(request.task_id)
        if not task:
            raise KeyError(f"Task not found: {request.task_id}")

        handoff_id = f"handoff_{uuid.uuid4().hex[:12]}"
        ts = now_iso()
        
        contract = request.contract or {}
        contract["mode"] = request.mode
        contract["from"] = request.from_agent
        contract["to"] = request.to_agent

        with self.connect() as conn:
            conn.execute(
                """INSERT INTO task_handoffs 
                   (id, task_id, mode, from_agent, to_agent, child_task_id, contract_json, status, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (handoff_id, request.task_id, request.mode, request.from_agent, request.to_agent,
                 request.child_task_id, json.dumps(contract), "pending", ts),
            )

            new_owner = request.to_agent
            if request.mode == "delegate" and request.child_task_id:
                new_owner = request.to_agent
            
            conn.execute(
                """UPDATE tasks SET owner_agent = ?, updated_at = ? WHERE id = ?""",
                (new_owner, ts, request.task_id),
            )

            conn.execute(
                """INSERT INTO task_events (id, task_id, at, actor, event_type, summary, detail_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (f"evt_{uuid.uuid4().hex[:12]}", request.task_id, ts, request.from_agent, "handoff",
                 f"Handoff [{request.mode}] from {request.from_agent} to {request.to_agent}",
                 json.dumps({"mode": request.mode, "toAgent": request.to_agent, "childTaskId": request.child_task_id})),
            )
            conn.commit()

        return {
            "status": "created",
            "handoffId": handoff_id,
            "taskId": request.task_id,
            "mode": request.mode,
            "toAgent": request.to_agent,
        }

    def accept_handoff(self, handoff_id: str, actor: str) -> dict[str, Any]:
        with self.connect() as conn:
            handoff = conn.execute("SELECT * FROM task_handoffs WHERE id = ?", (handoff_id,)).fetchone()
            if not handoff:
                raise KeyError(f"Handoff not found: {handoff_id}")
            
            if handoff["to_agent"] != actor:
                raise ValueError(f"Handoff not for {actor}")
            
            ts = now_iso()
            conn.execute(
                """UPDATE task_handoffs SET status = 'accepted', resolved_at = ? WHERE id = ?""",
                (ts, handoff_id),
            )
            conn.execute(
                """INSERT INTO task_events (id, task_id, at, actor, event_type, summary, detail_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (f"evt_{uuid.uuid4().hex[:12]}", handoff["task_id"], ts, actor, "handoff_accepted",
                 f"{actor} accepted handoff", json.dumps({"handoffId": handoff_id})),
            )
            conn.commit()

        return {"status": "accepted", "handoffId": handoff_id}

    def reject_handoff(self, handoff_id: str, actor: str, reason: str) -> dict[str, Any]:
        with self.connect() as conn:
            handoff = conn.execute("SELECT * FROM task_handoffs WHERE id = ?", (handoff_id,)).fetchone()
            if not handoff:
                raise KeyError(f"Handoff not found: {handoff_id}")
            
            ts = now_iso()
            conn.execute(
                """UPDATE task_handoffs SET status = 'rejected', resolved_at = ? WHERE id = ?""",
                (ts, handoff_id),
            )
            conn.execute(
                """INSERT INTO task_events (id, task_id, at, actor, event_type, summary, detail_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (f"evt_{uuid.uuid4().hex[:12]}", handoff["task_id"], ts, actor, "handoff_rejected",
                 f"{actor} rejected handoff: {reason}", json.dumps({"handoffId": handoff_id, "reason": reason})),
            )
            conn.commit()

        return {"status": "rejected", "handoffId": handoff_id, "reason": reason}

    def list_pending_handoffs(self, agent: str | None = None) -> list[dict[str, Any]]:
        with self.connect() as conn:
            if agent:
                rows = conn.execute(
                    "SELECT * FROM task_handoffs WHERE status = 'pending' AND to_agent = ? ORDER BY created_at DESC",
                    (agent,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM task_handoffs WHERE status = 'pending' ORDER BY created_at DESC",
                ).fetchall()
        return [dict(row) for row in rows]


def run_handoff():
    import argparse
    parser = argparse.ArgumentParser(description="Handoff Runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    
    create = sub.add_parser("create", help="Create handoff")
    create.add_argument("--task-id", required=True)
    create.add_argument("--mode", required=True, choices=["delegate", "transfer", "review", "escalate"])
    create.add_argument("--from", dest="from_agent", required=True)
    create.add_argument("--to", dest="to_agent", required=True)
    create.add_argument("--child-task-id")
    
    accept = sub.add_parser("accept", help="Accept handoff")
    accept.add_argument("--handoff-id", required=True)
    accept.add_argument("--actor", required=True)
    
    reject = sub.add_parser("reject", help="Reject handoff")
    reject.add_argument("--handoff-id", required=True)
    reject.add_argument("--actor", required=True)
    reject.add_argument("--reason", required=True)
    
    list_p = sub.add_parser("list", help="List pending handoffs")
    list_p.add_argument("--agent", default=None)
    
    args = parser.parse_args()
    runtime = HandoffRuntime()
    
    if args.command == "create":
        result = runtime.create_handoff(HandoffRequest(
            task_id=args.task_id,
            mode=args.mode,
            from_agent=args.from_agent,
            to_agent=args.to_agent,
            child_task_id=args.child_task_id,
        ))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == "accept":
        result = runtime.accept_handoff(args.handoff_id, args.actor)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == "reject":
        result = runtime.reject_handoff(args.handoff_id, args.actor, args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.command == "list":
        results = runtime.list_pending_handoffs(args.agent)
        print(json.dumps({"handoffs": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run_handoff()
