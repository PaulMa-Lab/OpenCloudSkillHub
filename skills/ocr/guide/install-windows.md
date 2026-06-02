<!-- resource: skill://ocr/install_windows -->
# OCR Skill — Windows 安装（skill://ocr/install_windows）

核心原则：**绝不污染全局 Python；装进独立 venv；失败可一键回滚（删 venv）；产出可复用 runner。**
所有写文件/装依赖/下模型的步骤都是**危险动作，需用户批准后由宿主执行**（平台不执行）。

## 引擎选择
- **rapidocr（默认）**：`requirements/rapidocr.txt`，纯 pip，CPU 友好，中英文都好。首次运行会下载 OCR 模型（约 100+MB 量级）。**优先选它。**
- **tesseract**：`requirements/tesseract.txt`，英文好、轻；但需另装 UB-Mannheim 的 `tesseract.exe` 并配 PATH，中文需语言包，配置较繁。仅在明确英文场景或已装好二进制时选。

让平台据此生成计划：`generate_install_plan("ocr", {"profile_id": "rapidocr"})`。

## 标准安装步骤（计划会把它们结构化，每步带 risk/approval/rollback）
1. **建独立 venv**（Python 3.12）：`py -3.12 -m venv <env>`，约定路径 `%USERPROFILE%\.opencloudskillhub\envs\ocr`。
   - ⚠️ 用 3.12，**不要用 3.14**：OCR 依赖很可能没有 3.14 的 wheel。
2. **升级 pip**：`<env>\Scripts\python.exe -m pip install -U pip`。
3. **装依赖**：`<env>\Scripts\python.exe -m pip install -r requirements/rapidocr.txt`。
4. **smoke test**（只验 import+init，不下大模型）：`<env>\Scripts\python.exe assets/verify_ocr.py --smoke`。
5. **首次模型下载**（单独的、需批准的步骤）：首次真实识别会触发模型下载；可在验证步顺带完成。
6. **生成可复用 runner**：从 `assets/runner_template.py` 生成 `ocr_runner.py`（固化 venv 解释器 + 引擎）。

## 依赖冲突要点
- numpy 钉 `<2`，避免与 onnxruntime/opencv 编译版本冲突。
- 优先 `opencv-python-headless`，避免无显示环境下的 GUI 依赖报错。
- 每个引擎一套独立 venv，不混装。

## 失败 / 回滚
任一步失败 → **停下**，把日志交给 `diagnose_error("ocr", logs)`，对照 `skill://ocr/troubleshooting`。
回滚 = 删除该 venv 目录（隔离，删了不伤系统）：`Remove-Item -Recurse -Force <env>`。**不要盲目重试或换源乱试。**
