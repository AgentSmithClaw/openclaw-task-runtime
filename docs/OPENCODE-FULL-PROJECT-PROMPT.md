# OpenCode 执行提示词：OpenClaw Task Runtime 全项目版

你现在要继续实现一个完整工程项目，而不是只做某个零散 Phase。

## 项目名称
OpenClaw 多 Agent 持续任务系统 / Task Control Plane / Harness-first runtime

## 你的角色
你现在不是来补几份文档，也不是来做分布式 brainstorm。
你是这个项目的**主实现工程师**，目标是把现有 starter pack、项目计划、当前本地代码，推进成一个真正可运行的 OpenClaw Task Runtime。

执行原则：
- 单主责实现
- 先做出最小可运行闭环，再扩展
- 以本地工作树为准，不脑补“已完成”
- 不把主线拆成多个 agent 拼装
- 不把 schema/config/TODO 误判为实现完成
- source of truth 必须是 task DB，而不是 markdown

---

## 上游输入材料
请把以下两份文件视为背景材料和上游输入：

1. `openclaw_task_runtime_starter.zip`
   - 真实路径：`/home/baiyuxi/.openclaw/media/inbound/openclaw_task_runtime_starter---004ffa50-4eb7-4e79-bd8e-eb0a8b6ccee9.zip`

2. `OpenClaw_Project_Plan.docx`
   - 真实路径：`/home/baiyuxi/.openclaw/media/inbound/OpenClaw_Project_Plan---612b1e6d-0dd6-44cc-b820-79cc818ad935.docx`

说明：
- starter zip = starter pack / 实施包来源
- project plan = 项目背景、目标与阶段计划来源

---

## 项目背景
这是一个 OpenClaw 多 Agent 持续任务系统，目标不是“问一句做一句”，而是改造成：

- 任务对象驱动
- Task DB 作为 source of truth
- Harness-first runtime
- OpenClaw 作为 edge runtime
- 后续可迁移到 Temporal

核心定位：
- Picard = supervisor / orchestrator，不是 scheduler
- Uhura = projection / rollup / notification plane，不是状态真相
- heartbeat / cron = scheduler only
- Feishu / group chat = notification plane only
- 真正的状态真相必须在 task DB

---

## 当前阶段判断（非常重要）
当前项目不是从零开始，也不是已完成。

### 已完成
- starter pack 已导入
- SQL DDL 已落地
- runtime 配置已在
- schemas / templates / policies / agent contracts 已在
- bootstrap 初始化脚本已在
- 已补过一轮 Phase 1 核心代码
- 当前本地已有最小 runtime 代码，而不只是空骨架

### 尚未完成
- Phase 1 还没完整验收闭环
- Phase 2 还没真正落地
- Phase 3 的最小业务链路还没跑通
- Phase 4 的 supervisor / collector / projection / migration 还没展开

### 当前准确判断
- Phase 0.5（starter + bootstrap）已完成
- Phase 1（runtime 最小骨架）已进入后半段
- Phase 2 / 3 / 4 仍未完成

不要把“有文件 / 有 schema / 有 config”误判成“实现完成”。

---

## 项目根目录
请以这个目录为唯一工作根目录：

`/home/baiyuxi/.openclaw/workspace/openclaw-task-runtime`

---

## 当前已知目录结构
```text
openclaw-task-runtime/
├─ 00_overview/
│  └─ package_map.md
├─ config/
│  ├─ agents/
│  ├─ dashboards/
│  ├─ openclaw/
│  ├─ policies/
│  ├─ runtime.yaml
│  └─ temporal/
├─ data/
│  └─ runtime.db
├─ docker/
│  └─ docker-compose.temporal.dev.yaml
├─ env/
│  ├─ openclaw.env.example
│  └─ temporal.env.example
├─ runtime/
│  ├─ boards/
│  │  ├─ ROLLUP.md
│  │  └─ WORK-BOARD.md
│  └─ tasks/
│     └─ registry.json
├─ schemas/
│  ├─ agent_result.schema.json
│  ├─ handoff.schema.json
│  ├─ laforge-result.schema.json
│  ├─ picard-result.schema.json
│  ├─ spock-result.schema.json
│  ├─ sulu-result.schema.json
│  ├─ task_state.schema.json
│  ├─ uhura-result.schema.json
│  └─ worf-result.schema.json
├─ sql/
│  └─ 001_task_control_plane.sql
├─ src/
│  └─ openclaw_task_runtime/
│     ├─ __init__.py
│     ├─ __main__.py
│     ├─ bootstrap.py
│     └─ runtime_v1.py
├─ IMPLEMENTATION-NEXT-STEPS.md
├─ README-LOCAL-START.md
├─ README.md
└─ manifest.txt
```

---

## 当前已知实现状态
已知 `src/openclaw_task_runtime/runtime_v1.py` 已覆盖的内容：
- task create / list
- event append
- lifecycle state machine v1
- registry 同步
- WORK-BOARD 生成
- ROLLUP 生成
- 最小 CLI 入口

已知最近相关提交：
- `6f0ccff feat: bootstrap openclaw task runtime starter`
- `34d6174 feat: implement phase1 task runtime core`

说明：
- `34d6174` 表示已经做过第一轮 Phase 1 核心实现
- 但还不能视为整个项目完成，也不能视为 Phase 1 已正式验收通过

---

# 整个项目的 4 个 Phase

## Phase 1：搭最小 runtime 骨架
先落：
1. task registry / task schema
2. state machine v1
3. task event log
4. work-board / rollup 生成

### Phase 1 完成标准
- 能创建 task
- 能追加 event
- event 能驱动 task 状态变化
- 能生成 registry / board / rollup
- 合法状态迁移通过
- 非法状态迁移被阻止
- 文档命令与真实实现对齐

---

## Phase 2：接 OpenClaw 执行桥
再接：
1. dispatcher
2. agent turn bridge
3. handoff runtime
4. stale / blocked / retry 规则

### Phase 2 完成标准
- queued task 能被 dispatcher 扫描与 claim
- task 能转成可供 OpenClaw agent 消费的执行输入
- handoff 能形成最小 child / parent 推进逻辑
- stale / blocked / retry 有最小可用规则

---

## Phase 3：打通最小闭环
先只跑通一条最小业务链：
- root task
- spec
- frontend/backend handoff
- QA
- rollup

### Phase 3 完成标准
- 至少一条真实任务链可以跑通
- 多阶段任务状态可以正确推进
- handoff / child task / rollup 关系闭环成立
- 最终输出可用于 supervisor/汇总层消费

---

## Phase 4：增强与系统化
最后再补：
- supervisor 规则
- Uhura collector
- projection / status card
- migration / 接线层

### Phase 4 完成标准
- supervisor 能基于 runtime 状态作出最小调度/升级判断
- Uhura 能消费 rollup / projection 输出
- projection / status card 可读且稳定
- 为未来迁移/接线层留出清晰边界

---

# 你的任务目标
你这次的工作不是只做某个局部，而是要对整个项目负责。

但执行顺序必须是：

1. **先把 Phase 1 收口到验收完成**
2. **再做 Phase 2 的最小可用实现**
3. **然后尝试推进到 Phase 3 的最小闭环**
4. **最后把 Phase 4 作为增强层能做多少做多少**

不要一上来扑向 Phase 4，也不要跳过 Phase 1/2/3 的主干实现。

---

# 具体执行要求

## Step 1：审视当前实现
先阅读并理解：
- `README.md`
- `README-LOCAL-START.md`
- `IMPLEMENTATION-NEXT-STEPS.md`
- `config/runtime.yaml`
- `sql/001_task_control_plane.sql`
- `schemas/task_state.schema.json`
- `schemas/agent_result.schema.json`
- `schemas/handoff.schema.json`
- `src/openclaw_task_runtime/bootstrap.py`
- `src/openclaw_task_runtime/runtime_v1.py`
- `src/openclaw_task_runtime/__main__.py`

目标：
- 搞清当前实现边界
- 找出四个 Phase 的准确起点
- 不重复造轮子

## Step 2：完成 Phase 1
重点检查并补强：
- state transition 合法性
- root / parent / child 行为
- event -> state patch 逻辑
- registry / board / rollup 一致性
- 文档与当前实现一致性

并跑一个最小样例链完成验收。

## Step 3：实现 Phase 2 最小版
优先落：
- dispatcher v0
- agent turn bridge
- handoff runtime 起步版
- stale / blocked / retry 最小规则

目标是：
- 不是大而全
- 而是最小可用、可继续接线

## Step 4：推进 Phase 3 最小闭环
至少尝试跑一条：
- root task
- spec
- frontend/backend handoff
- QA
- rollup

如果无法整条打通，也要明确阻塞点在哪里，不要含糊说“理论上支持”。

## Step 5：视情况推进 Phase 4 起步项
如果前面主线推进顺利，可开始：
- supervisor 规则起步版
- Uhura collector 输入/输出契约
- projection/status card 的最小结构
- migration / 接线边界说明

注意：Phase 4 是增强层，不应反客为主。

---

## 非目标 / 不要做的事
不要把范围做散：
- 不要把主线拆给多个 agent 各写一部分
- 不要只补文档不补代码
- 不要一上来接 Temporal
- 不要只写 schema/config/TODO 就说支持了
- 不要过度设计一个大而全框架，却没有本地可验证结果
- 不要假装某个 Phase 已完成

暂时不要优先做：
- Temporal durable runtime 全落地
- 完整 collector / status card 体系
- 复杂 supervisor 编排系统
- 大规模 UI/notification 包装

这些可以留给后续，但前提是主干 runtime 已经能跑。

---

## 工程原则
请遵守：
- 小步提交，但保持主线连续
- 能复用现有结构就复用
- 优先 Python 标准库
- 结构清晰，不乱引依赖
- source of truth = DB
- markdown = projection，不是真相
- heartbeat / cron 不承担状态真相角色

---

# 全项目验收口径

## Phase 1 验收
- task/event/state/projection 闭环成立
- 文档可执行

## Phase 2 验收
- dispatcher / bridge / handoff / retry 最小版落地

## Phase 3 验收
- 至少一条真实任务链打通

## Phase 4 验收
- supervisor / Uhura / projection / migration 起步结构明确

---

## 输出格式要求
完成后请按这个结构输出：

### 1. Summary
一句话说明整个项目推进到了哪个阶段

### 2. Phase Status
分别说明：
- Phase 1 完成度
- Phase 2 完成度
- Phase 3 完成度
- Phase 4 完成度

### 3. Files Changed
列出改动文件

### 4. What Was Implemented
按能力列出：
- task
- event
- state machine
- projection
- dispatcher
- bridge
- handoff
- retry/stale/blocked
- sample chain / rollup
- supervisor / collector / status card / migration
- CLI / docs

### 5. Validation
写清楚：
- 执行了什么命令
- 生成了哪些文件
- 观察到了什么结果
- 哪些 Phase 被实际验证通过

### 6. Remaining Gap
明确说明：
- 还没做什么
- 为什么没做
- 属于哪个 Phase 的剩余项

### 7. Suggested Next Step
只给一个主建议，不要列一堆虚建议

---

## 最后提醒
这不是一个“写点材料”的任务。
这是一个强耦合 runtime 实施项目。

请用这条原则收口：

> 先把最小控制面做成真能跑的东西，再接执行桥，再跑通最小闭环，最后做监督与增强层。

如果当前实现已经覆盖了部分内容，请在现有基础上补齐，而不是推翻重来。
