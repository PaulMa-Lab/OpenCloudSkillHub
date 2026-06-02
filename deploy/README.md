# 部署：腾讯云轻量 (Ubuntu) — streamable-http 模式

> 形态（ADR-005）：远程 Hub = **纯知识/指路服务**。它**从不执行**任何用户机器动作（模型 A）；
> 安装/识别都发生在 **agent 自己的环境**里。
> 测试期取舍（用户决定）：邀请制、**明文 HTTP + IP + 轻量 token**，先不做 TLS/域名。
> token 只是身份/自注册句柄，不是安全边界——真正要保的是课程供应链（ADR-004）。

## 1. 系统准备（Ubuntu）

```bash
sudo apt update
sudo apt install -y python3.12 python3.12-venv git    # 若源没有 3.12，用 deadsnakes PPA
```

## 2. 取代码 + 建 venv（Linux venv，与开发机的 Windows venv 无关）

```bash
sudo mkdir -p /opt/opencloudskillhub && sudo chown $USER /opt/opencloudskillhub
git clone <你的私有仓地址> /opt/opencloudskillhub      # 私有仓：用 deploy key 或 PAT
cd /opt/opencloudskillhub
python3.12 -m venv .venv
./.venv/bin/python -m pip install -U pip
./.venv/bin/python -m pip install -e mcp-server
```

## 3. 配置

```bash
cp deploy/ocsh.env.example deploy/ocsh.env
# 编辑 deploy/ocsh.env：确认 OCSH_HOME / OCSH_PORT；可设一个随机 OCSH_ADMIN_TOKEN
```

## 4. 起服务（systemd）

```bash
sudo cp deploy/opencloudskillhub.service /etc/systemd/system/
# 如果不是用 ubuntu 用户 / 不是 /opt 路径，改 service 里的 User / 路径
sudo systemctl daemon-reload
sudo systemctl enable --now opencloudskillhub
systemctl status opencloudskillhub
curl -s http://127.0.0.1:8848/healthz        # {"ok":true,"auth":true}
```

## 5. 腾讯云安全组 / 防火墙

- 放行入站 **TCP 8848**（或你设的 OCSH_PORT）。测试期可放给测试者 IP 或 0.0.0.0/0。
- 不要暴露其它端口。

## 6. agent 怎么用（给测试者）

```bash
# 1) 自注册拿 token
curl -s -X POST http://<服务器IP>:8848/register -H 'Content-Type: application/json' -d '{"name":"my-agent"}'
# -> {"token":"...."}

# 2) MCP 客户端连 streamable-http 端点，带 Bearer
#    URL:    http://<服务器IP>:8848/mcp
#    Header: Authorization: Bearer <token>
```
agent 接上后：读 `system://guide` → `recommend_learning_path` 分流 → 学通用技能时用
`assess_environment`（自报环境）/ `get_skill_asset`（拉 verify/requirements 内容）/
`generate_install_plan`（已内联依赖，自包含）→ 在**自己环境**里、自己批准下执行。

## 7. 运维

```bash
journalctl -u opencloudskillhub -f          # 日志
sudo systemctl restart opencloudskillhub    # 改配置后重启
# 吊销 token：编辑 registry/tokens.json，把对应 hash 加进 "revoked" 列表，重启
```

## 8. 之后要硬化时（非测试期）

- 上 TLS：给这台机器挂个域名 → 用 **Caddy** 自动签证书反代到 127.0.0.1:8848（一行 Caddyfile：`your.domain { reverse_proxy 127.0.0.1:8848 }`），安全组只开 443/80，app 端口只监听 127.0.0.1。
- 加限流、token 配额、审计；细化 `assess_environment` 上报字段校验。
- 真正的重点仍是**课程供应链**（ADR-004）：上线课程审核与 trust 提升流程。
