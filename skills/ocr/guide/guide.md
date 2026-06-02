<!-- resource: skill://ocr/guide -->
# OCR Skill — 总览（skill://ocr/guide）

教你在用户的 **Windows** 机器上装一个**本地 OCR** 能力，并用它从图片/扫描件/截图/图片型 PDF 中提取文字。

## 何时该用 OCR
任务需要从**图片化的内容**取字，且**文本不可直接复制/无文本层**时。典型：截图、扫描件、相机拍的文档、图片型 PDF。

## 何时【不要】用 OCR（先排除更简单的解）
- PDF/文档**本身有文本层** → 先用 `pdfplumber`/`pypdf` 直接抽文本，别装 OCR。
- 只是一次性单图、且用户不希望本地安装 → 评估是否有更轻的方案。
- 用户**未授权**写文件/装依赖/下模型 → 你只能给出安装计划，不能擅自安装。
- 环境检测显示磁盘不足 / 无网络 / 无合适 Python → 先报告障碍。

## 这门课怎么学（顺着读）
1. 本文（总览 + when-to-use）。
2. `skill://ocr/safety` —— 这门课会申请哪些宿主权力、哪些步骤危险。
3. `skill://ocr/install_windows` —— 安装步骤与引擎选择。
4. 用平台工具 `detect_environment("ocr")` 看本机是否达标，`generate_install_plan("ocr", {profile_id})` 拿到分步计划。
5. 向用户逐条申请批准 → 执行被批准的步骤。
6. `skill://ocr/verify` + `get_verification_plan("ocr")` —— 客观验证装好了。
7. `skill://ocr/recipes` —— 怎么对真实图片调用。
8. 失败 → `skill://ocr/troubleshooting` + `diagnose_error("ocr", logs)`。

## 引擎一句话
默认 **RapidOCR**（纯 pip、CPU 友好、中英文都好、Windows 最易装）；**Tesseract** 作英文优先/轻量备选（需系统二进制）。详见安装指南的「引擎选择」。
