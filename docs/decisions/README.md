# Architecture Decision Records (ADR)

记录 OpenCloudSkillHub 的关键架构决定。每条 ADR 是不可变的历史记录；决定若被推翻，新增一条 ADR 标注 supersedes，而非改旧的。

| ADR | 标题 | 状态 | 优先级 |
|---|---|---|---|
| [001](ADR-001-execution-model-a.md) | 执行采用模型 A（Hub 只读/出计划，宿主执行+审批） | Accepted | — |
| [002](ADR-002-default-ocr-engine-rapidocr.md) | MVP 默认 OCR 引擎 RapidOCR | Accepted（待里程碑 4 真机复核） | — |
| [003](ADR-003-platform-package-decoupling.md) | 平台核心与课程包解耦（第一不变量） | Accepted | **最高，冲突以此为准** |
| [004](ADR-004-course-contribution-is-supply-chain.md) | 课程贡献是供应链问题（自动校验把关+信任分级+不自动发布） | Accepted（原则；流水线属第二阶段） | 高（安全相关） |

相关规范：
- 架构设计文档：[`../architecture.md`](../architecture.md)
- 课程包契约：[`../skill-package-contract.md`](../skill-package-contract.md)
