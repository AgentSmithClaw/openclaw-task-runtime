from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "runtime.yaml"
DB_PATH = ROOT / "data" / "runtime.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_config() -> dict[str, Any]:
    import yaml
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {}


@dataclass
class DispatchResult:
    task_id: str
    lease_owner: str
    lease_until: str
    structured_input: dict[str, Any]


class Dispatcher:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.config = load_config()
        self.lease_minutes = self.config.get("components", {}).get("dispatcher", {}).get("lease_minutes", 15)
        self.claim_batch_size = self.config.get("components", {}).get("dispatcher", {}).get("claim_batch_size", 10)

    def connect(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def scan_queued_tasks(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """SELECT * FROM tasks 
                   WHERE lifecycle_state = 'queued' 
                   ORDER BY 
                     CASE priority WHEN 'P0' THEN 1 WHEN 'P1' THEN 2 WHEN 'P2' THEN 3 ELSE 4 END,
                     created_at ASC
                   LIMIT ?""",
                (self.claim_batch_size,),
            ).fetchall()
        return [dict(row) for row in rows]

    def claim_task(self, task_id: str, lease_owner: str) -> str | None:
        ts = now_iso()
        lease_until = (datetime.now(timezone.utc) + timedelta(minutes=self.lease_minutes)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        
        with self.connect() as conn:
            existing = conn.execute(
                "SELECT id FROM tasks WHERE id = ? AND lifecycle_state = 'queued' AND (lease_owner IS NULL OR lease_until IS NULL OR lease_until < ?)",
                (task_id, ts),
            ).fetchone()
            
            if not existing:
                return None
            
            conn.execute(
                """UPDATE tasks SET 
                   lifecycle_state = 'claimed',
                   lease_owner = ?,
                   lease_until = ?,
                   updated_at = ?
                   WHERE id = ?""",
                (lease_owner, lease_until, ts, task_id),
            )
            
            conn.execute(
                """INSERT INTO task_events (id, task_id, at, actor, event_type, summary, detail_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (f"evt_{uuid.uuid4().hex[:12]}", task_id, ts, lease_owner, "claimed", f"Task claimed by {lease_owner}", None),
            )
            conn.commit()
        return lease_until

    def build_structured_input(self, task: dict[str, Any]) -> dict[str, Any]:
        return {
            "taskId": task["id"],
            "rootId": task["root_id"],
            "title": task["title"],
            "type": task["type"],
            "owner": task["owner_agent"],
            "phase": task["phase"],
            "currentStep": task.get("current_step"),
            "nextAction": task.get("next_action"),
            "doneCriteria": json.loads(task.get("done_criteria_json", "null") or "null") if task.get("done_criteria_json") else None,
            "parentId": task.get("parent_id"),
            "requestedBy": task["requested_by"],
        }

    def dispatch(self, lease_owner: str = "dispatcher") -> list[DispatchResult]:
        results = []
        queued = self.scan_queued_tasks()
        
        for task in queued:
            lease_until = self.claim_task(task["id"], lease_owner)
            if lease_until:
                results.append(DispatchResult(
                    task_id=task["id"],
                    lease_owner=lease_owner,
                    lease_until=lease_until,
                    structured_input=self.build_structured_input(task),
                ))
        
        return results


def run_dispatch():
    import argparse
    parser = argparse.ArgumentParser(description="Dispatcher")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--lease-owner", default="dispatcher")
    args = parser.parse_args()
    
    dispatcher = Dispatcher()
    results = dispatcher.dispatch(args.lease_owner)
    
    for r in results:
        print(json.dumps({
            "taskId": r.task_id,
            "leaseOwner": r.lease_owner,
            "leaseUntil": r.lease_until,
            "structuredInput": r.structured_input,
        }, ensure_ascii=False, indent=2))
        print("---")
    
    if not results:
        print(json.dumps({"status": "no_tasks", "message": "No queued tasks to dispatch"}))


if __name__ == "__main__":
    run_dispatch()
