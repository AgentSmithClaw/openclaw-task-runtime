# Local Start

## 1. 初始化 / 重新物化 runtime

```bash
cd openclaw-task-runtime
PYTHONPATH=src python3 -m openclaw_task_runtime init
```

## 2. 查看当前任务投影

```bash
cd openclaw-task-runtime
PYTHONPATH=src python3 -m openclaw_task_runtime list-tasks
PYTHONPATH=src python3 -m openclaw_task_runtime board
```

## 3. 创建一个 root task

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

## 4. 给任务追加进度事件

```bash
cd openclaw-task-runtime
PYTHONPATH=src python3 -m openclaw_task_runtime append-event \
  --task-id <task_id> \
  --actor picard \
  --event-type progress \
  --summary "Phase 1 in progress" \
  --detail-json '{"current_step":"state machine v1","next_action":"render board"}'
```

## 5. 调度 queued task

```bash
cd openclaw-task-runtime
PYTHONPATH=src python3 -m openclaw_task_runtime dispatch --lease-owner dispatcher
```

## 6. 写入结构化 agent result

```bash
cd openclaw-task-runtime
PYTHONPATH=src python3 -m openclaw_task_runtime ingest \
  --result '{"taskId":"<task_id>","agent":"picard","decision":"done","summary":"completed","currentStep":"done"}'
```

## 7. 处理 handoff

```bash
cd openclaw-task-runtime
PYTHONPATH=src python3 -m openclaw_task_runtime handoff create \
  --task-id <task_id> \
  --mode delegate \
  --from picard \
  --to spock

PYTHONPATH=src python3 -m openclaw_task_runtime handoff list
```

## 8. 运行 supervisor 检查

```bash
cd openclaw-task-runtime
PYTHONPATH=src python3 -m openclaw_task_runtime supervisor --status-card
PYTHONPATH=src python3 -m openclaw_task_runtime supervisor --check-stale
```

## 9. 查看最终产物
- `runtime/tasks/registry.json`
- `runtime/boards/WORK-BOARD.md`
- `runtime/boards/ROLLUP.md`
- `runtime/events/YYYY-MM-DD.jsonl`

## 10. 当前阶段说明
当前仓库已具备 v1 最小 runtime 能力：
- task create / list / show
- event append + state transition
- board / rollup projection
- dispatcher（scan & claim queued tasks）
- structured agent result ingest
- handoff runtime（delegate / transfer / review / escalate）
- supervisor（stale / blocked / status card）
- 稳定最小闭环链（root -> spec -> frontend/backend -> qa -> rollup）

后续仍待增强：
- reconciler / watchdog（lease recovery）
- 更完整 retry 规则
- OpenClaw 外部执行桥深化
- Temporal integration
