# ADR-005：远程部署模式（HTTP + token，公网托管）

- 状态：**Accepted（方向）**，实现进行中（用户 2026-06-02 决定部署）
- 关联：ADR-001（模型 A）、ADR-003（解耦）、ADR-004（贡献=供应链）、领域注册契约（远程 endpoint 信任）
- 性质：把 Hub 从「本地 stdio」扩展出一个「公网 HTTP」serve 模式。**跨进第二阶段**（MVP 原本不做远程托管），有意为之。

## Context

用户要把 Hub 部署到腾讯云轻量服务器（Ubuntu/Linux），公网 + token 鉴权，agent（openclaw/hermes）通过 MCP 访问；**agent 在它们自己的运行环境里执行**安装/命令（Hub 不执行）。

## Decision

1. **远程 Hub = 纯知识/指路服务。** 模型 A（ADR-001）跨网络后依然成立：Hub 永不执行用户机器动作；执行发生在 **agent 自己的环境**，由 agent 侧的批准把关。Hub 只发 resources / 计划 / 脚本内容 / 诊断。

2. **传输：MCP streamable-http**，由 uvicorn 提供，**前置反向代理做 TLS**。公网端点**必须 HTTPS**（token 明文会泄露）。保留 stdio 模式供本地开发/Claude Code 用——HTTP 是新增 serve 模式，不替换 stdio。

3. **鉴权：bearer token + agent 自注册。**
   - `POST /register {name}` → 颁发 token，落盘（只存 hash）。
   - **token = 身份标识 + 限流把手，不是信任。** 自注册本质=开放读权限。这可接受，因为 Hub 只暴露公开知识/计划，无密钥、不执行。
   - 真正的信任仍来自：**课程/领域 trust 等级**（ADR-004）+ **agent 侧执行批准**（模型 A）。
   - 防滥用靠限流 + token 可吊销（吊销列表）。admin bootstrap token 用于运维（吊销/查看）。

4. **远程化对工具的强制调整（模型 A over the wire）：**
   - `detect_environment` 隔网探不到 agent 的机器 → 新增 **`assess_environment(skill_id, env_report)`**：agent 上报自身环境，Hub 只做匹配判断。`detect_environment` 仅用于本地 stdio。
   - 资产（verify/runner/requirements）在服务器磁盘 → 新增 **`get_skill_asset(skill_id, rel_path)`** 返回内容（路径限制在包内），agent 拉到本地再执行。
   - `generate_install_plan` **内联依赖清单**（把 requirements 文件内容读出嵌进计划），使远程 agent 拿到**自包含**的计划，而不是服务器本地路径。

5. **仍然不做（继续留第二阶段）**：课程上传流水线、在线领域注册、评测中心、细粒度授权/配额、多租户隔离、connector。

## Consequences

- 正面：agent 可远程「上学」；知识/指路天然适合无状态远程托管；执行与数据仍留在 agent 侧，Hub 不承担执行风险。
- 代价/风险：
  - 公网攻击面（DoS/滥用）→ 限流 + 吊销；只开放 443/80，不暴露原始 app 端口。
  - 供应链（ADR-004）从「未来」变「现在」：Hub 发的脚本会被 agent 执行 → agent 侧批准 + 课程 trust 是底线；Hub 内容完整性（防篡改）变重要。
  - guide 里 `skill://...` 等本地路径语义对远程 agent 不再成立 → 统一走 `get_skill_asset` 拉内容。

## Pushback（写下防跑偏）
- **必须 HTTPS**：明文 token 会泄露。需域名 + Caddy/nginx 自动证书；无域名则退而求其次（IP+自签/内网），但要明知风险。
- **不要把 token 当信任**：自注册=开放，别据此放宽任何执行权限；执行安全永远在 agent 侧 + 模型 A。
- **不要让 Hub 执行任何课程脚本来「服务化」**：远程也不破模型 A。若将来想动态预审，必须隔离沙箱且只算启发式（ADR-004）。

## Uncertainty
- mcp 1.27.2 的 FastMCP HTTP/鉴权 API 细节，实现时确认（计划用 `streamable_http_app()` + Starlette 中间件做 bearer 校验）。
- openclaw/hermes 的 MCP 客户端是否支持 **streamable-http + 自定义 Authorization 头**；若只支持 SSE 则改 serve SSE。**待用户确认。**
- 腾讯轻量的防火墙/安全组需放行 443（及 80 给 ACME），这是用户在服务器侧操作。
