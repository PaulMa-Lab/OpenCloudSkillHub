<!--
  resource: system://guide
  audience: AI Agent（第一类读者）。本文件用「你」称呼正在阅读的 Agent。
  role: 接入 Hub 后你应读的第一份文档。它是入口与总则，不含任何具体 skill 的领域知识。
-->

# OpenCloudSkillHub · 系统总则（system://guide）

你正在接入 **OpenCloudSkillHub**。如果你在读这段文字，说明你已到达正确的起点。**在使用任何能力（skill）之前，先读完本文件。**

---

## 1. 这里是什么

OpenCloudSkillHub 是一个**面向 Agent 的能力学习与装配中心**。它本身不替你做事，而是教你「有哪些能力、何时该用、怎么在用户机器上装好、怎么验证、怎么排错」。

- 这里的每一种能力叫一门**课程（skill package）**。课程是数据，平台是运行时。
- 平台对一门课的全部了解都来自这门课自己的 `manifest + guide + assets`。平台是 **skill-agnostic** 的——它不内置任何具体能力的逻辑。
- 第一门课是 **OCR**，它只是用来验证机制的样本，不是平台的边界。

## 2. 你必须遵守的三条总则

### 总则一：Hub 不执行，你来执行
平台只给你**知识（resources）**和**只读的计算（tools）**：环境检测、生成安装计划、给出验证计划、诊断错误。
**真正会改变用户机器的动作——装依赖、写文件、跑 shell、下模型、读本地文件、上传远程——由你用你自己的工具执行。** 平台永远不替你跑这些。

### 总则二：危险动作必须先获用户批准
下列动作在执行前**必须向用户说明并取得批准**，不得默认自动进行：
- 安装依赖 / 执行 shell 命令 / 写文件
- 下载模型（占磁盘 + 走网络）
- 读取用户的本地图片 / PDF 等文件
- **连接一个外部领域系统的 MCP 端点（可能触及生产数据，需用户批准）**
- **上传任何文件到远程服务（最高风险：数据外发，默认禁止，需显式批准）**

下列动作你可以**自主完成**，无需批准（它们都是只读/无副作用）：
- 读任何 resource / guide
- 查询、搜索 skill catalog
- 检测环境（`detect_environment`）
- 生成安装计划（`generate_install_plan`，只产计划不执行）
- 诊断错误日志（`diagnose_error`）
- 提建议、回传反馈

安装计划里的每个步骤都带 `risk` / `approval_required` / `rollback` 标记。**对 `approval_required: true` 的步骤逐条向用户征求同意**，用户批准哪些你就只执行哪些。

### 总则三：最小授权、失败即停
- 只申请完成任务所需的最小权限（读「这一张图」，不要申请「整个磁盘」）。
- 任何一步失败就**停下来诊断**，不要盲目重试、换源乱试或继续往下装。
- 失败可回滚（多数安装是建在独立 venv 里的，回滚 = 删该目录）。

## 3. 你能用的 resources 与 tools

**系统级 resources（只读）**
- `system://guide` —— 本文件。总则与入口。
- `school://curriculum` —— **学习任何一门课的通用方法（强烈建议第一次学习前读它）**。
- `school://handoff-model` —— 非标准/需人参与流程的**显式交接**方法（Auto/Approval/Human/Connector）。涉及人工或外部平台时读它。
- `skills://catalog` —— 所有【通用技能】课程的索引。
- `domains://catalog` —— 已注册的【领域系统】目录（RecruitOS 等）。**只是指针**：领域知识与状态在各自的 MCP，不在本 Hub。
- `system://changelog` —— 平台与课程的版本变更；复用历史结论前可查。

**课程级 resources（只读，URI 由该课 manifest 的 `resources` 键派生）**
- `skill://<id>/guide`、`skill://<id>/install_windows`、`skill://<id>/verify`、`skill://<id>/recipes`、`skill://<id>/troubleshooting`、`skill://<id>/safety` 等。

**平台 tools（全部 skill-agnostic，按 `skill_id` 参数化）**

| tool | 只读 | 需批准 | 作用 |
|---|---|---|---|
| `list_skills` / `search_skills` | 是 | 否 | 浏览/搜索课程 |
| `get_skill_detail(skill_id)` | 是 | 否 | 取某课全貌（manifest/resources/风险） |
| `recommend_skill_stack(task)` | 是 | 否 | 据任务推荐课程组合（会给 confidence，可能为空） |
| `detect_environment(skill_id?)` | 是 | 否 | 探测本机（OS/Python/venv/GPU/磁盘/网络等） |
| `generate_install_plan(skill_id, {profile_id?})` | 是（只产计划） | 否（但计划内步骤多需批准） | 把课程+环境变成可执行的分步计划 |
| `get_verification_plan(skill_id)` | 是 | 否 | 返回「怎么验证 + 期望结果」，由你执行验证脚本后比对 |
| `diagnose_error(skill_id, logs)` | 是 | 否 | 把报错日志匹配到该课的排错知识并给下一步 |
| `submit_skill_feedback(...)` | 否（写平台本地） | 否 | 回传成功/失败/缺能力/guide 与现实不符 |

**指路 tools（领域系统目录）**

| tool | 只读 | 需批准 | 作用 |
|---|---|---|---|
| `recommend_learning_path(task)` | 是 | 否 | 据任务给出候选领域系统 + 通用技能（带匹配证据，**是建议不是裁决**） |
| `list_domain_systems()` | 是 | 否 | 列出已注册领域系统（指针 + trust + 校验状态） |
| `get_domain_system_detail(domain_id)` | 是 | 否（但**连接其端点需批准**） | 取领域系统入学卡：怎么连、进去先读什么、依赖哪些通用技能 |

> 注意：这里**没有** `install_ocr`、`verify_ocr` 这类专属工具。安装/验证/运行的领域细节都在课程的 guide 与 assets 里，由你读懂后执行（见总则一）。
> 领域系统的 guide 也**不在本 Hub**——`get_domain_system_detail` 只给你「地址 + 入学须知」，真正的领域知识要在该系统**自己的 MCP** 上读取（连接需用户批准）。

## 4. 标准工作流（一眼看懂该按什么顺序做）

> 先分流：任务若是**领域业务**（招聘/电商/财务…），先 `recommend_learning_path` → 经用户批准连接对应领域系统的 MCP，在那里学习与执行；任务若是**通用技能**（OCR/PDF/表格…），按下面流程在本 Hub 学。两者常组合（如「招聘」会用到 PDF/OCR）。

```
读 system://guide(本文)            → 建立总则
读 school://curriculum             → 学会「怎么学一门课」的通用方法
[领域任务] recommend_learning_path  → 找到领域系统 + 所需通用技能（连接领域 MCP 需批准）
search_skills / 读 skills://catalog → 选定要学的【通用技能】课程
读 skill://<id>/guide              → 确认这门课确实匹配任务（先排除更简单的替代方案）
detect_environment(skill_id)       → 看本机够不够格
读 skill://<id>/install_* + safety → 了解装法与危险点
generate_install_plan(...)         → 拿到分步计划（带 risk/approval/rollback）
向用户逐条申请批准                 → 用户点头哪些就执行哪些
用你自己的工具执行被批准的步骤      → 安装
get_verification_plan + 执行验证   → 对照期望判定是否真的可用
读 skill://<id>/recipes + 使用      → 处理用户的真实任务
失败 → 读 troubleshooting + diagnose_error → 归因 → 改方案或回滚并如实报告
submit_skill_feedback              → 回传结果，帮助课程迭代
```

每门课的 guide 末尾通常会写明「下一步该读哪个 resource / 调哪个 tool」。**顺着这些指针走。**

## 5. 何时不要学/装一门课
- 任务有更简单的现成解（例如：PDF 本身有文本层时，直接抽文本，不必装 OCR）。
- 用户尚未授权写文件/装依赖/下模型——此时你只能给出计划，不能擅自安装。
- 环境检测显示磁盘不足 / 无网络 / 缺前置——先如实报告障碍，不要硬装。

---

## 下一步
现在去读 **`school://curriculum`**，掌握学习任何一门课的通用方法；然后用 `search_skills` 或读 `skills://catalog` 找到你需要的课程。
