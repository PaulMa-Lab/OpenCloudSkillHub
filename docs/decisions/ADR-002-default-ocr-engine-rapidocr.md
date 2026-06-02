# ADR-002：MVP 默认 OCR 引擎选用 RapidOCR

- 状态：**Accepted**（用户 2026-06-02 确认）；**待里程碑 4 真机复核**
- 日期：2026-06-02
- 关联：架构文档 §8、§9；ADR-003（OCR 仅为 reference course，引擎选择是课程数据不是核心逻辑）

## Context

MVP 第一门课是 OCR，约束为 **Windows + CPU + 中文/英文 + 安装顺滑**。候选引擎与其在这些维度的表现：

| 引擎 | 中文 | 英文 | Windows 安装 | CPU | 依赖 | MVP 适配 |
|---|---|---|---|---|---|---|
| PaddleOCR | 很强 | 强 | 高（paddle 易与 numpy/opencv 版本冲突） | 可 | 重 | 中（准但脆） |
| EasyOCR | 强 | 强 | 中（拖 PyTorch，体积大） | 可（慢） | 重 | 中 |
| Tesseract | 中文一般（需语言包配置） | 强 | 中（需系统级二进制，非纯 pip） | 可（快） | 轻 | 中（英文好） |
| **RapidOCR** | 强（PP-OCR 同源模型） | 强 | **低（纯 pip，onnxruntime）** | **可，快，轻** | **轻** | **高** |

用户原列的三个候选里，没有一个在「Win + CPU + 中文 + 易装」四项同时达标。

## Decision

**MVP 默认引擎 = RapidOCR**（PaddleOCR 模型跑在 onnxruntime 上，纯 pip、CPU 友好、中文好、安装最顺）。

在课程包中以 `install_profiles` 表达（ADR-003 的泛型机制）：
- `rapidocr` —— 默认 profile；
- `tesseract` —— 英文优先/轻量备选；
- （可选）`paddle` —— 追求中文最高精度时的进阶 profile。

**引擎选择逻辑不进平台核心**，而是作为课程的 guide/recipes 数据 + install_profiles，由 Agent 读后推理（见 ADR-003）。

## Consequences
- 最大化「干净 Windows 一次装成」的概率，契合 MVP 要验证的「Agent 自主装/验/排错」。
- 规避 paddle/torch 在 Windows/CPU 上的依赖地狱（numpy/opencv 版本冲突、大体积下载）。
- 课程默认值变化（未来换引擎）不影响平台核心，只改课程包数据。

## Alternatives considered
- **默认 PaddleOCR**：中文精度最高，但 Windows/CPU 安装最易踩坑，与「一次装成」目标冲突。降级为进阶 profile。
- **默认 EasyOCR**：要拖数百 MB~GB 的 PyTorch，首次体验差。仅备选。
- **默认 Tesseract**：纯英文场景好，但需系统级二进制 + 中文配置繁琐。作英文备选 profile。

## Uncertainty（必须里程碑 4 真机验证后才能定稿）
- RapidOCR 中文权重的实际体积、首次下载耗时未实测，`est_download_mb` 暂估。
- 在较老 Win10 上的 `onnxruntime` 兼容性未验证。
- **回退顺位**：若真机不顺 → Tesseract（英文）/ PaddleOCR（中文高精度）。本 ADR 在里程碑 4 后据实测结果复核，可能修订默认 profile。
