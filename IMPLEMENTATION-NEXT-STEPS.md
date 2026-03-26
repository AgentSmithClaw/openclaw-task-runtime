# OpenClaw Task Runtime — Implementation Next Steps

## 当前状态
- starter pack 已落地并已提交收口
- task DB / registry / board / rollup 已可生成稳定非空结果
- Phase 1 最小控制面已完成：task / event / state machine / projection
- Phase 2 核心模块已完成：dispatcher / structured ingest / handoff / supervisor
- 已保留一条最小闭环链：root -> spec -> frontend/backend -> qa -> rollup

## 当前剩余重点
1. reconciler / watchdog（lease recovery）
2. retry / stale / blocked 规则从“最小版”补到“更稳版”
3. agent bridge 与 OpenClaw 外部执行层进一步接线
4. Temporal durable runtime（后续阶段，不是当前阻塞项）

## 当前目录
- `sql/`：DDL
- `schemas/`：JSON Schema
- `config/`：policy / contract / openclaw samples
- `runtime/`：board / events / task registry
- `src/openclaw_task_runtime/`：实现代码与统一 CLI 入口

## 当前验收口径
- source of truth = task db
- markdown board / rollup = projection only
- heartbeat / cron = scheduler only
- Picard = supervisor, not scheduler
- Uhura = projection / rollup, not state truth

## 结论
当前仓库已经达到“可交付的 v1 最小 runtime”状态；后续工作属于稳定化、接线深化与 durable runtime 演进。
