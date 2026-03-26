# OpenClaw Task Runtime

> Harness-first task control plane for multi-agent execution in OpenClaw.

`openclaw-task-runtime` 是一个面向 **OpenClaw 多 Agent 持续任务系统** 的最小可交付 runtime。  
它的目标不是再做一个聊天机器人，而是把多 Agent 协作从“群聊推进”升级成“任务对象驱动”。

---

## 1. 项目背景

在传统的多 Agent 协作里，经常会遇到这些问题：

- 任务状态散落在聊天记录中
- 谁负责、做到哪、卡在哪，没有稳定的 source of truth
- handoff 靠人肉转述，容易丢上下文
- supervisor / 主控经常退化成手工调度员
- heartbeat、cron、群消息被迫承担“状态真相”的职责

这个项目就是为了解决这些问题。

它把多 Agent 系统重构为：

- **Task DB = source of truth**
- **board / rollup = projection**
- **heartbeat / cron = scheduler only**
- **chat / Feishu = notification plane only**
- **Picard = supervisor / orchestrator，而不是手工调度器**

换句话说：

> 这个项目的本质，是把 OpenClaw 多 Agent 系统从“靠聊天推进任务”，升级成“靠 runtime 推进任务”。

---

## 2. 核心目标

`openclaw-task-runtime` 要解决的是：

1. **任务对象化**
   - 每个任务有明确 id、owner、phase、state、parent/root 关系

2. **状态机化**
   - 任务状态通过 event 驱动，而不是靠聊天猜测

3. **可观察化**
   - 可以直接看到 registry、work board、rollup、status card

4. **handoff 结构化**
   - agent 之间的交接有明确 contract，而不是口头描述

5. **可升级化**
   - 当前先用 SQLite / 本地 runtime 跑通，未来可迁移到 Temporal durable runtime

---

## 3. 当前已实现能力（v1）

当前仓库已经达到 **v1 最小可交付版**。

### Phase 1：最小 runtime 骨架
- task create / list / show
- task event log
- lifecycle state machine v1
- registry projection
- work board projection
- rollup projection

### Phase 2：执行桥起步能力
- dispatcher（scan & claim queued tasks）
- structured result ingest（agent bridge）
- handoff runtime（delegate / transfer / review / escalate）
- supervisor（stale / blocked / dependency / status card）

### Phase 3：最小闭环链
当前已经保留一条最小任务链示例：
- root task
- spec
- frontend
- backend
- QA
- rollup

### Phase 4：增强层起步
- supervisor 规则起步版
- status card / rollup 基础结构
- 为后续 Uhura collector / migration / durable runtime 留出边界

---

## 4. 部署后会是什么效果

项目跑起来之后，你得到的不是“一堆脚本”，而是一套 **任务控制面 + 状态机 + 看板 + handoff + 汇总能力**。

### 你会直接看到
- 当前有哪些任务
- 每个任务是谁负责
- 每个任务在哪个 phase
- 当前在 doing / blocked / done 哪个状态
- 哪个任务有 blocker
- 哪些 child task 还没完成
- 当前总览 rollup 是什么样

### 你会感受到的变化

#### 以前
- 靠聊天推进
- 靠群里追进度
- 靠记忆或人工翻记录判断任务状态

#### 之后
- 任务状态沉到 DB
- handoff 变成结构化对象
- board / rollup 可直接看
- Picard 更像真正的 orchestrator
- 多 Agent 协作更像流水线，而不是群聊工地

一句话：

> 部署后，这套系统会把 OpenClaw 多 Agent 协作从“聊天式推进”升级成“runtime 驱动推进”。

---

## 5. 目录结构

```text
openclaw-task-runtime/
├─ config/              # runtime / policy / openclaw / temporal 配置
├─ data/                # runtime.db（source of truth）
├─ docker/              # Temporal 本地开发示例
├─ env/                 # 环境变量示例
├─ runtime/
│  ├─ boards/           # WORK-BOARD / ROLLUP
│  ├─ events/           # 按天 jsonl 事件日志
│  └─ tasks/            # registry projection
├─ schemas/             # task state / agent result / handoff schema
├─ sql/                 # task control plane DDL
├─ src/openclaw_task_runtime/
│  ├─ runtime_v1.py     # 核心 runtime / state machine / projection / CLI
│  ├─ dispatcher.py     # queued task dispatch
│  ├─ agent_bridge.py   # structured result ingest
│  ├─ handoff.py        # handoff runtime
│  └─ supervisor.py     # stale / blocked / status card
├─ templates/           # task / report 模板
├─ README-LOCAL-START.md
└─ IMPLEMENTATION-NEXT-STEPS.md
```

---

## 6. 快速开始

### 初始化 runtime

```bash
cd /home/baiyuxi/.openclaw/workspace/openclaw-task-runtime
PYTHONPATH=src python3 -m openclaw_task_runtime init
```

### 查看当前任务和投影

```bash
PYTHONPATH=src python3 -m openclaw_task_runtime list-tasks
PYTHONPATH=src python3 -m openclaw_task_runtime board
```

### 创建任务

```bash
PYTHONPATH=src python3 -m openclaw_task_runtime create-task \
  --title "OpenClaw Task Runtime v1" \
  --owner picard \
  --requested-by user \
  --phase intake
```

### 追加事件

```bash
PYTHONPATH=src python3 -m openclaw_task_runtime append-event \
  --task-id <task_id> \
  --actor picard \
  --event-type progress \
  --summary "working on spec"
```

### 调度 queued task

```bash
PYTHONPATH=src python3 -m openclaw_task_runtime dispatch --lease-owner dispatcher
```

### 写入结构化结果

```bash
PYTHONPATH=src python3 -m openclaw_task_runtime ingest \
  --result '{"taskId":"<task_id>","agent":"picard","decision":"done","summary":"completed"}'
```

### 处理 handoff

```bash
PYTHONPATH=src python3 -m openclaw_task_runtime handoff create \
  --task-id <task_id> \
  --mode delegate \
  --from picard \
  --to spock
```

### 查看 supervisor 状态卡

```bash
PYTHONPATH=src python3 -m openclaw_task_runtime supervisor --status-card
```

更完整的本地运行说明见：
- [`README-LOCAL-START.md`](./README-LOCAL-START.md)

---

## 7. 最值得看的文件

如果你第一次看这个项目，建议按这个顺序：

### 看结果
- `runtime/tasks/registry.json`
- `runtime/boards/WORK-BOARD.md`
- `runtime/boards/ROLLUP.md`

### 看核心逻辑
- `src/openclaw_task_runtime/runtime_v1.py`
- `src/openclaw_task_runtime/dispatcher.py`
- `src/openclaw_task_runtime/agent_bridge.py`
- `src/openclaw_task_runtime/handoff.py`
- `src/openclaw_task_runtime/supervisor.py`

### 看项目说明
- `README-LOCAL-START.md`
- `IMPLEMENTATION-NEXT-STEPS.md`

---

## 8. 当前状态与后续路线

### 当前状态
当前仓库已经达到：
- **v1 最小可交付 runtime**
- **有稳定最小闭环链**
- **有统一 CLI 与投影结果**

### 后续增强项
后续更适合继续做的是：
1. reconciler / watchdog（lease recovery）
2. 更完整的 retry / stale / blocked 规则
3. 更深的 OpenClaw 执行桥接线
4. Temporal durable runtime
5. Uhura collector / 更完整 status card

也就是说：

> 当前阶段已经不是“能不能跑”，而是“如何继续稳定化与升级”。

---

## 9. 适用场景

这个项目适合：
- OpenClaw 多 Agent 协作系统
- 需要 task control plane 的 agent runtime
- 想把群聊推进升级为任务驱动推进
- 想先在本地 / SQLite 跑通，再逐步演进到 durable runtime

---

## 10. 一句话总结

> `openclaw-task-runtime` 是 OpenClaw 多 Agent 系统的任务控制面：它把任务状态、handoff、看板、汇总和 supervisor 能力从聊天层抽出来，沉到一个可运行、可观察、可升级的 runtime 中。
