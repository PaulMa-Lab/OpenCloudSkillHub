<!-- resource: skill://ocr/troubleshooting -->
# OCR Skill — 排错（skill://ocr/troubleshooting）

人类可读的「症状 → 原因 → 对策」表。结构化版本在 `assets/diagnostics.yaml`，由 `diagnose_error("ocr", logs)` 做匹配。**两者应保持一致。**

| 症状（日志关键词） | 原因 | 对策 |
|---|---|---|
| `compiled using NumPy 1.x` / `_ARRAY_API` / binary incompatibility | numpy 版本与 onnxruntime/opencv 不兼容（常见 numpy 2.x） | 该 venv 重装 `numpy<2`；仍冲突则重建 venv，先装 numpy 再装 rapidocr |
| `No module named 'rapidocr_onnxruntime'` | 依赖未装到当前 venv，或用错了解释器 | 确认用的是 OCR 的 venv；`pip install -r requirements/rapidocr.txt` |
| `No module named 'onnxruntime'` | onnxruntime 缺失 | `pip install onnxruntime` |
| `DLL load failed` / `cv2` 导入失败 | 缺 VC++ 运行库，或装了带 GUI 的 opencv | 装 VC++ Redistributable；换 `opencv-python-headless` |
| `URLError`/`timed out`/`Max retries`/`SSL` | 模型/依赖下载失败（网络/代理/被墙） | 重试；配 pip 镜像；或预下载模型离线运行 |
| `Could not find a version` / `No matching distribution` | 找不到匹配 wheel（常因 Python 太新，如 3.14） | 改用 Python 3.12 重建 venv |

排错流程：把真实日志交给 `diagnose_error("ocr", logs)` 得到归因与下一步 → 采取**单一明确**的动作 → 回到验证。走不通则**回滚（删 venv）并如实报告**，不要假装成功。
