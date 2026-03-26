# OpenClaw Task Runtime — Implementation Next Steps

## 当前状态
- 已导入 starter pack
- 已创建 runtime 目录骨架
- 已补 bootstrap 初始化脚本
- 已具备最小 task DB 初始化能力
- 已补 Phase 1 最小控制面逻辑：task create / event append / state machine v1 / board projection / rollup projection

## 下一步最小闭环
1. 实现 dispatcher v0（仅扫描 queued task）
2. 实现 structured agent result ingest
3. 实现 handoff runtime（delegate/transfer/review/escalate）
4. 跑通一条 root -> spec -> frontend/backend -> qa -> rollup 的最小链路
5. 再补 stale / blocked / retry / lease recovery

## 当前目录
- `sql/`：DDL
- `schemas/`：JSON Schema
- `config/`：policy / contract / openclaw samples
- `runtime/`：board / events / task registry
- `src/openclaw_task_runtime/`：实现代码

## 原则
- source of truth = task db
- heartbeat / cron = scheduler only
- group chat = notification plane only
- Picard = supervisor, not scheduler
- Uhura = projection / rollup, not state truth
