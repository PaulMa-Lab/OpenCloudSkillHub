# OpenCloudSkillHub 架构设计文档（草案 v0.1）

> 状态：设计草案，供后续实现使用，非对外文案。
> 日期：2026-06-02
> 范围：整体架构 + 第一个 MVP skill（OCR）。
> 原则：不假设一切可自动完成；不确定处直接标注；对过激设想给出 pushback。

---

## 0. 阅读前必须先接受的一个核心判断（贯穿全文）

整个项目最危险也最容易被忽略的问题不是「OCR 怎么装」，而是：

**「真正会改变用户机器的那条命令，到底是谁执行的？审批发生在哪一层？」**

存在两种架构：

- **模型 A（Advisory / 顾问型，推荐）**：Hub 的 MCP server 主要提供 **只读 resources** 和 **只读/纯计算 tools**（环境检测、生成安装计划、验证、诊断）。真正会写文件、装依赖、跑 shell、下模型的动作，**交给宿主 Agent（Claude Code 等）用它自己的 Bash/Write 工具去执行**，从而复用宿主已有的权限审批 UI。Hub 永远不碰用户机器的可变状态。
- **模型 B（Executive / 执行型）**：Hub 自己提供 `install_ocr` 这类会真正跑 `pip install` 的 tool，并自己实现一套审批机制。

**本设计推荐模型 A，理由：**

1. MCP 协议本身没有「服务端弹审批框」的标准原语。在 Claude Code 里，审批发生在 **宿主的工具权限层**（某个 tool 不在 allowlist 就会弹窗）。如果 Hub 自己跑命令，等于在重新发明一套审批，还绕开了宿主用户已经信任的那套。
2. 模型 A 让「教 Agent 学会能力」这个目标依然成立：guide 负责教，`generate_install_plan` 负责产出可执行步骤，宿主 Agent 负责（在用户批准下）执行，`verify_*` 负责检查。验证与环境检测是只读的，天然适合放进 Hub。
3. 安全边界更干净：Hub = 知识 + 判断；宿主 = 执行 + 审批。一旦 Hub 被攻击或 guide 写错，最坏后果是「给了一个坏计划」，而不是「直接在用户机器上跑了坏命令」。

> **不确定性标注**：模型 A 的代价是「最后一公里」依赖宿主 Agent 忠实执行计划。如果某个宿主不具备 shell 执行能力（纯聊天型 Agent），那它就只能读 guide、看计划，无法真正落地安装。这是可接受的——那种宿主本来也不该自动装东西。MVP 阶段我们以 Claude Code 这类有 shell 的宿主为目标。

文档后续的「是否需要审批」一栏，都建立在模型 A 之上：**Hub 的工具几乎都是只读的；可变操作以「计划」形式交回宿主执行，审批在宿主侧发生。**

---

## 0.5 平台核心与课程包的解耦（架构第一不变量）

> 这条优先级**高于本文其余所有设计**；任何地方与之冲突，以本节为准。（v0.2 增补）

**不变量**：OpenCloudSkillHub 是「**承载很多课程的平台 / 协议 / 注册与分发层**」，不是「**带 OCR 的平台**」。OCR 只是第一门 reference course，**任何 OCR 专属逻辑都不得写进平台核心**。

两层结构：
- **平台核心（opencloudskill-hub）**：registry/catalog、搜索、推荐、guide 暴露、安装计划生成、安全风险标注、版本管理、feedback 收集、贡献者治理、课程质量校验。**完全 skill-agnostic。**
- **课程包（skill package，如 skill-ocr）**：自带 `skill.yaml` + `guide/*` + `assets`。平台只「读取、校验、暴露」这些包，不理解其内部领域逻辑。

**验收式不变量（必须能通过，否则边界已漏）**：新增一门课（如 skill-pdf-extraction）= 往 `skills/` 丢一个合规包（或注册一个外部 skill repo），**对 `mcp-server/` 零代码改动**。如果加一门课必须改核心代码，说明 OCR/某 skill 的逻辑漏进了平台。

### 0.5.1 对 §6 工具层的修正（重要，覆盖原 §6.2）
原 §6.2 的 `recommend_ocr_setup / verify_ocr_install / diagnose_ocr_error / run_sample_ocr / ocr_image_remote` 是 OCR 专属逻辑，**放进平台核心会破坏本不变量**。修正：平台核心只暴露**泛化、按 `skill_id` 参数化的工具**，OCR 专属行为全部沉到「数据（manifest+guide）+ 资产（assets，宿主执行）」。

| 原 OCR 专属 tool | 解耦后的归属 |
|---|---|
| `recommend_ocr_setup`（选引擎） | → **guide/recipes 里的「引擎选择矩阵」数据**，Agent 读后自行推理；跨 skill 组合用泛化的 `recommend_skill_stack` |
| `verify_ocr_install` | → 泛化 `get_verification_plan(skill_id)` 返回 `{脚本路径, 期望输出, 怎么跑}`；**宿主执行** `assets/verify_ocr.py`（模型 A），Agent 比对 |
| `diagnose_ocr_error` | → 泛化 `diagnose_error(skill_id, logs)`：对该包的 `troubleshooting.md` 做检索匹配（匹配逻辑泛化，知识在包里） |
| `run_sample_ocr` | → 不是平台工具；是**宿主按 recipes + runner 资产执行**的动作（可选泛化 `get_run_recipe(skill_id)`） |
| `ocr_image_remote` | → 远程推理是 skill 专属可执行能力，**不进平台核心**；由课程包以可选资产/宿主动作提供，默认关闭 |

于是平台核心工具集是**全泛化**的：
`list_skills` / `search_skills` / `get_skill_detail` / `recommend_skill_stack` / `generate_install_plan(skill_id)` / `detect_environment(skill_id?)` / `get_verification_plan(skill_id)` / `diagnose_error(skill_id, logs)` / `submit_skill_feedback` / `validate_skill_package(path)`。
所有 OCR 特性都是**数据**，不是核心代码。（与「模型 A」相互强化：核心不跑任何 skill 代码，skill 代码只在宿主侧、用户批准下执行。）

> `detect_environment` 之所以仍是泛化平台工具：环境探测（OS/Python/venv/GPU/磁盘/网络）本身与 skill 无关；**「该探测哪些包/前置」由 skill 在 manifest 里声明**，工具读声明去探，而不是内置「OCR 要查 onnxruntime」这种知识。

### 0.5.2 贡献机制（围绕课程包，不碰核心）
未来贡献者 / 其他 Agent 贡献课程 = 提交一个 skill package（manifest + guide + assets），**不改 Hub 核心代码**。平台对包做六件事：
1. 校验 manifest 完整性；
2. 校验 guide 引用的脚本/资产真实存在（即 **guide↔脚本一致性**，本就是头号技术债，§13）；
3. 标注 / 复核 `risk_level`；
4. 暴露成 MCP resources；
5. 收集成功 / 失败反馈；
6. 维护可信等级（`official` / `community` / `unverified`）。

样例 manifest（契约草形，正式 schema 后续单独定）：
```yaml
id: ocr
name: OCR Skill
version: 0.1.0
maintainer: opencloudskill
capabilities: [image_to_text, scanned_pdf_to_text]
risk_level: medium
resources:
  guide: guide/guide.md
  install_windows: guide/install-windows.md
  safety: guide/safety.md
tools_required: [shell_optional, file_read, file_write]   # 宿主能力声明
verification:
  smoke_test: assets/verify_ocr.py
```

### 0.5.3 三仓演进（边界先画清，先别真拆）
- `opencloudskill-hub` —— 平台核心（MCP server / registry / search / safety / feedback）
- `opencloudskill-ocr` —— 第一门课程（OCR skill package）
- `opencloudskill-catalog` —— 官方 / 社区索引（有哪些 skill、版本、来源、可信等级）

**MVP 阶段单仓**，但目录按「未来可拆」组织：`skills/ocr` 在心智上是「平台托管的第一份课程内容」，不是平台代码。**别第一天就真拆三仓**（会凭空冒出工程负担：版本协调、跨仓 CI、引用解析），但边界从第一行代码起就清晰。

---

## 1. 产品定位

### 1.1 OpenCloudSkillHub 是什么
一个 **面向 AI Agent 的能力学习与装配中心（capability hub / agent school）**，以 MCP 协议对外暴露：
- 一批 **结构化、Agent 可读的 guide（resources）**，教 Agent「有哪些能力、何时用、怎么装、怎么验证、怎么排错」；
- 一批 **只读/计算型 tools**，帮 Agent 检测环境、生成安装计划、验证安装、诊断错误、回传反馈。

它不卖某个具体能力，而是卖「让 Agent 自己学会获取并装配能力」的这套流程。

### 1.2 与四类东西的区别

| 对比对象 | 它们的逻辑 | OpenCloudSkillHub 的不同 |
|---|---|---|
| 普通 Skill / 插件市场 | 人浏览、人判断、人安装、人配置，再告诉 Agent 用 | Agent 自己读 guide、自己判断该装什么、自己生成计划、向用户申请批准后落地 |
| 普通 README | 给人看的散文，结构松散，不保证可执行、不保证与脚本同步 | guide 是「第一类公民」，结构化、分层（install/verify/troubleshooting/safety/recipes），面向 Agent 的决策与执行 |
| 普通 OCR API | 你调一个 endpoint 拿结果，能力在云端，黑盒 | 这里不是「替你做 OCR」，而是「教会 Agent 在用户本机把 OCR 能力装起来并自检」。OCR 只是被教的内容 |
| 普通插件 SDK | 面向开发者写代码集成 | 面向运行时的 Agent 做即时学习与装配，零人工集成 |

### 1.3 服务的是人还是 Agent
**第一类用户是 Agent。** 人是 Agent 背后的「审批人 / 权限持有者」。所有 resource/tool 的措辞、结构、返回格式都以「Agent 能据此决策与行动」为标准，而不是「人读着舒服」。

### 1.4 为什么更像 agent school / capability hub
传统市场假设「能力 = 一个可安装的包」；这里假设「能力 = 一份可被 Agent 内化的知识 + 一套自检方法」。Agent 来这里不是「下载一个东西」，而是「上一节课」：理解概念 → 评估自身环境是否够格 → 制定方案 → 实操 → 自测 → 失败后复盘。这就是 school 的语义。

### 1.5 OCR 在项目里的角色
**OCR = 第一个验证样本（reference skill），不是项目边界。** 选它是因为它具备「真实环境依赖、跨平台坑、本地/远程取舍、可客观验证（识别出文字就是成功）」这些能把整套机制压测出来的属性。它是「第一节课」，用来证明这套教学法本身成立。

### 1.6 MVP 要证明的假设（一句话）
> **一个此前不会 OCR 的 Agent，仅通过访问 OpenCloudSkillHub 的 MCP resources/tools，就能在一台干净的 Windows 机器上，在用户批准下，自主完成 OCR 能力的安装、验证、调用与基本排错。**

如果这个假设成立，「OpenCloudSkillHub 不是 OCR 工具，而是一套可复制到任意 skill 的教学/装配机制」才有说服力。

---

## 2. 核心理念

### 2.1 Agent-readable capability package（ARCP）
一个 skill 的物理形态 = **一个目录**，里面包含：
- **manifest**（结构化元数据：id、版本、风险等级、需要哪些 resource、声明哪些 tool）；
- **guide 集**（Markdown，分层：overview / when-to-use / install / verify / troubleshoot / recipes / safety）；
- **可执行资产**（验证脚本、smoke test、sample 输入、runner 模板）——但这些是「被计划引用的资产」，不是 Hub 自动执行的东西。

「Agent-readable」的硬标准：**Agent 读完后，不需要再问人「具体每一步怎么做」，只需要向人申请「允许我做这几步」。**

### 2.2 MCP resources vs tools 的分工
- **resources = 知识 / 状态（只读、可缓存、幂等）**：guide、安装说明、排错手册、安全边界、验证标准。Agent「读」它们来获得判断力。
- **tools = 动作 / 计算（有输入输出，可能有副作用）**：但在模型 A 下，Hub 的 tools 刻意保持「只读或纯计算」——检测环境、生成计划、跑验证、诊断日志、回传反馈。真正的副作用（装、写、下载）外包给宿主。

一句话：**resources 让 Agent「懂」，tools 让 Agent「算」，宿主让 Agent「做」。**

### 2.3 为什么 guide 比 tool list 更重要
tool list 只告诉 Agent「我能调什么」，不告诉它「什么时候该调、调之前要满足什么前提、失败了意味着什么」。**判断力来自 guide，执行力才来自 tool。** 一个只有 tools 没有好 guide 的 Hub，等于给了 Agent 一把没有说明书的电钻——它会乱用、会在不该装的时候装、会把用户机器搞坏。能力市场的真正壁垒是 guide 的质量，不是 tool 的数量。

### 2.4 Agent 如何从 guide 学会「装/验/用/排错」
- **装**：读 `skill://ocr/install/windows` → 得到分步骤、带前置条件、带风险标注的安装路径 → 交给 `generate_install_plan` 结构化 → 交宿主执行。
- **验**：读 `skill://ocr/verification`（成功长什么样）→ 调 `verify_ocr_install`（只读检查）→ 对照标准判定。
- **用**：读 `skill://ocr/recipes`（最小可用调用范式）→ 用安装阶段产出的 runner 跑真实任务。
- **排错**：读 `skill://ocr/troubleshooting`（症状→原因→对策表）→ 把真实日志喂给 `diagnose_ocr_error` → 得到归因和下一步。

### 2.5「人告诉 Agent 去哪学，而不是告诉它每一步怎么做」
人只需说一句「你的 OCR 能力可以去 OpenCloudSkillHub 学」。Agent 自己完成从「我不会 OCR」到「我装好且验证过 OCR」的全过程。人的角色从「手把手教学 + 逐条操作」退化为「指一个学校 + 在危险动作上点头/摇头」。这就是这个项目想验证的范式迁移。

> **Pushback / 现实约束**：这里有一个被很多人忽略的 **bootstrapping 问题**——MCP resources 是被动的，Agent 不会「自动」去读 `system://guide`。必须有机制引导它先读。方案见 §5.0 和 §11。如果不解决这个，整套「Agent 自学」会卡在第一步。

---

## 3. 总体架构

> 设计的是整个 Hub，不只是 OCR。OCR 是其中一个 skill 插槽。

```
                         ┌─────────────────────────────────────────┐
   宿主 Agent            │           OpenCloudSkillHub (MCP)         │
 (Claude Code 等)        │                                          │
        │                │  ┌────────────────────────────────────┐  │
        │  read resource │  │  Skill Registry / Catalog          │  │
        ├───────────────▶│  │  (扫描 skills/*/manifest，索引)     │  │
        │                │  └────────────────────────────────────┘  │
        │                │  ┌────────────────────────────────────┐  │
        │  read guide    │  │  Guide Resource Layer (Markdown)    │  │
        ├───────────────▶│  │  system:// / school:// / skill://  │  │
        │                │  └────────────────────────────────────┘  │
        │                │  ┌────────────────────────────────────┐  │
        │  call tool     │  │  Read-only / Compute Tools         │  │
        ├───────────────▶│  │  - Environment Detector (只读)     │  │
        │                │  │  - Install Plan Generator (纯计算) │  │
        │                │  │  - Verification Runner (只读检查)  │  │
        │                │  │  - Troubleshooting Assistant (计算)│  │
        │                │  │  - Feedback Loop (写入 Hub 本地)   │  │
        │                │  └────────────────────────────────────┘  │
        │                │  ┌────────────────────────────────────┐  │
        │                │  │  Safety / Policy Layer             │  │
        │                │  │  (给每个动作打风险标签，标注哪些   │  │
        │                │  │   必须由宿主审批后执行)            │  │
        │                │  └────────────────────────────────────┘  │
        │                └─────────────────────────────────────────┘
        │
        │  执行计划（pip/写文件/下模型/跑脚本）——在用户批准下，由宿主自己的工具完成
        ▼
   用户本机环境（venv / 模型缓存 / 图片输入）
```

各组件职责：

1. **Skill Registry / Catalog**：启动时扫描 `skills/*/skill.yaml`，构建可查询的能力目录（id、名称、标签、风险等级、状态、依赖摘要）。对外通过 `skills://catalog` resource + `list_skills`/`search_skills` tool 暴露。**唯一事实来源是各 skill 的 manifest**，catalog 是它的索引视图。
2. **Skill Guide Resources**：把每个 skill 目录下的 Markdown guide 映射成 `skill://<id>/<doc>` 这样的 resource URI。纯只读。
3. **Install Plan Generator**：输入「skill id + 环境检测结果 + 用户选定的引擎/模式」，输出 **结构化、分步、带风险标签、带回滚说明的安装计划**。它本身不执行，只产出计划。
4. **Environment Detector**：只读探测——OS/架构、Python 版本与路径、是否有 venv、是否有 GPU、关键包是否已装、磁盘空间、网络可达性（用于判断模型下载）。
5. **Verification Runner**：在「已安装」假设下做只读自检——能否 import、模型是否就位、sample 图能否识别出预期文本。返回结构化 pass/fail + 证据。
6. **Troubleshooting Assistant**：输入错误日志/症状，匹配 `troubleshooting` guide 里的「症状→原因→对策」知识，输出归因 + 建议的下一步（仍以「建议」形式，不自动执行）。
7. **Feedback Loop**：Agent 回传「装成功/装失败/缺能力/guide 与现实不符」。MVP 阶段写入 Hub 本地的 append-only 日志（JSONL），用于人工迭代 guide。**不**做自动学习闭环（见 §13 风险）。
8. **Safety / Approval Layer**：不是一个会拦截的网关，而是一个 **标注层 + 约定层**：为每个 plan step、每个 tool 打 `read_only / needs_approval / dangerous` 标签，并在 guide 与 tool 输出里显式声明「这一步必须经用户批准」。真正的拦截/弹窗由宿主完成。

---

## 4. 项目目录设计

```
D:\Github\OpenCloudSkillHub\
├─ mcp-server/                 # MCP 服务端（Python / FastMCP）
│   ├─ src/
│   │   ├─ server.py           # 入口：注册 resources + tools + instructions
│   │   ├─ registry.py         # 扫描 skills/，构建 catalog
│   │   ├─ resources/          # 系统级 resource 提供器
│   │   ├─ tools/              # 系统级 + skill 级 tool 实现（只读/计算为主）
│   │   ├─ safety.py           # 风险标签、计划标注约定
│   │   └─ feedback.py         # 反馈写入
│   ├─ pyproject.toml
│   └─ README.md               # 给人看的：怎么起这个 server
├─ registry/                   # 索引层（skill catalog / indexing / 可信等级）
│   ├─ catalog.json            # 由扫描生成的 skill 索引（id/版本/来源/trust）
│   └─ trust.yaml              # official/community/unverified 等级与来源声明
├─ skills/                     # 平台【托管的课程内容】，非平台代码；每个子目录 = 一个课程包(ARCP)
│   └─ ocr/                    # 第一门 reference course（心智上 = opencloudskill-ocr 仓的内容）
│       ├─ skill.yaml          # manifest（机器读）
│       ├─ guide/              # Markdown guide（Agent 读）
│       │   ├─ overview.md
│       │   ├─ when-to-use.md
│       │   ├─ install.windows.md
│       │   ├─ verify.md
│       │   ├─ troubleshooting.md
│       │   ├─ recipes.md
│       │   └─ safety.md
│       ├─ assets/             # 被计划引用的可执行资产
│       │   ├─ verify_ocr.py   # 验证脚本（只读自检）
│       │   ├─ smoke.py        # smoke test
│       │   ├─ runner_template.py  # 生成本地 runner 用的模板
│       │   └─ samples/        # sample 图片 + 期望文本
│       └─ requirements/       # 各引擎的依赖清单（如 rapidocr.txt）
├─ docs/                       # 给人看的项目级文档（本文件在此）
│   ├─ architecture.md
│   └─ decisions/              # ADR：关键决策记录
├─ examples/                   # 端到端示例：模拟 Agent 学 OCR 的完整 transcript
├─ scripts/                    # 开发/运维脚本（起 server、跑测试、校验 guide↔脚本一致性）
└─ tests/                      # server 与 catalog 的自动化测试
```

**扩展到更多 skill 的方式**：新增 `skills/<new>/`，写好 `skill.yaml` + guide + assets，registry 自动收录，无需改 server 代码。这是「能力是数据，不是代码」的体现——`mcp-server` 是稳定的运行时，`skills/` 是可无限增长的内容层。

> 注：`assets/` 里的脚本要做到「**guide 描述什么，脚本就做什么**」。二者不同步是本项目最现实的技术债（§13），`scripts/` 里要放一个一致性校验器。

---

## 5. MCP resources 设计

### 5.0 Bootstrapping（必须先解决）
为缓解「Agent 不会主动读 guide」：
- 在 MCP server 的 **`instructions` 字段**（initialize 时返回）写明：「使用任何 skill 前，先读 `system://guide`，再查 `skills://catalog`」。
- 提供一个低摩擦的入口 tool（如 `list_skills`），其 **description 本身**就引导「先读 system guide」。
- guide 之间用显式「下一步该读哪个 resource / 调哪个 tool」串成一条链，让 Agent 顺着走。

> 不确定性：不同宿主对 `instructions` 的尊重程度不一。这是需要在 §11 工作流里靠「tool 描述 + guide 内链」双保险兜底的开放问题。

### 5.1 系统级 resources

| URI | 内容 | Agent 何时读 | 读后动作 |
|---|---|---|---|
| `system://guide` | Hub 是什么、怎么用、resource/tool 总览、安全总则、推荐工作流 | 接入 Hub 后**第一件事** | 建立全局心智模型，知道下一步去查 catalog |
| `system://changelog` | Hub 与各 skill 的版本变更 | 怀疑 guide 过时、或复用历史结论前 | 判断缓存的知识是否还有效 |
| `school://curriculum` | 「学习路径」：一个 skill 从认知到掌握应经过的阶段（认知→评估环境→计划→执行→验证→排错→反馈），以及通用安全原则 | 第一次学任何 skill 前 | 内化标准学习流程，套用到具体 skill |
| `skills://catalog` | 所有 skill 的索引（id/名称/标签/风险/状态/一句话用途） | 确定「要不要某能力、有没有现成 skill」时 | 选定一个或多个候选 skill，去读其 guide |

### 5.2 OCR skill resources

| URI | 内容 | Agent 何时读 | 读后动作 |
|---|---|---|---|
| `skill://ocr/guide` | OCR skill 总览 + when-to-use + 本 skill 的 resource/tool 导航 | 选定 OCR 后第一份读物 | 决定是否继续、规划后续读哪些 |
| `skill://ocr/install/windows` | Windows 下分步安装：venv 策略、引擎选择、依赖、模型、smoke test、回滚 | 决定要装、且已知环境后 | 配合 `generate_install_plan` 产出可执行计划 |
| `skill://ocr/troubleshooting` | 症状→原因→对策表（numpy/opencv 冲突、paddle 装不上、模型下载失败、中文乱码等） | 任何一步失败时 | 把日志喂给 `diagnose_ocr_error`，对照采取对策 |
| `skill://ocr/recipes` | 最小可用调用范式：给一张图/PDF，怎么得到文本；常见参数 | 安装验证通过后、真正用之前 | 用 runner 跑真实任务 |
| `skill://ocr/safety` | 本 skill 的风险点与必须审批项（装依赖、下模型、读本地文件、上传远程） | 生成计划前、调用任何可变动作前 | 标记哪些步骤需向用户申请批准 |
| `skill://ocr/verification` | 「成功长什么样」的客观标准 + 验收清单 | 装完后、排错后 | 调 `verify_ocr_install` 并对照标准判定通过与否 |

设计要点：**每份 guide 末尾都显式写「下一步：读 X / 调 Y」**，把被动 resource 织成主动流程。

---

## 6. MCP tools 设计

> 模型 A 下：Hub 的 tool 几乎都 `read_only=true`。`needs_approval` 一栏多数为「否（Hub 侧）」——因为可变执行不在 Hub。带副作用的只有「写反馈」和可选的「远程 OCR」。

### 6.1 系统级 tools

| tool | 输入 | 输出 | 只读 | 需审批 | 场景 |
|---|---|---|---|---|---|
| `list_skills` | 无 / `{status?}` | `[{id,name,tags,risk,status,summary}]` | 是 | 否 | 概览全部能力；也是引导读 system guide 的入口 |
| `search_skills` | `{query, tags?}` | 同上（过滤后） | 是 | 否 | 「我需要 X 能力，有没有现成 skill」 |
| `get_skill_detail` | `{skill_id}` | `{manifest, resource_uris[], tool_names[], risk_summary}` | 是 | 否 | 选定某 skill 后拉全貌 |
| `recommend_skill_stack` | `{task_description, env?}` | `{recommended:[{skill_id,reason,confidence}], notes}` | 是 | 否 | 根据任务推荐能力组合；明确给 confidence，可为空 |
| `generate_install_plan` | `{skill_id, env_report, choices?}` | `{steps:[{id,intent,command?,writes?,risk,approval_required,rollback}], summary, est_download_mb}` | 是（纯计算，不执行） | 否（生成计划本身不需要）；**但计划里的步骤多数 approval_required=true** | 把 guide+环境变成可执行步骤，交宿主执行 |
| `submit_skill_feedback` | `{skill_id, outcome, stage, logs?, guide_mismatch?}` | `{accepted:true, id}` | 否（写 Hub 本地） | 否（写的是 Hub 自己的日志，不碰用户机器） | 回传成功/失败/缺能力/guide 不符 |

### 6.2 OCR 相关 tools

> ⚠️ **已被 §0.5.1 修正**：下表的 OCR 专属工具违反「平台核心 skill-agnostic」不变量，**不再作为平台核心工具实现**。其能力被改写为「泛化工具（按 skill_id 参数化）+ 课程包的数据/资产」。下表仅保留为「这门课需要哪些能力」的需求清单，用于推导泛化工具与 manifest 字段——**不要据此在核心里写 OCR 代码**。

| tool | 输入 | 输出 | 只读 | 需审批 | 场景 |
|---|---|---|---|---|---|
| `detect_environment` | `{}` 或 `{python_path?}` | `{os, arch, python:{version,path,in_venv}, gpu, installed_pkgs, disk_free_mb, network_ok}` | 是 | 否（只探测，不改） | 评估本机够不够装 OCR、该选哪个引擎 |
| `recommend_ocr_setup` | `{env_report, lang_needs, doc_types}` | `{engine, mode:'local'|'remote', reason, confidence, fallbacks[]}` | 是 | 否 | 在 Paddle/Rapid/EasyOCR/Tesseract/远程之间给建议 |
| `verify_ocr_install` | `{python_path, engine}` | `{import_ok, model_ready, sample:{passed, recognized_text, expected, score}}` | 是（只跑只读自检脚本） | 否 | 装后/排错后判定是否真的可用 |
| `diagnose_ocr_error` | `{logs, stage, engine?}` | `{likely_cause, evidence, suggested_actions[], matched_troubleshooting_ref}` | 是 | 否 | 把真实报错归因到 troubleshooting 条目并给下一步 |
| `run_sample_ocr` | `{python_path, image_path?}` | `{text, boxes?, elapsed_ms}` | **否（会调用已装引擎跑推理；若读用户提供的图则触及本地文件）** | **是（读本地文件 / 跑推理需用户许可）** | 装好后跑一张真实图，端到端证明能力可用 |
| `ocr_image_remote`（可选） | `{image_path, provider}` | `{text, provider, cost?}` | **否（上传文件到远程）** | **是（外发数据，高风险，必须显式批准）** | 本地装不动时的兜底；默认关闭 |

设计要点：
- **`generate_install_plan` 的每个 step 自带 `risk` / `approval_required` / `rollback`**——这是安全层的落点。宿主据此对「需要批准」的步骤逐条征求用户同意。
- `run_sample_ocr` 是「跑推理 + 读本地图」，所以它是少数有副作用、需审批的 OCR tool；但它**不安装任何东西**。
- `ocr_image_remote` 默认 **disabled**，要装到 catalog 也标 `risk: high`，因为它把用户数据外发。

---

## 7. OCR skill 作为 MVP 的设计

### 7.1 为什么 OCR 适合做第一个 skill
- **依赖真实、坑真实**：numpy/opencv/paddle 版本冲突、系统级二进制（Tesseract）、模型下载——能把「环境检测/安装计划/排错」全链路压测出来。
- **可客观验证**：sample 图里有「已知文本」，识别出来=成功，没有则失败。验证不靠主观判断，适合证明「Agent 真的学会了」。
- **本地/远程都成立**：天然能演示「该不该外发数据」的审批决策。
- **跨平台差异明显**：正好契合「先做 Windows」的约束，且能暴露平台特异性问题。

### 7.2 OCR skill 要教会 Agent 什么
1. OCR 是什么、能/不能做什么（不是万能文档理解）。
2. 何时该用 OCR、何时不该（§7.3/7.4）。
3. 在本机环境下选哪个引擎、本地还是远程。
4. 在 Windows 上怎么不污染全局地装好。
5. 怎么客观验证装好了。
6. 怎么调用、怎么读结果。
7. 失败时怎么归因、怎么回滚。

### 7.3 Agent 何时应选 OCR
任务里出现「从**图片 / 扫描件 / 截图 / 图片型 PDF**中提取文字」且**文本不可直接复制/不可由文本层获取**时。

### 7.4 Agent 何时**不**应自动装 OCR
- PDF/文档本身有**文本层**，直接抽文本即可（先试 `pdfplumber`/`pypdf`，别上来就装 OCR）。
- 任务只是一次性的小图，**远程一次调用**比本地装一套更划算（但远程要审批，见 §10）。
- 用户**未授权**写文件/装依赖/下模型——此时只能给计划，不能擅自装。
- 环境检测显示**磁盘不足 / 无网络 / Python 缺失**——先报告障碍，别硬装。

### 7.5 本地 vs 远程取舍

| 维度 | 本地 OCR | 远程 OCR |
|---|---|---|
| 数据隐私 | 不出本机 ✅ | 文件外发 ⚠️（必须审批） |
| 安装成本 | 一次性较重 | 几乎为零 |
| 离线可用 | ✅ | 依赖网络 |
| 大批量成本 | 装好后边际成本低 | 按量计费可能贵 |
| 首次延迟 | 安装+下模型慢 | 立即可用 |
| MVP 验证价值 | **高**（要验证的就是「装/验/排错」） | 低（黑盒调用，证明不了学习能力） |

**结论：MVP 主线是本地 OCR**（因为项目要验证的就是「学会装/验/用/排错」）；远程仅作为本地失败时的、需显式批准的兜底，且默认关闭。

---

## 8. OCR engine 选择策略

| 引擎 | 中文 | 英文 | Windows 安装难度 | CPU 可用 | 依赖复杂度 | 模型下载 | 适合 MVP |
|---|---|---|---|---|---|---|---|
| **PaddleOCR** | 很强 | 强 | **高**（paddlepaddle 在 Win/CPU 上易与 numpy 冲突、版本敏感） | 可 | 重（paddle 全家桶） | 首次自动下载，较大 | 中（准但脆） |
| **EasyOCR** | 强 | 强 | 中（要装 PyTorch，**下载体积大**，CPU 版尚可） | 可（慢） | 重（torch 系） | 模型较大 | 中 |
| **Tesseract / pytesseract** | 中文一般（需中文语言包，配置繁琐） | 强 | 中（**需装系统级二进制**，非纯 pip，要配 PATH/语言包） | 可（快） | 轻（py 侧） | 语言包 | 中（英文场景好，中文偏弱） |
| **RapidOCR（onnxruntime，强烈建议纳入对比）** | 强（PP-OCR 同源模型） | 强 | **低**（纯 pip，`onnxruntime` 无需 paddle/torch） | **可（快、轻）** | **轻** | 模型小、随包或一次下载 | **高** |

> **Pushback / 主动补充**：你给的三个候选里，**没有一个在「Windows + CPU + 中文 + 安装顺滑」四项上同时达标**：PaddleOCR 准但 Windows/CPU 安装最容易踩坑（paddle 与 numpy/opencv 版本地狱）；EasyOCR 要拖 PyTorch（动辄数百 MB~GB）；Tesseract 不是纯 pip、中文配置麻烦。
>
> 因此我**建议 MVP 默认引擎选 RapidOCR**（= PaddleOCR 的模型跑在 onnxruntime 上，纯 pip、轻、CPU 友好、中文好），把 PaddleOCR 作为「追求最高精度时的进阶选项」，Tesseract 作为「纯英文/已装好二进制」的轻量备选，EasyOCR 作为另一备选。这样最能让「干净 Windows 机器上一次装成」这个 MVP 目标达成。
>
> 不确定性：RapidOCR 的模型下载与中文权重的具体体积、以及在最老 Win10 上的 onnxruntime 兼容性，需要在里程碑 4 真机验证后再敲定。如果实测不顺，回退顺位为 Tesseract（英文）/ PaddleOCR（中文高精度）。

---

## 9. 本地安装流程设计（Windows 重点）

设计目标：**绝不污染全局 Python；失败可一键回滚；产出可复用 runner。**

1. **永远创建独立 venv**：在一个 Hub 约定的工作目录下，例如 `%USERPROFILE%\.opencloudskillhub\envs\ocr\`，`python -m venv`。**不**用全局 `pip install`。好处：回滚 = 删目录，干净彻底。
2. **不污染全局**：所有依赖只进该 venv；runner 也只引用该 venv 的解释器路径。
3. **装依赖（分层、可控）**：
   - 先 `python -m pip install -U pip`；
   - 按选定引擎装**钉死版本**的依赖清单（来自 `skills/ocr/requirements/<engine>.txt`，如 `rapidocr_onnxruntime`、配套 `numpy`/`opencv-python-headless` 的兼容版本）；
   - **用 `opencv-python-headless` 而非 `opencv-python`**，避免 GUI 依赖在 server/headless 环境报错；
   - numpy 版本钉死，避免被某个包拉到不兼容的大版本。
4. **smoke test**：装完立刻跑 `assets/smoke.py`——只验证「import 成功 + 引擎可初始化」，不下大模型。快速失败。
5. **模型就位**：首次推理会触发模型下载。安装计划必须**把「下载模型」标为单独的、需审批的、显示预计体积的步骤**，并提供「可预下载」选项，避免在真实任务里才卡住。
6. **依赖冲突处理**：
   - 钉版本 + 用 headless opencv + 选 onnxruntime 系（RapidOCR）天然避开 paddle/torch 的大坑；
   - 若仍冲突，`diagnose_ocr_error` 对照 `troubleshooting` 给出「降级 numpy / 换引擎」建议；
   - **每个引擎一套互不干扰的依赖清单**，不混装。
7. **可复用本地 runner**：安装成功后，从 `runner_template.py` 生成一个固化了「venv 解释器路径 + 引擎 + 默认参数」的 `ocr_runner.py`，放在 Hub 工作目录。之后所有 OCR 调用都走它——**装一次，用多次**。
8. **失败回滚 / 停止**：任一步失败 → 停止，不继续往下装；提供回滚 = 删除该 venv 目录（因为隔离，删了不影响系统）。计划里每个 step 自带 `rollback` 文案。**绝不在失败后盲目重试或换源乱试。**

> 关键安全设计：上述每一个会「写文件 / 装依赖 / 下模型」的步骤，在模型 A 下都是 `generate_install_plan` 产出的、`approval_required=true` 的 step，由**宿主**在用户点头后执行。Hub 自己不跑这些。

---

## 10. 安全与权限边界

### 10.1 必须请求用户批准（高风险 / 有副作用）
- 安装依赖（pip install）
- 写文件（建 venv、生成 runner、写配置）
- 执行任意 shell 命令
- 下载模型（占磁盘 + 走网络）
- 访问本地图片 / PDF（读用户数据）
- 上传文件到远程 OCR 服务（**最高风险：数据外发**，默认关闭）

### 10.2 Agent 可自主完成（只读 / 无副作用）
- 读任何 resource / guide
- 查 skill catalog、搜索、看 detail
- `detect_environment`（只探测不改）
- `generate_install_plan`（只产计划不执行）
- `diagnose_ocr_error`（只分析日志）
- `recommend_*`（只给建议）

### 10.3 边界落地机制（重申模型 A）
- 审批**不是 Hub 弹窗**，而是：Hub 把可变步骤标 `approval_required`，**宿主**在执行这些步骤（pip/写/下载/读图/上传）时，触发它自己的权限审批 UI 向用户确认。
- `safety.py` + 每个 skill 的 `safety.md` 定义「什么算危险」；`generate_install_plan` 据此给每步打标。
- **默认拒绝原则**：远程上传、任意 shell 这类，默认 disabled / 需显式开启 + 单独批准。
- **最小授权**：读图只读「这一张/这一批」指定文件，不申请「整个磁盘」。

> Pushback：不要试图在 Hub 里做「自动判断风险并自动放行低风险动作」。MVP 阶段，凡是 §10.1 的六类，**一律走宿主审批**，宁可多问一次。自动放行的复杂度和误伤风险，不值得在验证阶段引入。

---

## 11. Agent 工作流（用户说「我需要 OCR 能力」之后）

```
0. [引导] 宿主据 server.instructions / list_skills 描述 → 先读 system://guide
1. [认知] 读 system://guide + school://curriculum → 建立「怎么在这学能力」的心智模型
2. [选能力] 调 search_skills("OCR") / 读 skills://catalog → 命中 ocr skill
3. [读课] 读 skill://ocr/guide → 再读 when-to-use → 确认任务确实需要 OCR（先排除「文档有文本层」）
4. [查环境] 调 detect_environment → 得到 OS/Python/venv/GPU/磁盘/网络
5. [定方案] 调 recommend_ocr_setup(env, 中文/英文, 文档类型) → 建议引擎(默认 RapidOCR)+本地模式
            读 skill://ocr/install/windows + skill://ocr/safety
6. [出计划] 调 generate_install_plan(ocr, env, choices) → 拿到分步计划（每步带 risk/approval/rollback/预计下载体积）
7. [请批准] 向用户逐条说明「我要建 venv / 装这些依赖 / 下约 N MB 模型 / 读你这张图」
            → 用户批准哪些就执行哪些（宿主审批层）
8. [安装] 宿主执行被批准的步骤：建 venv → 装钉版依赖 → smoke.py → （批准后）下模型 → 生成 ocr_runner.py
          任一步失败 → 停 → 进入 [诊断]
9. [验证] 调 verify_ocr_install(venv_python, engine) → 对照 skill://ocr/verification 判定 pass/fail
10.[使用] 读 skill://ocr/recipes → 调 run_sample_ocr / 用 ocr_runner 跑用户真实图（读本地图需批准）→ 交付文本
11.[失败诊断] 读 skill://ocr/troubleshooting + 调 diagnose_ocr_error(logs) → 归因 → 改方案回到 6/8；
              确实装不动 → 经显式批准走 ocr_image_remote 兜底，或回滚（删 venv）并如实报告
12.[反馈] 调 submit_skill_feedback(成功/失败/缺能力/guide与现实不符) → 供人工迭代 guide
```

> 不确定性：第 0/1 步能否稳定触发，取决于宿主是否尊重 `instructions`、是否会顺着 guide 内链走。这是 MVP 最需要真机观察的环节——如果 Agent 不肯先读 guide，整套就退化成「人又得手把手」。里程碑 5 的核心就是验证这一点。

---

## 12. MVP 边界

### 12.1 第一版**包含**
- 一个本地 Python/FastMCP MCP server（stdio）。
- system/school/skills 系统级 resources + catalog。
- 一个完整的 OCR skill：manifest + 全套 guide + verify/smoke/runner_template/samples。
- 系统级只读 tools：list/search/detail/recommend_stack/generate_install_plan/submit_feedback。
- OCR 只读/计算 tools：detect_environment/recommend_ocr_setup/verify_ocr_install/diagnose_ocr_error；+ 需审批的 run_sample_ocr。
- 安全标注层（plan step 打标 + safety.md）。
- 一份 examples/ 里的端到端「Agent 学 OCR」transcript。

### 12.2 第一版**不包含**
- 多个 skill（只有 OCR）。
- Web UI、用户系统、账号、计费。
- Docker、云部署、托管服务。
- 自动学习闭环（反馈只落盘供人看，不自动改 guide）。
- 跨平台（先只 Windows；mac/Linux 安装 guide 留空或标 TODO）。
- Hub 自动执行安装（坚持模型 A，执行在宿主）。
- 默认开启的远程 OCR。
- 大而全 marketplace 治理（搜索排序、评分、版本兼容矩阵等）。

### 12.3 成功标准
1. 在一台**干净 Windows + 仅有 Python** 的机器上，Agent 仅凭访问 Hub，**在用户逐步批准下**，把 OCR 从零装好。
2. `verify_ocr_install` 客观判定通过（sample 图识别出预期文本）。
3. Agent 能用装好的能力处理**一张用户真实图**并交付正确文本。
4. 故意制造一个安装失败（如 numpy 冲突），Agent 能经 troubleshooting + diagnose **自主定位并修复或合理回滚**。
5. 全程**没有任何 §10.1 的危险动作在用户未批准时发生**。

### 12.4 怎么证明它不是「普通 OCR API」
- 普通 API：你调 endpoint，能力在云端，机器上什么都没多。
- 这里：跑完后**用户本机多了一个隔离的、可离线复用的 OCR 环境**，且整个「装/验/排错」过程是 Agent 读 guide 自主完成的。把网线拔了，本地 OCR 仍能用——API 做不到这点。

### 12.5 怎么证明「Agent 真的通过 guide 学会了」
- **消融对照**：同一个 Agent，(a) 接 Hub vs (b) 不接 Hub 只给一句「装个 OCR」。若 (b) 明显更易失败/乱装/污染全局，而 (a) 稳定走完标准流程，则 guide 起了作用。
- **可追溯性**：记录 Agent 实际读了哪些 resource、按什么顺序、每步决策引用了 guide 的哪条——证明决策来自 guide 而非模型先验。
- **扰动测试**：把 guide 里某个关键约束（如「用 headless opencv」）改掉，观察 Agent 行为是否随之改变——变了，说明它真在读、在用 guide。

---

## 13. 已知风险与技术债

| 风险 | 说明 | 缓解 |
|---|---|---|
| Windows 环境差异 | Python 版本/PATH/权限/中文路径/杀软拦截各异 | detect_environment 充分探测；guide 列已知差异；先窄定支持矩阵 |
| Python 依赖冲突 | numpy/opencv/paddle/torch 版本地狱 | 钉版本 + 每引擎独立 venv + headless opencv + 默认选 onnxruntime 系（RapidOCR）规避 paddle/torch |
| 模型下载慢/失败 | 首次推理拉模型，可能很慢或被墙 | 下载列为独立可审批步骤、显示体积、支持预下载与镜像；失败有 troubleshooting 条目 |
| GPU/CPU 差异 | 有无 GPU 影响引擎与速度 | MVP 只承诺 CPU 路径；GPU 作为可选优化，不进 MVP 关键路径 |
| Agent 误执行安装命令 | Agent 自作主张跑危险命令 | 模型 A：Hub 不执行；危险步必经宿主审批；计划步全部打标 |
| 安全权限过宽 | 一次批准被滥用到其他动作 | 最小授权、默认拒绝、远程默认关闭、逐步批准 |
| **guide 与真实脚本不同步** | guide 说 A，assets 脚本做 B，Agent 被误导 | `scripts/` 放一致性校验器；CI 校验 guide 引用的命令/文件存在；ADR 记录变更 |
| catalog 未来膨胀治理 | skill 多了之后搜索/质量/版本/冲突难管 | **MVP 明确不解决**；只留 manifest schema 的扩展位；治理留到验证成功后 |
| Bootstrapping 不稳 | Agent 不肯先读 guide | instructions + tool 描述 + guide 内链三重引导；里程碑 5 重点观测 |
| 反馈无闭环 | 反馈只落盘，靠人改 guide | MVP 接受人工闭环；不在验证阶段做自动学习（风险更高） |

> 最该正视的两条技术债：**guide↔脚本同步** 与 **bootstrapping**。前者决定 guide 可不可信，后者决定 Agent 会不会真去读。两者任一崩了，整个范式验证就失败。

---

## 14. 推荐技术栈

| 选择项 | 建议 | 理由 |
|---|---|---|
| **MCP server 语言** | **Python + FastMCP** | OCR 生态、安装脚本、验证脚本全是 Python；单语言避免跨语言 shelling；FastMCP 写 resource/tool 简洁，支持 stdio |
| Node MCP Server | **不用** | 会被迫为每个 Python 操作 shell 出去，多一层割裂；无收益 |
| FastAPI | **MVP 不用** | MCP-first，stdio 即可；没有 HTTP 客户端需求；引入它是过度工程 |
| Web UI | **不用** | 第一类用户是 Agent，不是人浏览；做 UI 偏离验证目标 |
| Docker | **不用** | 要验证的恰恰是「用户**本机**装能力」；容器化会掩盖本地环境问题，与目标相悖。（未来若做托管远程 tool 再议） |
| **guide 格式** | **Markdown（guide 正文）+ YAML（manifest/结构化元数据）** | 二者各司其职：Markdown 承载教学性散文（Agent+人都易读），YAML `skill.yaml` 承载机器索引字段（id/version/risk/resources/tools）。**不要把教学内容硬塞进 JSON**——会牺牲可读性且 guide 的价值就在叙述 |

> 一句话栈：**Python + FastMCP（stdio）+ Markdown guide + YAML manifest，无 Web、无 Docker、无 DB（反馈用 JSONL 落盘）。**

---

## 15. 第一阶段实现计划（里程碑）

**里程碑 1 — 脚手架 + 可跑的 MCP server**
- 建目录骨架；`pyproject.toml`；FastMCP server 能 stdio 起来、能被 Claude Code 连上。
- 实现 `list_skills`（哪怕先返回空/假数据）+ `system://guide` 一份最小 guide。
- 验收：宿主能连上、能读到 guide、能调通一个 tool。

**里程碑 2 — 系统 resources + catalog**
- 定义 `skill.yaml` schema；实现 registry 扫描 `skills/`。
- 实现 `system://guide`、`system://changelog`、`school://curriculum`、`skills://catalog`，以及 `search_skills`/`get_skill_detail`/`recommend_skill_stack`/`submit_skill_feedback`。
- 验收：放一个占位 skill，能被 catalog 索引、被搜索/查详情。

**里程碑 3 — OCR skill 的 resources（内容层）**
- 写全 OCR guide（overview/when-to-use/install.windows/verify/troubleshooting/recipes/safety）。
- 准备 assets：verify_ocr.py、smoke.py、runner_template.py、samples（带已知文本的中英文图）、requirements/rapidocr.txt 等。
- 验收：Agent 能读全套 OCR guide，内容自洽、内链能把流程串起来。

**里程碑 4 — 环境检测 + 安装计划 + 验证（工具层 + 真机）**
- 实现 `detect_environment`、`recommend_ocr_setup`、`generate_install_plan`（带 risk/approval/rollback/下载体积）、`verify_ocr_install`、`diagnose_ocr_error`、`run_sample_ocr`。
- **在真实干净 Windows 上手动跑通一次完整安装**，敲定默认引擎（验证 RapidOCR 假设）、钉死依赖版本、补全 troubleshooting 真实条目。
- 验收：人按计划在真机一次装成 + 验证通过；故意制造冲突能被 diagnose 命中。

**里程碑 5 — 端到端 Agent 测试（验证假设本身）**
- 让一个未预置 OCR 知识的 Agent，仅凭 Hub，在用户逐步批准下走完 §11 全流程。
- 跑 §12.5 的消融/可追溯/扰动测试；记录 Agent 实际读了哪些 resource、决策依据。
- 验收：满足 §12.3 全部五条成功标准；产出 examples/ 里的真实 transcript。

> 里程碑 4 与 5 是**真正的风险点**（真机环境 + bootstrapping）。1~3 基本是确定性工程，4~5 才是「假设成不成立」的地方。建议在 4 完成后留出缓冲，因为依赖问题大概率会让计划返工。

---

## 附：明确的 pushback 汇总（便于决策）
0. **平台核心必须 skill-agnostic（第一不变量，见 §0.5，优先级最高）**——OCR 只能作 reference course，OCR 逻辑不得焊进核心；加一门新课要做到「零核心代码改动」。这条直接推翻了原 §6.2 的 OCR 专属工具设计。
1. **执行权要外包给宿主（模型 A）**，Hub 别自己跑危险命令、别自建审批——否则在重复造轮子且扩大攻击面。
2. **你给的三个 OCR 引擎都不完美**，Windows+CPU+中文+易装四项没有全中的；建议 MVP 默认 **RapidOCR**，Paddle 作进阶、Tesseract 作英文备选。
3. **不要做 Web/Docker/FastAPI/自动学习闭环**，全是偏离验证目标的过度工程。
4. **bootstrapping（Agent 会不会主动读 guide）是真问题**，不能假设它自动会读；必须靠 instructions+tool 描述+guide 内链三重引导，并在里程碑 5 实测。
5. **guide↔脚本同步**必须从第一天就用校验器守住，否则 guide 不可信、整套塌掉。
6. **catalog 治理、多 skill、跨平台**统统推迟，MVP 只证一件事：Agent 能不能通过 Hub 学会 OCR 的装/验/用/排错。

---

*（草案结束。建议下一步：基于本文件在 `docs/decisions/` 落 2 条 ADR——「ADR-001 采用模型 A：执行外包给宿主」「ADR-002 MVP 默认引擎 RapidOCR」——再进入里程碑 1。）*
