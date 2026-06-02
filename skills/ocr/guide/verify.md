<!-- resource: skill://ocr/verify -->
# OCR Skill — 验证（skill://ocr/verify）

「装好了」必须由**客观验证**判定，不靠感觉。

## 怎么验证
1. 调 `get_verification_plan("ocr")` 拿到「脚本路径 + 怎么跑 + 期望输出」。
2. **由宿主执行**该验证脚本（在 OCR 的 venv 里）：
   `<env>\Scripts\python.exe assets/verify_ocr.py`
3. 脚本会在内存里渲染一张含已知文本 `HELLO OCR 12345` 的测试图，跑 OCR，并检查识别结果。

## 通过标准
- 退出码 0，且输出 `PASS: all expected tokens found`；
- 识别文本（大写后）包含 `HELLO`、`OCR`、`12345`（即 manifest `verification.expected.contains`）。

## 分级
- `--smoke`：只验 import + 引擎初始化（快），用于安装后的早期失败检测。
- 完整验证（无 `--smoke`）：端到端证明引擎真的能识别。
- `--image <path>`：对用户真实图片识别并打印文本（读用户文件前需批准）。

验证不过 → 进入 `skill://ocr/troubleshooting` + `diagnose_error("ocr", logs)`。
