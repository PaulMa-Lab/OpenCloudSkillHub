# Skill Package 契约（v0.1）

> 状态：契约草案，供平台核心与课程作者共同遵守。
> 关联：架构文档 §0.5（平台核心与课程包解耦，第一不变量）。
> 本文件定义「一个课程包长什么样」以及「平台如何校验它」。**平台核心据此校验包，但绝不内置任何具体 skill 的领域逻辑。**

---

## 0. 这份契约要解决的问题

解耦架构的全部重量压在一处：**平台核心是 skill-agnostic 的，它对一门课的全部了解，仅来自这门课的 package（manifest + guide + assets）。**

因此：
- manifest 是**包与平台之间唯一的结构化接口**。平台只认 manifest 声明的字段，不猜测、不读心。
- 校验器（`validate_skill_package`）是**质量与安全的第一道闸**，也是「guide↔脚本同步」这条头号技术债的主战场。
- 契约本身要可演进（`schema_version`），否则第一天定的字段会绑死未来所有课程。

---

## 1. 包目录契约（canonical layout）

一个课程包 = 一个目录。**所有路径都相对于包根目录**，禁止绝对路径、禁止 `..` 逃逸（安全硬规则）。

```
<package-root>/                # 如 skills/ocr/  或 外部仓 opencloudskill-ocr/
├─ skill.yaml                  # 【必需】manifest，唯一结构化接口
├─ guide/                      # 【必需】Agent 可读的教学内容（Markdown）
│   ├─ guide.md                #   总览 + when-to-use + 导航（resources.guide 指向它）
│   ├─ install-windows.md      #   平台相关安装（被 install.windows.guide 引用）
│   ├─ verify.md
│   ├─ recipes.md
│   ├─ troubleshooting.md
│   └─ safety.md               # 【必需】危险动作与审批声明
├─ assets/                     # 【可选】被 manifest 引用的可执行/样本资产
│   ├─ verify_<skill>.py       #   verification.smoke_test 指向它（宿主执行）
│   ├─ runner_template.*       #   生成可复用 runner 的模板
│   └─ samples/                #   带已知期望输出的样本输入
└─ requirements/               # 【可选】install_profiles 引用的依赖清单
    └─ <profile>.txt
```

**硬规则**：manifest 里引用的每一个路径都必须真实存在于包内（校验规则 R-REF-1）。guide/assets 的具体内容质量不在本契约范围，但「被引用即须存在」是强制的。

---

## 2. Manifest（skill.yaml）字段 schema

`R` = required，`O` = optional。「平台是否解释语义」一栏很关键：标「否」的字段，平台只做存在性/格式校验和透传，**不理解其含义**（这是 skill-agnostic 的体现）。

| 字段 | 必需 | 类型 | 平台解释语义 | 说明 |
|---|---|---|---|---|
| `schema_version` | R | string enum `"1"` | 是 | 本 manifest 遵循的契约版本。平台据此决定怎么解析。未来契约升级靠它兼容。 |
| `id` | R | slug `^[a-z0-9][a-z0-9-]*$` | 是 | 全局唯一标识。catalog 主键。 |
| `name` | R | string | 否 | 人/Agent 可读名。 |
| `version` | R | semver | 是 | 包版本。用于版本治理（R-GOV-2）。 |
| `summary` | R | string ≤140 | 否 | 一行用途，用于 catalog/search。 |
| `description` | O | string | 否 | 较长描述。 |
| `maintainer` | R | string \| `{name,contact?,url?}` | 否 | 维护者。 |
| `source` | O | url | 是 | 包来源仓库（外部 skill repo 用；三仓演进的引用锚点）。 |
| `license` | O | string (SPDX) | 否 | 许可。 |
| `tags` | O | string[] | 否（仅检索） | 检索标签。 |
| `capabilities` | R | string[] | 否（仅检索/推荐） | 这门课赋予的能力 token，如 `image_to_text`。供 search/recommend 用，平台不理解其含义。 |
| `risk_level` | R | enum `low\|medium\|high` | 是 | 整体风险。会被平台**交叉校验**（R-SAFE-1），不是自说自话。 |
| `platforms` | R | enum[]，子集 of `windows\|macos\|linux` | 是 | 本包当前真正支持的平台。MVP 仅 `[windows]`。 |
| `tools_required` | R | enum[]（见 §2.1） | 是 | 这门课运行所需的**宿主能力/权限**。安全契约核心：声明 Agent 会替它申请哪些宿主权力。 |
| `resources` | R | map<string,path> | 部分 | 逻辑名→guide 路径。**必须含 `guide`**。平台原样暴露成 MCP resources，不读内容语义。 |
| `install` | O | map<platform, InstallRef> | 部分 | 见 §2.2。 |
| `install_profiles` | O | InstallProfile[] | 是（泛型） | 见 §2.3。**泛型变体机制**：平台消费其通用结构（id/requirements/体积/风险），但不理解「引擎」这种领域含义。 |
| `verification` | R*（可运行的 skill） | `{smoke_test:path, plan?:path, expected?:any}` | 部分 | 见 §2.4。脚本由**宿主执行**（模型 A）。 |
| `troubleshooting` | O | path | 否 | 排错手册路径，供泛化 `diagnose_error` 检索。 |
| `recipes` | O | path | 否 | 用法范式路径。 |
| `safety` | R | path | 否 | 安全声明路径（safety.md）。**必需**。 |
| `requires_skills` | O | `{id, version_range}[]` | 是 | 依赖的其他课程（未来 skill stacking）。 |
| `status` | O | enum `draft\|active\|deprecated`，默认 `draft` | 是 | 生命周期。 |

> **`trust` 不在 manifest 里**。一门课不能自封 `official`。信任等级由平台在 `registry/trust.yaml` 赋予（§4）。manifest 里出现 `trust` 字段 = 校验错误（R-GOV-1）。

### 2.1 `tools_required` 受控词表（v0.1，可扩展）
声明这门课需要宿主授予的能力。平台据此向 Agent/用户说明「装这门课会申请哪些权力」，并参与风险交叉校验。

| token | 含义 | 风险贡献 |
|---|---|---|
| `file_read` | 读用户文件 | 低 |
| `file_write` | 写文件（建 venv、生成 runner、写配置） | 中 |
| `shell_optional` | 可能需要执行 shell（有降级路径） | 中 |
| `shell_required` | 必须执行 shell 才能完成 | 高 |
| `network_outbound` | 对外网络访问 | 中 |
| `model_download` | 下载模型（隐含 `network_outbound` + 磁盘占用） | 中 |

未在词表内的 token = 校验错误（R-STRUCT-5）。词表扩展需走契约版本升级。

### 2.2 InstallRef（`install.<platform>`）
```yaml
install:
  windows:
    guide: guide/install-windows.md     # 必需，须存在
    default_profile: rapidocr            # 可选，指向某个 install_profiles.id
```

### 2.3 InstallProfile（泛型安装变体）
**关键解耦设计**：把「OCR 有 RapidOCR/Paddle/Tesseract 三种引擎」表达成平台能消费的**泛型 profile**，而平台不需要知道「引擎」是什么。
```yaml
install_profiles:
  - id: rapidocr                  # slug，唯一
    label: "RapidOCR (onnxruntime, CPU, 推荐)"
    platforms: [windows]
    requirements: [requirements/rapidocr.txt]   # 路径须存在
    creates_venv: true
    est_download_mb: 80           # 估算，用于审批时告知用户
    risk_level: medium
    notes: "纯 pip，CPU 友好，中文好"
```
`generate_install_plan(skill_id, {profile_id})` 据此产出分步计划；平台只看通用字段，领域取舍（选哪个 profile）由 Agent 读 guide 推理。

### 2.4 Verification
```yaml
verification:
  smoke_test: assets/verify_ocr.py    # 须存在；宿主执行；只读自检
  expected:                            # 可选，平台不解释语义，原样回给 Agent 比对
    contains: ["示例", "Hello"]
```
`get_verification_plan(skill_id)` 返回 `{smoke_test 路径, 怎么跑, expected}`，**宿主执行脚本**（模型 A，核心不跑 skill 代码），Agent 对照 `expected` 判定。

---

## 3. `validate_skill_package` 校验规则

只读工具/CLI。输入包路径，输出结构化报告，**不修改任何东西、不需要审批**。
规则分四类，每条带稳定 `code` 与 `severity`（`error` 阻断收录 / `warn` 允许但提示）。

### 3.1 结构性（schema）— 多为 error
| code | severity | 规则 |
|---|---|---|
| R-STRUCT-1 | error | `skill.yaml` 能解析为合法 YAML |
| R-STRUCT-2 | error | 所有 R 字段存在且类型正确 |
| R-STRUCT-3 | error | `id` 匹配 slug 模式；`version` 是合法 semver；`schema_version` 在平台支持集内 |
| R-STRUCT-4 | error | `risk_level`/`platforms`/`status` 取值在各自枚举内 |
| R-STRUCT-5 | error | `tools_required` 每个值都在受控词表内 |
| R-STRUCT-6 | error | `resources` 是 map 且至少包含 `guide` |

### 3.2 引用完整性（filesystem）— error（安全相关）
| code | severity | 规则 |
|---|---|---|
| R-REF-1 | error | `resources`/`install.*.guide`/`verification.smoke_test`/`troubleshooting`/`recipes`/`safety`/`install_profiles[].requirements` 引用的每个路径都真实存在 |
| R-REF-2 | error | 所有路径都在包根目录内：无绝对路径、无 `..` 逃逸（**目录穿越防护**） |
| R-REF-3 | error | `verification.smoke_test` 指向的是文件（非目录） |
| R-REF-4 | error | `install.default_profile` / `requires_skills[].id` 等内部引用能解析到存在的目标 |

### 3.3 一致性（含 guide↔脚本同步，头号技术债主战场）
| code | severity | 规则 |
|---|---|---|
| R-CONS-1 | warn | guide 的 Markdown 中以代码块/链接形式引用的包内相对路径（如 `assets/xxx.py`、`requirements/xxx.txt`）都应真实存在。**这是把「guide 说的」与「包里有的」对齐的核心检查**（best-effort，先做警告级，成熟后升 error）。 |
| R-CONS-2 | warn | `capabilities` 与 `tags` 非空（否则检索/推荐能力差） |
| R-CONS-3 | warn | `summary` 长度 ≤140 |
| R-CONS-4 | error | 若存在 `install_profiles` 或任一 `creates_venv:true`/有 `requirements`，则 `safety` 文件必须存在（装东西就必须有安全声明） |
| R-CONS-5 | warn | `install_profiles[].platforms` 必须是 manifest 顶层 `platforms` 的子集 |

> R-CONS-1 是本项目能不能让 Agent「信任 guide」的关键。MVP 先做「路径引用存在性」这一可机检子集；更深的「guide 描述的命令 == 脚本实际行为」无法纯静态保证，留作人工评审 + 反馈闭环（架构文档 §13）。**不假装它能被完全自动校验。**

### 3.4 安全与治理
| code | severity | 规则 |
|---|---|---|
| R-SAFE-1 | error | **风险交叉校验**：自声明 `risk_level` 不得低于 `tools_required` 隐含的下限。映射：含 `file_write`/`shell_optional`/`network_outbound`/`model_download` ⇒ 至少 `medium`；含 `shell_required` ⇒ 至少 `medium`，且若同时含 `network_outbound`/`model_download` ⇒ 建议 `high`（warn 升 error 视策略）。**防止课程低报风险。** |
| R-SAFE-2 | error | 任一 `install_profiles[].est_download_mb>0` 或含 `model_download`，则 `tools_required` 必须含 `network_outbound`（声明一致） |
| R-GOV-1 | error | manifest 中**不得**出现 `trust` 字段（信任由平台赋予，不可自封） |
| R-GOV-2 | error | 同一 `id` 的新 `version` 不得低于 catalog 中已记录的最高版本（防版本回退；registry 级检查） |
| R-GOV-3 | warn | `status: draft` 的包可被索引但在 catalog 标注，默认不进入「推荐」结果 |

### 3.5 输出结构（read-only，无副作用，无需审批）
```json
{
  "skill_id": "ocr",
  "valid": false,
  "errors":   [{"code":"R-REF-1","severity":"error","path":"assets/verify_ocr.py","message":"referenced file not found"}],
  "warnings": [{"code":"R-CONS-2","severity":"warn","field":"tags","message":"empty tags hurt discoverability"}],
  "summary": "1 error, 1 warning"
}
```
`valid = (errors.length === 0)`。`warn` 不影响 `valid`，但会进入 catalog 的质量标注。

---

## 4. 信任等级与索引（registry/）

信任**不在包里**，由平台维护在 `registry/trust.yaml`：
```yaml
trust:
  ocr:    { level: official,   source: skills/ocr }
  # 新提交默认 unverified，经人工/治理流程升级
levels: [official, community, unverified]   # 默认 unverified
```
`registry/catalog.json` 由扫描 + 校验生成，记录：`id, name, version, source, capabilities, risk_level, status, trust, validation: {valid, error_count, warn_count}`。**catalog 是派生视图，唯一事实源是各包的 manifest + trust.yaml。**

---

## 5. 契约版本治理

- `schema_version` 当前 `"1"`。
- 新增**可选**字段或新增 `tools_required` token：不升大版本，但更新本文件与 JSON Schema，并在 `system://changelog` 记录。
- 改动/删除字段、收紧校验到 error：升 `schema_version`，平台需同时支持旧版解析一段时间（向后兼容窗口）。
- 校验器对 `schema_version` 不支持的包：报 R-STRUCT-3 error，不强行解析。

---

## 6. 示例：OCR 课程包的 manifest（仅示例，非磁盘成品）

> OCR 是第一门 reference course。下面是其目标 manifest；引用的 guide/assets 由里程碑 3 落地，届时校验器应对它返回 `valid:true`。**现在若把它落盘，校验器会正确地报 R-REF-1（文件未建）——这正是校验器在起作用。**

```yaml
schema_version: "1"
id: ocr
name: OCR Skill
version: 0.1.0
summary: 从图片/扫描件/图片型 PDF 中提取文字（本地优先，Windows）
maintainer: { name: opencloudskill }
license: MIT
tags: [ocr, text-extraction, vision, chinese, english]
capabilities: [image_to_text, scanned_pdf_to_text]
risk_level: medium
platforms: [windows]
tools_required: [file_read, file_write, shell_optional, network_outbound, model_download]
resources:
  guide:            guide/guide.md
  install_windows:  guide/install-windows.md
  verify:           guide/verify.md
  recipes:          guide/recipes.md
  troubleshooting:  guide/troubleshooting.md
  safety:           guide/safety.md
safety:          guide/safety.md
troubleshooting: guide/troubleshooting.md
recipes:         guide/recipes.md
install:
  windows:
    guide: guide/install-windows.md
    default_profile: rapidocr
install_profiles:
  - id: rapidocr
    label: "RapidOCR (onnxruntime, CPU, 推荐)"
    platforms: [windows]
    requirements: [requirements/rapidocr.txt]
    creates_venv: true
    est_download_mb: 80
    risk_level: medium
    notes: "纯 pip，CPU 友好，中文好；MVP 默认"
  - id: tesseract
    label: "Tesseract (英文优先，需系统二进制)"
    platforms: [windows]
    requirements: [requirements/tesseract.txt]
    creates_venv: true
    est_download_mb: 30
    risk_level: medium
    notes: "需另装 UB-Mannheim 二进制；中文偏弱"
verification:
  smoke_test: assets/verify_ocr.py
  expected:
    contains: ["示例文本"]
status: draft
```

---

## 7. 明确的边界与不确定性
- 本契约只规定**结构与可机检的约束**。guide 的教学质量、脚本是否真的能装成，**不在静态校验能力范围内**——靠真机验证（里程碑 4）+ 反馈闭环。
- `tools_required` 词表、`risk_level` 推导映射是 v0.1 的合理起点，**会随真实课程增多而调整**，所以用 `schema_version` 守住兼容性。
- R-CONS-1（guide↔脚本一致性）目前只能覆盖「路径引用存在」，**不要把它当成「guide 与脚本行为一致」的保证**。这是已知技术债，不掩盖。
