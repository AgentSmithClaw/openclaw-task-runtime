-- OpenClaw Task Control Plane v1
-- Source of truth: task DB
-- Notes:
-- 1) V1 可直接跑在 SQLite + WAL；多节点建议改 Postgres
-- 2) 不要再把 session store / Markdown 当任务真相

CREATE TABLE IF NOT EXISTS tasks (
  id                TEXT PRIMARY KEY,
  root_id           TEXT NOT NULL,
  parent_id         TEXT,
  title             TEXT NOT NULL,
  type              TEXT NOT NULL,        -- epic/spec/frontend/backend/qa/rollup/release
  owner_agent       TEXT NOT NULL,        -- picard/spock/sulu/laforge/worf/uhura
  requested_by      TEXT NOT NULL,        -- user/system/picard
  lifecycle_state   TEXT NOT NULL,        -- queued/claimed/doing/waiting_input/waiting_external/blocked/done/failed
  freshness_state   TEXT NOT NULL,        -- fresh/stale
  phase             TEXT NOT NULL,        -- intake/spec/delivery/qa/rollup/release/closed
  priority          TEXT NOT NULL DEFAULT 'P2',
  current_step      TEXT,
  next_action       TEXT,
  done_criteria_json TEXT,
  blocker_type      TEXT,
  blocker_detail    TEXT,
  source_session_key TEXT,
  source_message_ref TEXT,
  artifact_root     TEXT,
  latest_artifact_ref TEXT,
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL,
  last_progress_at  TEXT,
  next_run_at       TEXT,
  deadline_at       TEXT,
  lease_owner       TEXT,
  lease_until       TEXT,
  retry_count       INTEGER NOT NULL DEFAULT 0,
  max_retries       INTEGER NOT NULL DEFAULT 3
);

CREATE TABLE IF NOT EXISTS task_dependencies (
  task_id             TEXT NOT NULL,
  depends_on_task_id  TEXT NOT NULL,
  relation            TEXT NOT NULL,      -- hard/soft/review
  PRIMARY KEY (task_id, depends_on_task_id)
);

CREATE TABLE IF NOT EXISTS task_handoffs (
  id               TEXT PRIMARY KEY,
  task_id          TEXT NOT NULL,
  mode             TEXT NOT NULL,         -- delegate/transfer/review/escalate
  from_agent       TEXT NOT NULL,
  to_agent         TEXT NOT NULL,
  child_task_id    TEXT,
  contract_json    TEXT NOT NULL,
  status           TEXT NOT NULL,         -- pending/accepted/done/rejected
  created_at       TEXT NOT NULL,
  resolved_at      TEXT
);

CREATE TABLE IF NOT EXISTS task_artifacts (
  id               TEXT PRIMARY KEY,
  task_id          TEXT NOT NULL,
  kind             TEXT NOT NULL,         -- spec/pr/patch/report/test/risk/release_note/dashboard/summary
  path_or_url      TEXT NOT NULL,
  metadata_json    TEXT,
  created_at       TEXT NOT NULL,
  created_by       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS task_events (
  id               TEXT PRIMARY KEY,
  task_id          TEXT NOT NULL,
  at               TEXT NOT NULL,
  actor            TEXT NOT NULL,
  event_type       TEXT NOT NULL,         -- created/claimed/progress/handoff/wait/block/done/fail/stale
  summary          TEXT NOT NULL,
  detail_json      TEXT
);

CREATE TABLE IF NOT EXISTS agent_runs (
  id               TEXT PRIMARY KEY,
  task_id          TEXT NOT NULL,
  agent_id         TEXT NOT NULL,
  trigger_type     TEXT NOT NULL,         -- dispatch/retry/manual/cron/child_done/approval/webhook
  run_id           TEXT,
  session_key      TEXT,
  started_at       TEXT NOT NULL,
  finished_at      TEXT,
  result_state     TEXT,
  output_summary   TEXT
);

CREATE INDEX IF NOT EXISTS idx_tasks_root_id       ON tasks(root_id);
CREATE INDEX IF NOT EXISTS idx_tasks_owner_state   ON tasks(owner_agent, lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_tasks_next_run      ON tasks(next_run_at);
CREATE INDEX IF NOT EXISTS idx_tasks_lease         ON tasks(lease_until);
CREATE INDEX IF NOT EXISTS idx_events_task_at      ON task_events(task_id, at);
CREATE INDEX IF NOT EXISTS idx_runs_task_started   ON agent_runs(task_id, started_at);
