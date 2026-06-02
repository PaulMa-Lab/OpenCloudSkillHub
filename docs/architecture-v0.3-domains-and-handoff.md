# OpenCloudSkillHub 架构建议 v0.3：通用学校 + 领域目录 + 交接机制

> 状态：架构分析草案（不含代码）。回应产品演进：两类能力 / 领域系统目录 / 学习路径 / 人机交接。
> 关系：在 v0.2（architecture.md）、课程包契约、ADR-001/002/003 之上做**增量**，不推倒重来。
> 原则：对过激或自相矛盾处明确 pushback，不照单全收。

---

## 0. 与已有实现的关系（不重启）

已经建好且验证通过的部分**保持不变**：
- 平台核心 `mcp-server/`（FastMCP，Python 3.12，stdio）。
- 课程包契约 `docs/skill-package-contract.md` + `registry/skill.schema.json` + 校验器 `validate_skill_package`。
- 系统级 resources：`system://guide`、`school://curriculum`、`system://changelog`、`skills://catalog`。
- 泛化只读工具：`list_skills` / `search_skills` / `get_skill_detail` / `validate_skill_package`。
- ADR-001（模型 A：Hub 不执行）、ADR-003（平台 skill-agnostic）—— 这两条是本次演进的地基，**不放松**。

本次演进新增的是「**领域目录层**」和「**学习路径推荐**」，以及对「**人机交接**」归属的明确判断。

---

## 1. 核心心智：三层联邦（federation）

```
┌──────────────────────────────────────────────────────────────┐
│  Agent（无状态客户端，自带 LLM 的判断力）                       │
└───────┬───────────────────────────────────┬──────────────────┘
        │ 1. 来学校问"这个任务去哪学"          │ 3. 直接连领域系统干活
        ▼                                     ▼
┌─────────────────────────┐         ┌──────────────────────────────┐
│ OpenCloudSkillHub（元层）│  指路    │ 领域系统（各自独立 MCP）       │
│ - 通用技能学校           │ ───────▶│  RecruitOS / EcommerceOps ... │
│ - 领域系统【目录/指针】  │         │  - 领域 guide / methodology    │
│ - 学习路径推荐           │         │  - 领域 tools                  │
│ - 通用技能课程包         │         │  - 领域【状态/数据/审计】       │
│ ⚠ 不持有领域知识/状态    │         │  - 人机交接【实例/状态】        │
└─────────────────────────┘         └──────────────────────────────┘
        │ 2. 教通用技能(OCR/PDF/表格...)
        ▼
   用户本机（宿主 Agent 在用户批准下执行安装/调用）
```

一句话：**Hub 是"元层"——它教通用技能、给领域系统发"地址 + 入学须知"，但不替领域系统保存知识、不保存任务状态、不执行领域业务。** 智能（理解用户自然语言任务）主要在 **Agent** 侧，不在 Hub 侧。

> 核心原则：**General capability is centralized; domain competence is local.** Hub 守住"通用 + 指路"，领域守住"情境 + 状态"。任何让 Hub 开始囤积领域内容或任务状态的设计，都要被拒绝。

---

## 2. Q1 · 平台核心怎么设计

平台核心 = **目录 + 教学内容暴露 + 泛化计算 + 指路**，全部 skill/domain-agnostic。能力分四组：

| 组 | 职责 | 已有/新增 |
|---|---|---|
| 通用技能目录 | 扫 `skills/`，catalog、search、detail、校验 | 已有 |
| 教学内容暴露 | 把 `system/*` 和课程包的 guide 暴露成 resources | 已有（system 级）；课程级待 M3 内容 |
| 泛化执行支持 | `detect_environment` / `generate_install_plan(skill_id)` / `get_verification_plan(skill_id)` / `diagnose_error(skill_id, logs)` | 新增（M4，全泛化） |
| 领域目录 + 指路 | 扫 `domains/`，`list_domain_systems` / `get_domain_system_detail` / `recommend_learning_path` | 新增（本次） |
| 反馈 | `submit_course_feedback` | 新增（写 Hub 本地 JSONL） |

**硬约束**：平台核心**不**持有任何领域 guide 全文、不持有任何任务状态、不执行领域业务、不代理转发领域 MCP 的请求。它只持有"指针 + 通用知识 + 泛化计算"。

---

## 3. Q2 · skill package 标准结构

已由 `docs/skill-package-contract.md` 定义（manifest + guide/* + assets + requirements，校验器已实现）。本次演进**只需小增量**：

- manifest 增加可选字段 `kind: general`（默认）以区别于 domain；为将来"通用技能 vs 领域内课程"留位，但 MVP 只有 general。
- 可选字段 `success_criteria`（成功标准的结构化声明，呼应你说的"声明依赖、风险和成功标准"）——目前散落在 verify/guide，提一个显式字段更利于推荐与反馈对齐。
- 其余结构不变。**不**为了 domain 而改课程包契约——domain 是另一套 contract（见 Q3）。

> 结论：课程包结构已经够用，本次几乎零改动。这正是 ADR-003 解耦的红利。

---

## 4. Q3 · domain system registration 设计

领域注册是**与课程包平行的第二类 contract**，放在 `domains/<id>.yaml`，由平台扫描成 `domains://catalog`。它**只是一张"入学卡 + 地址"**，不含领域知识全文。

建议字段（domain registration schema v0.1）：
```yaml
schema_version: "1"
id: recruitos
name: RecruitOS
domain: recruiting
summary: 招聘领域 AI Native system；教 Agent 在本系统内完成招聘任务。
mcp_endpoint: https://zhaopin.songtao.me/mcp
transport: streamable-http        # 明确传输方式，Agent 才知道怎么连
entry_resource: system://guide     # 入学第一读（在【领域系统自己的】MCP 上）
also_read:                          # 进入后还应读什么（URI 属于领域系统）
  - system://changelog
  - system://methodology/jd-generation
teaches: [resume_screening, pipeline_management, jd_generation, interview_preparation]
requires_general_skills: [pdf-extraction, structured-reporting]   # 指向 Hub 的通用课程 id
keywords: [招聘, 简历, JD, hiring, recruiting, pipeline]            # 供 recommend 匹配
safety_level: production_data      # 提示：连上即可能触及生产数据
status: active
maintainer: { name: ... }
# trust 由平台在 registry/trust.yaml 赋予，禁止自声明（与课程同规）
```

**校验规则（复用校验器思路）**：必填字段、`mcp_endpoint` 必须是 https、`requires_general_skills` 必须能在 catalog 解析到、`trust` 不可自声明、`keywords/teaches` 非空（否则无法被推荐）。

> ⚠️ **Pushback / 安全面**：domain registration 引入了一个**新的信任边界**——Hub 会告诉 Agent"去连这个 URL 并按它说的做"。一个恶意/被篡改的注册条目可以把 Agent 导向敌对 MCP（重定向 / 类 SSRF 风险）。因此：
> - 领域条目必须有 **trust 等级**（official/community/unverified），与课程同规，由平台赋予、不可自封。
> - **连接一个新的领域 MCP endpoint 属于"危险动作"，必须经用户批准**（等同于"访问外部服务"），写进 safety 总则。
> - **MVP 只接受本地维护的 `domains/*.yaml`（由 Hub 维护者提交、committed 入库）**，不开放用户在线注册。在线注册 = 第二阶段，且必须先有 trust + 审核机制。

---

## 5. Q4 · recommend_learning_path 怎么工作

这是最容易做歪的工具。它**听起来像一个智能路由器，但绝不能在 Hub 里实现成一个 LLM 路由器**。

**设计原则：dumb / declarative / 给证据不给裁决。**
- 输入：`task`（自然语言）。
- 做的事：**轻量声明式匹配**——把 task 的关键词与各 domain 的 `keywords/teaches`、各 skill 的 `capabilities/tags` 做重叠/包含匹配，打个朴素分。**不在 Hub 内跑 LLM、不做语义理解。** 语义理解是**调用方 Agent**（它自带 LLM）的职责。
- 输出：**带证据的候选清单 + 入学指引**，并显式声明"这是建议，最终判断由你做"：
```json
{
  "task_echo": "帮用户招聘电商运营",
  "domain_candidates": [{
    "id": "recruitos", "name": "RecruitOS",
    "why": "matched keywords: 招聘, 运营; teaches: jd_generation, pipeline_management",
    "confidence": 0.0,                      // 朴素分，可为 0/留空，不假装精确
    "how_to_enter": {
      "mcp_endpoint": "https://zhaopin.songtao.me/mcp",
      "transport": "streamable-http",
      "read_first": ["system://guide", "system://changelog", "system://methodology/jd-generation"]
    },
    "requires_general_skills": ["pdf-extraction", "structured-reporting"],
    "trust": "official",
    "user_approval_note": "连接此领域 MCP 前需用户批准（可能触及生产数据）"
  }],
  "general_skill_candidates": [{ "skill_id": "pdf-extraction", "why": "...", "confidence": 0.0 }],
  "notes": "建议性结果。连接新 MCP 端点、安装通用技能均需用户批准。最终判断由你（Agent）做出。"
}
```

> ⚠️ **Pushback**：不要把它包装成"Hub 替你决定该用哪个系统"。Hub 给的是**有依据的候选 + 怎么进门**，不是裁决。这样 Hub 保持 domain-agnostic（它只读注册卡的自声明字段），可靠性也不依赖一个藏在 Hub 里的脆弱分类器。

---

## 6. Q5 · OCR：哪些属于平台，哪些属于课程

这一点你在第十节**不小心回归了**：你又列出了 `recommend_ocr_setup / verify_ocr_install / diagnose_ocr_error / run_sample_ocr` 这些 **OCR 专属 tools**。这与 ADR-003 和你自己的原则 3 直接冲突。**必须保持泛化**。

| 第十节列的（OCR 专属） | 正确归属（已在 ADR-003 定过） |
|---|---|
| `recommend_ocr_setup` | → 课程 guide/recipes 的"引擎选择矩阵"数据 + `install_profiles`；Agent 推理 |
| `verify_ocr_install` | → 泛化 `get_verification_plan(skill_id)`，宿主执行课程的 verify 脚本 |
| `diagnose_ocr_error` | → 泛化 `diagnose_error(skill_id, logs)`，检索课程 troubleshooting |
| `run_sample_ocr` | → 宿主按 recipes + runner 资产执行（非平台工具） |
| `detect_environment` | 这个**本就是泛化平台工具**，保留（按 skill_id 读课程声明的探测项） |

**属于平台（泛化）**：catalog/search/detail、`detect_environment`、`generate_install_plan(skill_id)`、`get_verification_plan(skill_id)`、`diagnose_error(skill_id, logs)`、`validate_skill_package`、`recommend_learning_path`、领域目录工具、feedback。

**属于 OCR 课程（数据/资产）**：七份 guide、引擎选择矩阵、`install_profiles`（rapidocr/tesseract...）、verify/smoke 脚本、runner 模板、samples、troubleshooting 知识、safety 声明、success_criteria。

> 结论：平台一行 OCR 代码都不该有。第十节的 OCR 专属 tool 列表请按上表替换为泛化工具。

---

## 7. Q6 · HumanTask / ApprovalTask / ConnectorTask 放哪？

这是本次最重要的架构判断。直接回答：

**运行态的任务实例与状态 → 放领域系统（不是 Hub）。共享的"抽象/词汇/schema" → 作为一份可被教的规范，Hub 可以"教"，但 Hub 不持有任何实例。**

理由（全部来自你自己的原则 7："状态沉淀在领域系统"）：
- HumanTask 有 `status / assignee / 超时 / 凭证 / 回填` —— 这是**有状态、长生命周期**的东西。Hub 是**无状态知识/指路层**，一旦它开始存任务状态，就变成了一个隐形的领域系统，违背定位。
- 招聘的"发布岗位 HumanTask"天然属于招聘上下文，应存在 RecruitOS 的 DB 里（和 job/JD/resume/audit 一起），这样断线换 Agent 也能续。

但"两边都需要一种抽象"也对——所以：
- **共享的是"任务类型学(taxonomy)"与最小 schema**，作为 Hub 的一份**通用方法论资源**（例如 `school://handoff-model` 或一门通用技能 `task-handoff`）来教 Agent："遇到非标流程，请用 Auto/Approval/Human/Connector 四类显式交接，而不是在聊天里硬接。"
- **各领域系统各自实现**这套 schema 的存储与流转。Hub 只教概念，不存数据。

**与已有安全模型的统一**（重要洞察）：这四类其实是我们已有"风险/审批模型"在领域侧的镜像——
| 交接类型 | = 已有概念 |
|---|---|
| AutoTask | 只读/无副作用，Agent 自主 |
| ApprovalTask | `approval_required` 的步骤，需用户批准 |
| HumanTask | 必须人做；Agent 只准备材料 + 建待办 + 追踪 |
| ConnectorTask | 访问外部平台（最高风险，需批准） |

所以不需要发明全新体系，而是把同一套风险/审批语义**在领域系统里落成有状态的任务对象**，在 Hub 里落成**教学规范**。

> ⚠️ **Pushback**：任何"在 Hub 里建一个 task store / 待办中心"的提议都应否决。Hub 存了任务状态，就不再是学校了。

---

## 8. Q7 · 第一阶段最小实现范围（修订版）

保留已建（core/contract/validator/system resources/泛化只读工具），**新增**：

**A. 领域目录层（本次重点，纯本地）**
- `domains/recruitos.yaml`（指向已存在的 RecruitOS MCP，作为唯一 seed 领域）。
- domain registration schema + 校验（复用校验器骨架）。
- resource `domains://catalog`；tools `list_domain_systems` / `get_domain_system_detail`。
- tool `recommend_learning_path`（dumb/declarative，见 Q4）。

**B. 泛化执行支持（为 OCR 闭环，全泛化）**
- `detect_environment` / `generate_install_plan(skill_id)` / `get_verification_plan(skill_id)` / `diagnose_error(skill_id, logs)`。
- 真机验证默认 profile = RapidOCR（ADR-002）。

**C. 一门 seed 通用课程：OCR（内容）**
- `skills/ocr/` 全套 manifest + guide + assets，通过 `validate_skill_package`。
- **注意定位**：这是"内容/课程作者"的活，不是平台逻辑；MVP 用**本地目录新增**方式落地（与你第十节"第一版只支持本地目录新增课程"一致）。它存在的意义是**验证闭环**，不是平台功能。

**D. 交接机制：只交付"教学规范"，不交付运行态**
- 一份 `school://handoff-model` 资源（或通用方法论文档），教 Auto/Approval/Human/Connector 四类显式交接。
- **不**在 Hub 建任何 task store。

**E. 反馈**
- `submit_course_feedback`（写 Hub 本地 JSONL）。

**最小闭环验收**：Agent 来 Hub → `recommend_learning_path("帮用户招聘电商运营")` → 得到 RecruitOS 候选 + 入学指引（含"需批准连接") → 同时被提示需要 pdf-extraction/OCR 等通用技能 → 在用户批准下学会 OCR（装/验/用）→ 经批准连 RecruitOS（领域执行属于 RecruitOS 项目，不在本 MVP 内实现）。

> Hub MVP 的边界到"**指对路 + 教会通用技能 + 给出领域入学指引**"为止。**领域系统内部的 guide 化是 RecruitOS 自己的工程**，是另一个 workstream，不塞进 Hub。

---

## 9. Q8 · 必须明确不做（防跑偏）

- ❌ Web UI、Docker、复杂 marketplace。
- ❌ 用户在线上传/分享/审核/评分/社区治理（第二阶段；需先有 trust + 审核）。
- ❌ 评测中心 / 排行榜 / Agent 路由器（第二阶段自然长出）。
- ❌ 在 Hub 里实现 LLM 智能路由（recommend 必须 dumb/declarative）。
- ❌ **Hub 托管/镜像/代理领域系统的 guide 全文**（`domain://recruitos/guide` 不作为 Hub resource；领域 guide 留在 RecruitOS 自己的 MCP）。
- ❌ **Hub 持有任务状态 / HumanTask 实例 / 待办中心**（状态归领域系统）。
- ❌ Platform Playbook 商店（招聘平台 playbook 属于 RecruitOS；Hub 不囤积平台攻略）。
- ❌ 任何 OCR/领域专属逻辑进平台核心（保持 skill/domain-agnostic）。
- ❌ connector 实装（第十节也说先做 playbook 不做 connector）。
- ❌ 自动学习闭环（反馈只落盘供人看）。

---

## 10. Q9 · Python FastMCP vs Node

**Python FastMCP（官方 mcp SDK）—— 已落地，继续。**
- 通用技能生态（OCR/PDF/表格/数据清洗）几乎都是 Python；安装/验证脚本也是 Python，单语言避免跨语言 shelling。
- 我们已经有一个跑通 stdio 握手、resources/tools 都验证过的 Python server，无理由换。
- Node 仅在"Hub 要做重 Web 前端"时才有优势——而我们明确不做 Web UI。

---

## 11. Q10 · 集中 pushback（不照单全收）

1. **`domain://recruitos/guide` 不该是 Hub resource。** Hub 只存"注册卡 + 指针"，领域 guide 留在 RecruitOS 的 MCP。否则 Hub 变成所有领域文档的镜像，必然与源头漂移，且违背原则 4/7。
2. **第十节重新列了 OCR 专属 tools，违反 ADR-003。** 按 Q5 表替换为泛化工具。
3. **recommend_learning_path 不能是 Hub 内的智能路由器。** dumb/declarative，给候选 + 证据，让 Agent 判断。
4. **HumanTask 等运行态状态不进 Hub。** Hub 只教交接"概念/schema"，状态归领域系统。
5. **domain 注册引入远程 endpoint 信任面。** 需 trust 等级 + 用户批准连接；MVP 只用本地 committed 的 `domains/*.yaml`。
6. **Platform Playbook 是 marketplace 苗头。** 招聘平台 playbook 属于 RecruitOS，不进 Hub MVP。
7. **"就业指导中心"应是 directory + dispatcher（指路 + 交接），不是 decider/executor。** Hub 不替领域决策、不执行领域业务。
8. **milestone 3（写 OCR 课程）确实是"内容"而非"平台逻辑"——你说得对。** 但 MVP 仍需**至少一门 seed 课程**来验证闭环，否则平台是空的、无法证明它能承载课程。所以把"平台机制开发"（dev）与"课程内容编写"（content，可由用户/作者承担）显式分开，但 seed OCR 必须有人写出来（MVP 阶段就是我们写，作为 reference）。
9. **领域系统的 guide 化是独立 workstream（RecruitOS 的活），不是 Hub 的活。** 别把两个项目混进一个仓。

---

## 12. 对里程碑计划的修订

| 里程碑 | 内容 | 性质 |
|---|---|---|
| M1 ✅ | 平台脚手架 + system resources + 泛化只读工具 | 平台 dev（已完成） |
| M2 ✅ | 课程包契约 + `validate_skill_package` + catalog 校验 | 平台 dev（已完成） |
| **M3（重定位）** | **OCR seed 课程内容**（manifest+guide+assets，本地目录，过校验） | **内容/课程作者**（非平台逻辑；MVP 我们写一份 reference） |
| **M4（新）** | **领域目录层**：domain registration 契约+校验、`domains://catalog`、`list/get_domain_system`、`recommend_learning_path`、`domains/recruitos.yaml` seed | 平台 dev |
| **M5（新）** | **泛化执行支持** + 真机：`detect_environment`/`generate_install_plan`/`get_verification_plan`/`diagnose_error`，真机装 RapidOCR | 平台 dev + 真机 |
| **M6** | **交接教学规范** `school://handoff-model`（仅教学，无状态）+ `submit_course_feedback` | 平台 dev（轻） |
| **M7** | 端到端 Agent 测试：recommend_learning_path → 学 OCR → 给出 RecruitOS 入学指引 | 验证假设 |

> 领域系统内部 guide 化、connector、用户上传、评测中心 —— 全部第二阶段。

---

## 附：一句话定调
OpenCloudSkillHub 是 **Agent 的通用技能学校 + 领域系统的目录与指路台 + 显式交接的教学者**。它**教通用技能、指对路、教交接规范**；它**不**囤领域知识、**不**存任务状态、**不**执行领域业务、**不**做智能路由。守住这条线，项目就不会从"学校"退化成"又一个什么都想干的中台"。
