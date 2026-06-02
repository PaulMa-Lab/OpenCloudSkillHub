# examples/ — 端到端走查

## e2e_ocr_learning.py
一个**脚本化的 MCP 客户端**，按 `school://curriculum` 的阶段顺序驱动 Hub 走完一整条学习闭环，并在最后**真实执行** OCR 验证。

```powershell
# 需要先按 mcp-server/README.md 建好 .venv
.\mcp-server\.venv\Scripts\python.exe examples\e2e_ocr_learning.py
```

它依次演示：
0. orient — 读 `system://guide`（instructions 在握手时下发）
1a. 领域任务分流 — `recommend_learning_path("帮用户招聘…")` → 指向 RecruitOS（含端点/trust/所需通用技能/审批提示）
1b. 通用技能分流 — `recommend_learning_path("…从截图提取文字")` → 命中 OCR 课程
2. 选课 — `get_skill_detail("ocr")` → 拿到 resource URIs
3. 读课 — 读 `skill://ocr/guide`（验证 skill 资源模板）
4. 评估 — `detect_environment("ocr")` → 平台/Python/磁盘 + fit
5. 计划 — `generate_install_plan("ocr")` → 分步计划（Hub 只生成，每步标 approval/risk/rollback）
6. 验证 — `get_verification_plan("ocr")` → **宿主真实执行** verify → PASS
7. 排错 — `diagnose_error("ocr", numpy冲突日志)` → 命中 `numpy_incompat`
8. 反馈 — `submit_skill_feedback("ocr","verified")`

## 它证明了什么 / 没证明什么
- ✅ **证明**：整条闭环在 MCP 层机械连通，且能以真实 OCR 执行收尾。
- ❌ **未证明**：一个真实 LLM agent 会**自己选择**按此顺序行动（会不会主动读 guide、按关卡推进、在危险步申请批准）。这是真正的开放问题，只能靠把真实 Claude Code 接上来测（见 `mcp-server/README.md` 的 `.mcp.json`）。这份脚本是那次测试的预演与对照基线。

最近一次运行的输出见 `transcript.md`。
