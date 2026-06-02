# Domain System Registration 契约（v0.1）

> 状态：契约草案。与课程包契约（skill-package-contract.md）平行的**第二类 contract**。
> 关联：architecture-v0.3-domains-and-handoff.md §4；ADR-003（Hub 只持有指针，不持有领域知识/状态）。

## 0. 定位

领域注册是一张**「入学卡 + 地址」**，不是领域知识的容器。Hub 通过它**指路**——告诉来访 Agent「这类任务属于哪个领域系统、怎么连、进去先读什么」。

**硬约束**：
- Hub **不**托管领域 guide 全文；领域 guide 永远从领域系统自己的 MCP 读取。
- Hub **不**代理转发领域 MCP 请求，**不**保存领域任务状态。
- 连接一个领域 MCP endpoint 属于**危险动作**（可能触及生产数据），由用户批准、宿主执行。
- `trust` 由平台在 `registry/trust.yaml` 赋予，**禁止自声明**。

## 1. 文件位置
`domains/<id>.yaml`，一个文件一个领域系统。平台扫描成 `domains://catalog`。

## 2. 字段 schema（v0.1）

| 字段 | 必需 | 类型 | 说明 |
|---|---|---|---|
| `schema_version` | R | `"1"` | 契约版本 |
| `id` | R | slug | 全局唯一 |
| `name` | R | string | 显示名 |
| `domain` | R | string | 领域类别，如 `recruiting` |
| `summary` | R | string | 一句话定位 |
| `mcp_endpoint` | R | https url | 领域系统 MCP 地址（**必须 https**，D-SAFE-1） |
| `transport` | O | enum `streamable-http｜sse｜http` | 传输方式，Agent 据此连接 |
| `entry_resource` | R | string | 进入后第一读（URI 属于**领域系统**，如 `system://guide`） |
| `also_read` | O | string[] | 进入后还应读的资源（URI 属于领域系统） |
| `teaches` | R | token[]（≥1） | 这个系统教 Agent 做什么，如 `resume_screening` |
| `requires_general_skills` | O | skill_id[] | 依赖的**通用技能**（指向 Hub 的 skills catalog） |
| `keywords` | R | string[]（≥1） | 供 `recommend_learning_path` 匹配 |
| `safety_level` | R | enum `public_data｜internal_data｜production_data` | 提示连上后可能触及的数据敏感级 |
| `status` | O | enum `draft｜active｜deprecated`，默认 active | 生命周期 |
| `maintainer` | O | string｜{name,...} | 维护者 |
| `trust` | — | — | **禁止出现**；由平台赋予（D-GOV-1） |

## 3. 校验规则（validate_domain，前缀 D-）

| code | severity | 规则 |
|---|---|---|
| D-STRUCT-1 | error | 文件解析为合法 YAML mapping |
| D-STRUCT-2 | error | 必填字段存在且类型正确 |
| D-STRUCT-3 | error | `id` 匹配 slug；`schema_version` 受支持 |
| D-STRUCT-4 | error | `safety_level`/`status`/`transport` 在枚举内 |
| D-SAFE-1 | error | `mcp_endpoint` 必须是 https（防止明文/降级；指路目标可信的最低门槛） |
| D-REF-1 | warn | `requires_general_skills` 每项应能在 skills catalog 解析到（找不到 → 警告，可能尚未编写） |
| D-GOV-1 | error | 不得自声明 `trust` |
| D-GOV-3 | warn | `status: draft` 可索引但标注、默认不进推荐 |

输出结构同课程校验器：`{skill_id(此处复用为 domain id), valid, errors, warnings, summary}`。

## 4. 信任等级
`registry/trust.yaml` 维护：
```yaml
domains:
  recruitos: official   # official | community | unverified（默认 unverified）
```

## 5. 不确定性
- `transport` 取值集合（streamable-http/sse/http）随 MCP 生态演进可能调整，用 `schema_version` 守兼容。
- D-SAFE-1 只能保证 https，**不能**保证 endpoint 背后的系统可信——可信靠 trust 等级 + 用户批准连接，二者缺一不可。
