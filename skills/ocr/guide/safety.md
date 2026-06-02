<!-- resource: skill://ocr/safety -->
# OCR Skill — 安全声明（skill://ocr/safety）

这门课会让 Agent 申请以下**宿主权力**（manifest `tools_required`），对应的动作都**需用户批准、由宿主执行**（平台不执行）：

| 能力 | 用途 | 风险 |
|---|---|---|
| `file_write` | 建 venv、生成 runner | 中 |
| `shell_optional` | 跑 pip / venv / 验证脚本 | 中 |
| `network_outbound` | 下载 pip 依赖 | 中 |
| `model_download` | 首次识别下载 OCR 模型（占磁盘 + 走网络） | 中 |
| `file_read` | 读取用户要识别的图片/PDF | 中（触及用户数据） |

## 必须先获批准的动作
- 建 venv / 写文件、执行 shell、装依赖、下载模型；
- **读取用户的本地图片/PDF**（最小授权：只读用户指定的这一张/这一批，不要申请整盘）。

## 本课不做的事
- **不**上传任何用户图片到远程 OCR 服务（本课是本地 OCR；若将来加远程兜底，那是独立的、默认关闭、需显式批准的能力）。
- **不**联网做与安装/模型下载无关的事。
- 验证/runner 脚本只做本地识别，不外发数据、不写系统路径。

## 回滚
安装失败或用户撤回 → 删除 OCR 的 venv 目录即可彻底回滚，不影响系统其他部分。
