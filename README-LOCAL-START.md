# Local Start

## 1. 初始化最小 runtime

```bash
cd openclaw-task-runtime
PYTHONPATH=src python3 -m openclaw_task_runtime init
```

## 2. 创建一个 root task

```bash
cd openclaw-task-runtime
PYTHONPATH=src python3 -m openclaw_task_runtime create-task \
  --title "OpenClaw Task Runtime v1" \
  --owner picard \
  --requested-by user \
  --phase intake \
  --current-step "bootstrap runtime" \
  --next-action "spec + state machine"
```

## 3. 给任务追加进度事件

```bash
cd openclaw-task-runtime
PYTHONPATH=src python3 -m openclaw_task_runtime append-event \
  --task-id <task_id> \
  --actor picard \
  --event-type progress \
  --summary "Phase 1 in progress" \
  --detail-json '{"current_step":"state machine v1","next_action":"render board"}'
```

## 4. 查看投影结果
- `runtime/tasks/registry.json`
- `runtime/boards/WORK-BOARD.md`
- `runtime/boards/ROLLUP.md`
- `runtime/events/YYYY-MM-DD.jsonl`

## 5. 当前阶段说明
当前 v1 已补到最小控制面运行逻辑：
- task create / list
- event append
- lifecycle state machine v1
- board / rollup projection
- dispatcher (scan & claim queued tasks)
- agent bridge (ingest structured result)
- handoff runtime (delegate/transfer/review/escalate)
- supervisor (stale/blocked check, status card)

尚未完成：
- reconciler/watchdog (lease recovery)
- Temporal integration
