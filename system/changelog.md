<!--
  resource: system://changelog
  audience: AI Agent。
  role: 平台与课程的版本变更记录。你在复用历史结论（缓存的安装/验证知识）前可查此处，判断是否已过时。
  format: 倒序，最新在上。每条标注影响面（platform / skill:<id> / contract）。
-->

# OpenCloudSkillHub · Changelog（system://changelog）

> 约定：倒序排列；每条注明影响面与是否破坏兼容（breaking）。

## [unreleased]
- **contract**: skill package 契约 `schema_version: "1"`（+ `diagnostics`/`success_criteria` 可选字段）；domain registration 契约 `schema_version: "1"`（`docs/domain-registration-contract.md`、`registry/domain.schema.json`）。
- **platform**: ADR-001（执行模型 A）/ ADR-002（默认引擎 RapidOCR，真机验证通过）/ ADR-003（平台-课程解耦）/ ADR-004（课程贡献=供应链）。
- **platform**: 泛化工具上线——catalog/search/detail、`validate_skill_package`、`detect_environment`、`generate_install_plan`、`get_verification_plan`、`diagnose_error`、`recommend_learning_path`、`list/get_domain_system`、`submit_skill_feedback`。
- **system**: `system://guide`、`school://curriculum`、`school://handoff-model`、`system://changelog`、`skills://catalog`、`domains://catalog`。
- **skill:ocr**: 可用（reference course，trust=official）。Windows 真机 RapidOCR 安装+验证通过。
- **domain:recruitos**: 已注册（指针，trust=official）；领域 guide 在 RecruitOS 自己的 MCP。

<!-- 正式发布后改为 ## [0.1.0] - YYYY-MM-DD，并由 system://guide 引导 Agent 在复用缓存知识前查阅。 -->
