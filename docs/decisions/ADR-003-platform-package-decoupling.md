# ADR-003：平台核心与课程包解耦（架构第一不变量）

- 状态：**Accepted**（用户 2026-06-02 强调，优先级最高）
- 日期：2026-06-02
- 关联：架构文档 §0.5；课程包契约 `docs/skill-package-contract.md`；ADR-001（相互强化）
- 优先级：**高于其余所有架构决定。任何冲突以本 ADR 为准。**

## Context

OpenCloudSkillHub 的长期形态是「承载很多课程的平台 / 协议 / 注册与分发层」，不是「带 OCR 的平台」。若第一天就把 OCR 逻辑写进平台核心，项目会长歪：之后每加一门课都要改核心，贡献者无法独立贡献课程，平台沦为「OCR 工具 + 一堆 if」。

OCR 只是第一门 reference course，用来验证平台机制，不应与平台内核绑死。

## Decision

确立**第一不变量**：**平台核心必须 skill-agnostic；任何具体 skill 的领域逻辑都不得写进平台核心。**

两层结构：
- **平台核心（opencloudskill-hub）**：registry/catalog、搜索、推荐、guide 暴露、安装计划生成、安全风险标注、版本管理、feedback 收集、贡献者治理、课程质量校验。完全泛化。
- **课程包（skill package）**：自带 `skill.yaml` + `guide/*` + `assets`。平台只读取、校验、暴露这些包，不理解其领域语义。

**验收式不变量（必须可通过）**：新增一门课 = 丢一个合规 skill package（或注册外部 skill repo），**对 `mcp-server/` 零代码改动**。若加课需改核心，则边界已破坏。

**对工具层的强制后果**：平台工具一律泛化、按 `skill_id` 参数化。OCR 专属工具（recommend_ocr_setup / verify_ocr_install / diagnose_ocr_error / run_sample_ocr / ocr_image_remote）**不进核心**，改写为：
| 原 OCR 专属逻辑 | 解耦后归属 |
|---|---|
| 选引擎 | guide/recipes 数据 + `install_profiles`，Agent 推理；跨课组合用泛化 `recommend_skill_stack` |
| 安装 | 泛化 `generate_install_plan(skill_id, {profile_id})` |
| 验证 | 泛化 `get_verification_plan(skill_id)`，宿主执行 skill 的 verify 脚本 |
| 诊断 | 泛化 `diagnose_error(skill_id, logs)`，检索包内 troubleshooting |
| 运行/远程推理 | 宿主按 recipes + runner 资产执行；远程推理为课程可选资产，默认关闭 |

泛化核心工具集：`list_skills / search_skills / get_skill_detail / recommend_skill_stack / generate_install_plan / detect_environment(skill_id?) / get_verification_plan / diagnose_error / submit_skill_feedback / validate_skill_package`。

**贡献与治理**：贡献课程 = 提交 skill package，不改核心。平台对包做：校验 manifest、校验 guide 引用的资产存在、标注/复核 risk_level、暴露成 resources、收集反馈、维护可信等级（official/community/unverified，不可自封）。详见课程包契约。

**仓库演进**：目标三仓 `opencloudskill-hub` / `opencloudskill-ocr` / `opencloudskill-catalog`。**MVP 单仓**，目录按「未来可拆」组织（`registry/` 与 `mcp-server/` 平行，`skills/ocr` 是平台托管的课程内容而非平台代码）。**先别真拆**，避免凭空的跨仓工程负担；但边界从第一行代码起清晰。

## Consequences

**正面**
- 平台可无限加课，贡献者无需碰核心代码。
- 与 ADR-001 相互强化：核心不跑任何 skill 代码 → 既 skill-agnostic 又更安全。
- 强制「guide 即课程的智力载体」，与「guide 比 tool list 重要」一致。

**负面 / 代价（不回避）**
- 平台**不能**用代码做聪明的 skill 专属推荐/校验，这些智力被推给「Agent 读 guide + 宿主执行 assets」。**课程包的 guide/assets 质量成为唯一壁垒，平台帮不上忙。**
- 泛化抽象（如 `install_profiles`）需要在「平台能消费的通用结构」与「课程的领域表达」之间找平衡，可能出现某些课程难以塞进泛型的情况；届时优先扩展泛型契约（升 `schema_version`），而非在核心开 skill 专属后门。

## Alternatives considered
- **核心内置若干「一等公民」skill（含 OCR）**：短期省事，长期必然长成「平台 + 一堆 if(skill==ocr)」，违背项目定位。**否决。**
- **第一天就拆三仓**：边界确实更硬，但 MVP 阶段凭空增加版本协调、跨仓 CI、引用解析负担。**推迟，仅在目录层预留边界。**

## Uncertainty
- 泛型 `install_profiles` 能否覆盖未来差异很大的课程（如浏览器自动化、本地数据库）尚未验证。需在加第二门课时复核契约是否够泛。
- guide↔脚本一致性只能静态校验「路径存在」子集，不能保证行为一致（见课程包契约 §7）。

## 实现注记（2026-06-02，非决策变更）
- 本 ADR 列举的泛化工具 `recommend_skill_stack` 在实现中**并入了更通用的 `recommend_learning_path`**（后者同时返回候选领域系统与通用技能；`general_skill_candidates` 即原 skill-stack 职责）。运行时不单列 `recommend_skill_stack`。决策本身（核心全泛化、按 skill_id 参数化）不变。
