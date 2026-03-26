# OpenClaw 多 Agent 持续任务系统 Starter Pack

这个压缩包是配套《OpenClaw 多 Agent 持续任务系统落地方案》的起手包，目标是让团队可以直接在现有 OpenClaw 环境上开工。

## 包内结构
- `sql/`：任务控制平面最小表结构
- `config/`：运行时、策略、agent 合同、OpenClaw hook、Temporal 拓扑与队列建议
- `schemas/`：结构化输出与 handoff / task state JSON Schema
- `templates/`：任务目录、报告与镜像文件模板
- `env/`：环境变量示例
- `docker/`：Temporal 本地开发示例编排
- `manifest.txt`：文件清单

## 建议落地顺序
1. 先上 `sql/001_task_control_plane.sql`
2. 按 `config/runtime.yaml` 起 `dispatcher / reconciler / rollup`
3. 将 OpenClaw 的 `/status`、`/approve`、`/resume` 接到 `config/openclaw/*`
4. 强制 agent 输出符合 `schemas/*.json` 的结构化结果
5. 用 `templates/tasks/*` 跑通一个真实 epic
6. 稳定后再接 `config/temporal/*`，把 durable runtime 迁到 Temporal

## 适用前提
- 当前已有 OpenClaw 多 agent、消息通道、heartbeat、cron
- 希望在不推翻现有系统的前提下，把系统从“问一句做一句”改造成“任务对象驱动”

生成日期：2026-03-26
