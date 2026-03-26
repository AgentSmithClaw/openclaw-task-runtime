# OpenCode 执行提示词：OpenClaw Task Runtime（Phase 1 收口 + Phase 2 起步）

你现在要继续实现一个本地工程任务。

## 任务名称
OpenClaw 多 Agent 持续任务系统 / Task Control Plane / Harness-first runtime

## 你的角色
你不是来写零散文档，也不是来做分散式 brainstorm。
你现在是这个 runtime 的主实现工程师，目标是把现有 starter pack 落成**第一版可运行实现**。

执行原则：
- 单主责实现
- 先打通最小闭环
- 不要把主线拆成多个 agent 拼装
- 优先让系统跑起来，再谈增强
- 以当前本地工作树为准，不要脑补“已经完成”

---

## 上游输入材料
请把这两份文件视为背景输入：

- `openclaw_task_runtime_starter.zip`
- `OpenClaw_Project_Plan.docx`

说明：
- `starter.zip` = starter pack / 实施包来源
- `Project Plan.docx` = 项目背景、目标与阶段计划来源

---

## 当前项目背景
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
- group chat / Feishu = notification plane only
- 真正的状态真相必须在 task DB

---

## 当前阶段判断
当前项目不是从零开始，也不是已完成。
准确状态是：

### 已完成
- starter pack 已导入
- SQL DDL 已落地
- runtime 配置已在
- schemas / templates / policies / agent contracts 已在
- bootstrap 初始化脚本已在
- 已补过一轮 Phase 1 核心代码
- 当前本地已有最小 runtime 代码，而不只是空骨架

### 尚未完成
- 还没有完整打通 Phase 1 验收
- 还没有验证最小任务链
- 还没有进入 Phase 2 的完整执行桥实现
- dispatcher / bridge / handoff / retry recovery 仍未完整落地

---

## 项目根目录
项目目录：

`/home/baiyuxi/.openclaw/workspace/openclaw-task-runtime`

请以这里为唯一工作根目录。

---

## 当前目录结构（已知）
请优先阅读并基于以下真实路径工作：

```text
openclaw-task-runtime/
├─ 00_overview/
│  └─ package_map.md
├─ config/
│  ├─ agents/
│  │  ├─ laforge.yaml
│  │  ├─ picard.yaml
│  │  ├─ spock.yaml
│  │  ├─ sulu.yaml
│  │  ├─ uhura.yaml
│  │  └─ worf.yaml
│  ├─ dashboards/
│  │  └─ push_rules.yaml
│  ├─ openclaw/
│  │  ├─ commands.yaml
│  │  └─ hooks.yaml
│  ├─ policies/
│  │  ├─ approval_gates.yaml
│  │  ├─ lifecycle.yaml
│  │  ├─ retry_and_lease.yaml
│  │  ├─ stale_rules.yaml
│  │  └─ visibility.yaml
│  ├─ runtime.yaml
│  └─ temporal/
│     ├─ queues.yaml
│     └─ workflow_topology.yaml
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
请先理解当前真实状态，不要重复造轮子。

### 已知 `runtime_v1.py` 已覆盖的大项
- task create / list
- event append
- lifecycle state machine v1
- registry 同步
- WORK-BOARD 生成
- ROLLUP 生成
- 最小 CLI 入口

### 关键判断
不要把“已有这些文件”误判成“Phase 1 已完成”。
当前更准确的状态是：

- Phase 0.5（starter + bootstrap）已完成
- Phase 1（runtime 最小骨架可运行）已进入后半段，但仍需验证与补口
- 现在重点是：把 Phase 1 真正收口

---

## 当前提交记录（与你相关的最近提交）
可参考：

- `6f0ccff feat: bootstrap openclaw task runtime starter`
- `34d6174 feat: implement phase1 task runtime core`

说明：
- `34d6174` 代表已经做过第一轮 Phase 1 核心实现
- 但还不能视为 Phase 1 已验收完成

---

## 你的明确目标
这次只做两段连续任务：

# 第一段：完成 Phase 1
# 第二段：在 Phase 1 完成后，开始 Phase 2 最小可用版

但顺序必须严格：
- 先把 Phase 1 收口到可验收完成
- 然后再进入 Phase 2

不要跳阶段。

---

# 第一段：Phase 1 定义与目标

## Phase 1 = runtime 最小骨架可运行
必须真正具备这 4 类能力：

### 1. task registry / task schema
不是只有空 JSON 文件，而是：
- task 能创建
- task 能读取
- task 能列出
- task 的最小投影结构稳定

### 2. state machine v1
不是只有概念或 schema，而是：
- 有明确 lifecycle state
- 有 transition guard
- 非法状态迁移会报错
- 合法状态迁移会更新 task

### 3. task event log
不是只有表结构，而是：
- 能 append event
- event 能入 DB
- event 能落 jsonl
- event 能驱动 task 状态变化

### 4. work-board / rollup 生成
不是“暂无任务”占位，而是：
- board 从真实任务状态投影生成
- rollup 从真实任务状态聚合生成
- registry / board / rollup 三者内容一致

---

## Phase 1 具体工作
请按下面顺序执行：

### Step 1：审视当前实现
阅读并理解这些文件：
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
- 搞清楚当前已经做了什么
- 找出 Phase 1 还缺什么
- 不要重复造轮子

### Step 2：补完 Phase 1 缺口
重点检查并补强：
- state transition 合法性
- 任务创建后的 root / parent / child 行为
- event -> state patch 逻辑是否完整
- board / rollup 的生成是否稳定
- registry 投影是否足够清晰
- README / local start 是否与当前真实实现一致

如果发现结构不合理，可以重构，但不要大拆大改成另一套体系。

### Step 3：跑一个最小样例链
至少验证一个最小样例流程，例如：
- create root task
- append progress event
- append claimed / doing / blocked / done 之类的合法事件
- 生成 registry
- 生成 WORK-BOARD
- 生成 ROLLUP

如果你愿意，也可以做一个更完整但仍最小的样例：
- root task
- child spec task
- child delivery task
- child qa task
- rollup

注意：这一步是 Phase 1 验证，不是正式 Phase 3 全实现。

### Step 4：修正发现的问题
基于样例链运行结果：
- 修 bug
- 修不一致
- 修 board / rollup 投影错误
- 修文档不匹配处

### Step 5：给出 Phase 1 最终交付
交付必须包含：
1. 改了哪些文件
2. Phase 1 现在完成到什么程度
3. 怎么验证
4. Phase 2 的准确起点是什么

---

# 第二段：Phase 2 定义与范围

## 只有在 Phase 1 收口后，才开始 Phase 2

## Phase 2 = 接 OpenClaw 执行桥的最小可用版
优先做这 4 块：

### 1. dispatcher v0
- 扫描 `queued` task
- claim task
- 形成最小 dispatch 闭环

### 2. agent turn bridge
- 把 task 对象转成可发送给 OpenClaw agent 的执行输入
- 为后续实际 agent 执行留出桥接点
- 先做最小可用，不做大而全抽象

### 3. handoff runtime
- 支持最小 `delegate / transfer / review / escalate`
- 支持 child task / parent task 关系推进
- 只做起步版，不要重度框架化

### 4. stale / blocked / retry 最小规则
- 能识别最小 stale / blocked / retry 条件
- 能对任务状态做最小恢复/升级处理
- 先做可用版，不做过度设计

---

## 非目标 / 不要做的事
这次不要把范围做散。

### 不要
- 不要再把主线拆成多个 agent 各做一部分
- 不要只补文档不补代码
- 不要一上来接 Temporal
- 不要一上来做完整 supervisor / collector / projection 卡片系统
- 不要假装 Phase 1 已完成
- 不要只写 schema / config / TODO 然后说“已支持”
- 不要过度设计一个大而全框架，却没有本地可验证结果

### 暂时不要优先做
- structured agent result ingest 全实现
- Uhura collector / status card / Feishu notification plane
- 完整 supervisor 规则
- Temporal durable runtime 落地

这些都属于更后面的阶段，除非它们是完成当前 Phase 的必要最小补丁。

---

## 代码风格与工程原则
请遵守：
- 小步提交，但保持主线连续
- 能复用现有结构就复用
- 尽量保持 `runtime_v1.py` 结构清晰；如需拆分，也要保持模块边界清楚
- 不要引入没必要的新依赖
- 优先 Python 标准库
- source of truth 必须是 DB，不是 markdown
- markdown board / rollup 是 projection，不是状态真相
- heartbeat / cron 不要承担状态真相角色

---

## Phase 1 验收标准
只有满足下面条件，才能说 Phase 1 基本完成：

### 验收项 A：任务最小闭环可跑
- 能创建 task
- 能追加 event
- event 会驱动状态变化
- 能重新生成 registry / board / rollup

### 验收项 B：状态机真实生效
- 合法迁移通过
- 非法迁移被阻止
- 任务状态变化有清晰规则

### 验收项 C：投影可读
- `runtime/tasks/registry.json` 有真实任务数据
- `runtime/boards/WORK-BOARD.md` 反映真实状态
- `runtime/boards/ROLLUP.md` 有聚合结果
- 三者内容相互一致

### 验收项 D：文档可执行
- `README-LOCAL-START.md` 中命令能对得上当前实现
- 本地验证步骤清晰
- 不依赖“读代码猜怎么跑”

---

## 输出格式要求
完成后请按这个结构输出，不要散写：

### 1. Summary
一句话说明：
- Phase 1 完成度
- Phase 2 起步到什么程度

### 2. Files Changed
列出改动文件

### 3. What Was Implemented
按能力列出：
- task
- event
- state machine
- projection
- dispatcher
- bridge
- handoff
- retry/stale/blocked
- CLI / docs

### 4. Validation
写清楚你是怎么验证的，包括：
- 执行了什么命令
- 生成了哪些文件
- 观察到了什么结果
- Phase 1 怎么证明完成
- Phase 2 起步版怎么证明已落地

### 5. Remaining Gap After This Round
明确说明：
- 还没做什么
- 为什么它们属于后续阶段，不是这轮必须项

### 6. Suggested Next Step
只给一个主建议，不要列一长串虚建议

---

## 最后提醒
这不是一个“写点材料”的任务。
这是一个强耦合 runtime 实施任务。

请用这条原则收口：

> 先把最小控制面做成真能跑的东西，再把它接到 OpenClaw 执行桥上。

如果你发现当前实现已经部分覆盖了某些点，请在其基础上补齐，而不是推翻重来。
