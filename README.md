# 🧭 openclaw-task-runtime

<div align="center">

[![Runtime](https://img.shields.io/badge/runtime-Python-3776ab.svg)](#)
[![Storage](https://img.shields.io/badge/storage-SQLite-003b57.svg)](#)
[![Type](https://img.shields.io/badge/type-Task%20Runtime-0f766e.svg)](#)

**一个面向 OpenClaw 多 Agent 持续任务系统的任务控制面 runtime**

把任务状态、handoff、调度、投影和监督能力从聊天记录中抽离出来，沉到统一的 runtime 与状态机里。

</div>

---

## 📖 项目简介

`openclaw-task-runtime` 是一个聚焦 **多 Agent 任务对象化与状态机化** 的基础设施项目。

很多多 Agent 协作系统的真实问题，不是“Agent 不够多”，而是：

- 任务状态散落在聊天记录里
- 谁负责、做到哪、卡在哪没有稳定 source of truth
- handoff 依赖人工转述，容易丢上下文
- board 和 rollup 只是人工整理结果，不是 runtime projection
- supervisor 被迫退化成手工调度员

这个项目的目标，就是把 OpenClaw 多 Agent 协作从 **聊天推进** 升级为 **runtime 推进**。

核心原则包括：

- `Task DB = source of truth`
- `board / rollup = projection`
- `heartbeat / cron = scheduler only`
- `chat / Feishu = notification plane only`
- `supervisor = orchestrator, not manual dispatcher`

---

## ✨ 功能特性

- 🗂️ **任务对象化** - 每个任务都有 id、owner、phase、root / parent 关系
- 🔄 **生命周期状态机** - 基于 event 驱动任务状态迁移
- 📋 **投影物化** - 自动生成 registry、work board、rollup 等视图
- 🚚 **dispatcher** - 扫描 queued task 并执行 claim / lease
- 📥 **structured ingest** - 接收 agent 结构化结果并写入 runtime
- 🤝 **handoff runtime** - 支持 delegate / transfer / review / escalate
- 👀 **supervisor** - 检查 stale、blocked、依赖关系并生成 status card
- 🧱 **边界清晰** - 为后续 durable runtime / Temporal 迁移预留结构边界

---

## 🎯 适用场景

- 多 Agent 持续协作任务编排
- 需要状态机和任务投影的执行系统
- handoff 频繁、角色明确的协作流程
- 从实验型 Agent 系统向工程化 runtime 演进的项目

---

## 📁 目录结构

```bash
openclaw-task-runtime/
├── config/                     # runtime / policy / openclaw / temporal 配置
├── data/                       # runtime.db
├── docker/                     # Temporal 本地开发示例
├── env/                        # 环境变量示例
├── runtime/
│   ├── boards/                 # WORK-BOARD / ROLLUP
│   ├── events/                 # 每日事件日志
│   └── tasks/                  # registry projection
├── schemas/                    # task / handoff / agent result schema
├── sql/                        # 控制面 DDL
├── src/openclaw_task_runtime/
│   ├── runtime_v1.py           # 核心 runtime / CLI / state machine
│   ├── dispatcher.py           # queued task dispatch
│   ├── agent_bridge.py         # structured result ingest
│   ├── handoff.py              # handoff runtime
│   └── supervisor.py           # stale / blocked / status card
├── templates/                  # task / report 模板
├── README-LOCAL-START.md
└── README.md
```

---

## 🛠️ 技术栈

| 模块 | 技术 |
|------|------|
| Runtime | Python |
| 状态存储 | SQLite |
| 配置 | YAML |
| 数据交换 | JSON / JSON Schema |
| 投影输出 | Markdown + JSON |
| 调度边界 | Dispatcher / Cron / Supervisor |
| 后续扩展 | Temporal-ready architecture |

---

## 🧱 当前已实现内容

### 第一阶段（已完成）
- [x] task create / list / show
- [x] event log 与 lifecycle state machine v1
- [x] registry / board / rollup projection
- [x] dispatcher scan + claim 机制
- [x] structured agent result ingest
- [x] handoff runtime 起步版
- [x] supervisor stale / blocked / dependency / status card
- [x] 最小闭环任务链示例

### 当前 MVP 能力
- 用 SQLite 保存任务 source of truth
- 用 event 驱动 lifecycle state 变化
- 用 projection 物化给人读的 board / rollup
- 用 dispatcher / supervisor 衔接执行与观察能力
- 为后续外部执行桥和 durable runtime 演进保留接口

---

## 🚀 快速开始

### 1）安装最小依赖

```bash
git clone https://github.com/AgentSmithClaw/openclaw-task-runtime.git
cd openclaw-task-runtime

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install pyyaml
```

### 2）初始化 runtime

```bash
PYTHONPATH=src python3 -m openclaw_task_runtime init
```

### 3）查看任务和投影

```bash
PYTHONPATH=src python3 -m openclaw_task_runtime list-tasks
PYTHONPATH=src python3 -m openclaw_task_runtime board
```

### 4）创建任务并追加事件

```bash
PYTHONPATH=src python3 -m openclaw_task_runtime create-task \
  --title "OpenClaw Task Runtime v1" \
  --owner picard \
  --requested-by user \
  --phase intake

PYTHONPATH=src python3 -m openclaw_task_runtime append-event \
  --task-id <task_id> \
  --actor picard \
  --event-type progress \
  --summary "Phase 1 in progress"
```

### 5）运行调度与监督

```bash
PYTHONPATH=src python3 -m openclaw_task_runtime dispatch --lease-owner dispatcher
PYTHONPATH=src python3 -m openclaw_task_runtime supervisor --status-card
```

更多本地启动细节见：

- `README-LOCAL-START.md`

---

## 🗺️ 路线图

### 第二阶段（进行中）
- [ ] 增强 retry、lease recovery 和 watchdog 机制
- [ ] 深化 OpenClaw 外部执行桥
- [ ] 完善 handoff contract 与结果结构
- [ ] 丰富 board / rollup / status card 的可观察性

### 第三阶段（规划中）
- [ ] 向 durable runtime 形态演进
- [ ] 更完整接入 Temporal
- [ ] 建立更强的自动恢复与调度治理能力
- [ ] 将多 Agent 协作升级为更稳定的工程化任务系统

---

## 💡 产品方向

这个项目不是另一个聊天机器人，而是一个偏 **多 Agent 任务基础设施** 的 runtime。

核心想表达的能力包括：

- 把任务状态从聊天记录中抽离出来
- 把协作关系、handoff 和调度做成结构化对象
- 让 supervisor 真正基于 runtime 做决策
- 为复杂多 Agent 系统提供可持续演进的控制面

---

## 📌 当前状态

当前已经具备 **v1 最小可交付 runtime** 的骨架，能够支撑任务创建、状态迁移、投影生成、handoff 和 supervisor 检查。  
下一步重点，是把它从本地可运行版本继续推向更稳定的 durable runtime 形态。

---

<div align="center">

Made for multi-agent orchestration, structured handoffs, and runtime-driven execution.

</div>
