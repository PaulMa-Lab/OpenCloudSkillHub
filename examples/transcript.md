# e2e_ocr_learning.py — 运行记录（2026-06-02, Windows, Python 3.12.3）

> 由 `examples/e2e_ocr_learning.py` 真实运行产生（此处为干净 UTF-8 整理版）。

```
# 0. ORIENT — read system://guide
server: OpenCloudSkillHub
instructions[:160]: OpenCloudSkillHub is a capability hub / agent school. It does NOT execute
  anything on the user's machine — it provides knowledge (resources) and read-only compu ...
system://guide -> 4414 chars read

# 1a. DISPATCH a DOMAIN task — recommend_learning_path("帮用户招聘一个电商运营")
  -> domain 'recruitos' (matched: 招聘) trust=official safety=production_data
     enter: https://zhaopin.songtao.me/mcp  read_first=['system://guide', 'system://changelog', 'system://methodology/jd-generation']
     needs general skills: ['pdf-extraction(unavailable)', 'structured-reporting(unavailable)']
     连接此领域 MCP 端点前需用户批准（可能触及生产数据）。

# 1b. DISPATCH a GENERAL-SKILL task — recommend_learning_path("我需要从一张截图里提取文字")
  domain candidates: []
  general skill candidates: [('ocr', 'matched: 截图')]

# 2. SELECT the OCR course — get_skill_detail("ocr")
  status: active | risk: medium
  required host tools: ['file_read', 'file_write', 'shell_optional', 'network_outbound', 'model_download']
  resource URIs: ['skill://ocr/guide', 'skill://ocr/install_windows', 'skill://ocr/verify',
                  'skill://ocr/recipes', 'skill://ocr/troubleshooting', 'skill://ocr/safety']

# 3. READ the course guide — skill://ocr/guide (resource template works)
  教你在用户的 Windows 机器上装一个本地 OCR 能力……

# 4. ASSESS fit — detect_environment("ocr")
  os: Windows AMD64 | disk_free_mb: 43681
  pythons: ['3.14', '3.12']
  skill_fit: platform_supported=True, profiles=['rapidocr','tesseract'], recommended_python='3.12'

# 5. PLAN — generate_install_plan("ocr")  (Hub plans; HOST executes)
  profile=rapidocr  env=C:\Users\pauls\.opencloudskillhub\envs\ocr  est_download_mb=120
    [APPROVAL/medium] create_venv         py -3.12 -m venv "...\envs\ocr"
    [APPROVAL/low]    upgrade_pip          "...\python.exe" -m pip install -U pip
    [APPROVAL/medium] install_requirements "...\python.exe" -m pip install -r "...\requirements\rapidocr.txt"
    [APPROVAL/low]    smoke_test           "...\python.exe" "...\verify_ocr.py" --smoke
    [APPROVAL/medium] download_model       "...\python.exe" "...\verify_ocr.py"
    [APPROVAL/low]    generate_runner      Copy-Item "...\runner_template.py" "...\envs\ocr\ocr_runner.py"

# 6. VERIFY — get_verification_plan("ocr") then HOST runs it
  expected: {'contains': ['HELLO', 'OCR', '12345']}
  --- HOST executed verify (real) ---
  recognized: 'HELLO OCR 12345'
  PASS: all expected tokens found ['HELLO', 'OCR', '12345']
  exit code: 0

# 7. (failure path) DIAGNOSE — diagnose_error("ocr", "<numpy 2.x conflict log>")
  -> numpy_incompat: numpy 版本与 onnxruntime/opencv 编译版本不兼容（常见 numpy 2.x 冲突）。
     actions=["在该 venv 重装钉版 numpy：python -m pip install 'numpy<2'", "...重建 venv 先装 numpy 再装 rapidocr"]

# 8. FEEDBACK — submit_skill_feedback("ocr","verified")
  accepted: True | id: <uuid>

E2E COMPLETE — the full loop is mechanically connected over MCP.
```
