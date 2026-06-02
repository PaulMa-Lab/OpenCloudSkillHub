<!-- resource: skill://ocr/recipes -->
# OCR Skill — 用法（skill://ocr/recipes）

安装并验证通过后，用 runner 处理用户的真实任务。**读取用户的本地图片/PDF 前需用户批准。**

## 最小调用
```powershell
# <env> = OCR 的 venv；ocr_runner.py 由安装步从 assets/runner_template.py 生成
& "<env>\Scripts\python.exe" ocr_runner.py "C:\path\to\image.png"
# 结构化输出（含每行 score）：
& "<env>\Scripts\python.exe" ocr_runner.py "C:\path\to\image.png" --json
```

## 常见情形
- **多张图**：对每个文件调一次 runner，循环收集结果。
- **图片型 PDF**：先把 PDF 每页转成图片（如 `pdf2image`/`pymupdf`），再逐页 OCR。**先确认 PDF 没有文本层**——有的话直接抽文本，别走 OCR。
- **中文**：RapidOCR 默认模型支持中英文混排，通常无需额外配置。

## 输出
runner 返回识别文本（`--json` 时附带逐行 `text` 与 `score`）。把结果交付用户；不确定的低 `score` 行应提示用户复核，不要当成确定结果。
