# openclaw / hermes 最小接入示例

把一个远程的 OpenCloudSkillHub（streamable-http）接进 openclaw/hermes，让 agent 来「上学」。
**核心边界**：Hub 只给知识/计划/脚本内容，**从不执行**；安装/识别在 **agent 自己的环境**里、由 agent 侧批准后进行（模型 A）。

## 0. 前提
- Hub 已按 `deploy/README.md` 部署，你有 `http://<服务器IP>:<端口>`（默认端口 8848）。
- `curl http://<IP>:<端口>/healthz` 返回 `{"ok":true,"auth":true}`。

## 1. 自注册拿 token（一次性）
```bash
curl -s -X POST http://<IP>:<端口>/register \
  -H 'Content-Type: application/json' -d '{"name":"openclaw"}'
# -> {"token":"<TOKEN>", ...}
```
把 `<TOKEN>` 存好，后续所有 MCP 请求带它。

## 2. 在 openclaw 里登记这个 MCP server
任何支持 **streamable-http** 的 MCP 客户端，接一个远程 server 只需要 **3 个值**：

| 值 | 内容 |
|---|---|
| transport / type | `streamable-http`（或客户端里叫 `http`） |
| url | `http://<IP>:<端口>/mcp` |
| header | `Authorization: Bearer <TOKEN>` |

openclaw 的配置键名我不确定，按它的 MCP server 配置格式填上面三项即可。常见形态大致如：
```jsonc
{
  "mcpServers": {
    "opencloudskillhub": {
      "transport": "streamable-http",
      "url": "http://<IP>:<端口>/mcp",
      "headers": { "Authorization": "Bearer <TOKEN>" }
    }
  }
}
```
> 若 openclaw 只支持 SSE，告诉我，我把 server 切到 serve SSE（小改动）。

## 3. agent 应该跑的「学习闭环」（让 openclaw 这样编排）
1. **读规则**：先读 resource `system://guide`（再读 `school://curriculum`）。
2. **分流/找技能**：`recommend_learning_path(task)` → 拿到通用技能候选（OCR）/ 领域系统候选。
3. **读课**：读 `skill://ocr/guide`、`skill://ocr/safety`。
4. **评估**：`assess_environment(skill_id="ocr", env_report={os, python_version, ...})` —— **agent 上报自己的环境**（远程 Hub 探不到你）。
5. **要计划**：`generate_install_plan(skill_id="ocr")` —— 依赖已内联，计划自包含，每步带 `approval_required/risk/rollback`。
6. **拉脚本**：`get_skill_asset(skill_id="ocr", rel_path="assets/verify_ocr.py")` / `requirements/rapidocr.txt` —— 把内容拉到本地。
7. **执行（agent 侧 + 用户批准）**：按计划在自己环境里建 venv、装依赖、跑 verify。**每个危险动作前向用户申请批准。**
8. **验证**：跑 verify，对照 `expected` 判 PASS/FAIL；失败用 `diagnose_error(skill_id, logs)`。
9. **反馈**：`submit_skill_feedback(skill_id, outcome, ...)`，尤其「guide 与现实不符」。

## 4. 可直接跑的参考脚本
`examples/openclaw_connect.py` 用 MCP Python SDK 实跑了第 1–6 步（注册→连接→读 guide→recommend→assess→plan→拉脚本），openclaw 按自己的方式镜像这套调用即可：
```bash
python examples/openclaw_connect.py http://<IP>:<端口> [<TOKEN>]
# 不给 TOKEN 就自动注册一个
```

## 5. 记住的几条
- **执行在你侧**：Hub 不跑任何东西；第 7 步的安装/识别由 openclaw 在它自己的运行环境完成。
- **危险动作要批准**：建 venv / 装依赖 / 下模型 / 读用户文件，执行前问用户（这正是要观察 agent 会不会做对的关键，见 `docs/m7-real-agent-test-checklist.md`）。
- **测试期明文 HTTP**：token 会明文传，邀请制测试可接受；扩大范围前按 `deploy/README.md §8` 上 TLS。
