<!--
  resource: school://handoff-model
  audience: AI Agent。用「你」称呼正在阅读的 Agent。
  role: 教 Agent 在非标准 / 需要人参与的流程里如何【显式交接】。这是一份【教学规范】，
        不是运行态。本 Hub 不保存任何任务状态；任务实例由【领域系统】持有（见原则 7）。
-->

# 显式交接模型（school://handoff-model）

真实业务里很多步骤**不是全自动**：有的需要人审批，有的必须人来做（面试、谈薪、最终录用），有的目标平台没有 API（BOSS 直聘、猎聘…）。

**关键原则：不要在聊天上下文里硬接这些步骤。** 聊天上下文会丢、会断、会换 Agent。要把每一次交接变成**有状态、有凭证、有超时、有后续动作**的任务对象——而这些对象**存在领域系统里**，不在本 Hub，也不在对话里。

> 本 Hub 只**教**你这套词汇；具体的任务存储与流转由各领域系统实现。Hub 不持有任何 HumanTask/审批实例。

## 四类任务

把任何一步明确归到下面四类之一（它们其实是「风险/审批模型」在领域侧的落地）：

| 类型 | 含义 | 你要做的 | 对应的风险/审批语义 |
|---|---|---|---|
| **AutoTask** | Agent 可自动执行 | 直接做（只读/无副作用或低风险） | 只读自主 |
| **ApprovalTask** | Agent 能做，但必须先获人批准 | 说清楚要做什么+风险 → 等批准 → 执行 | `approval_required` |
| **HumanTask** | 必须由人完成（面试/谈薪/最终决定/无 API 的平台操作） | **不要假装自己能做**；准备好材料、创建待办、追踪状态、回填结果 | 人工，Agent 只备料 |
| **ConnectorTask** | 通过外部平台 connector 执行 | 经审批后走 connector；无 connector 时降级为 HumanTask | 外部访问，最高风险 |

## HumanTask 怎么交接（核心）

当一步必须人来做时，**不要只说「你去发布吧」**。要在**领域系统里**创建一个结构化 HumanTask，给人和 Agent 一个有状态的交接点。示例（无 BOSS 直聘 API 时发布岗位）：

```yaml
task_type: publish_job_ad
assignee_type: human
platform: boss_zhipin
title: 发布电商运营岗位
agent_brief: 这是为 BOSS 直聘优化过的外发广告（标题/正文/标签见 payload）
payload:
  job_id: ...
  ad_content: ...
  recommended_tags: [...]
success_criteria: 发布成功后回填岗位链接或截图
status: pending          # pending → in_progress → done / expired
deadline: ...
on_complete: 继续推进 pipeline
```

这样：人知道要做什么、Agent 知道在等什么、断线换 Agent 也能凭 `status` 续上。

## 无 API 平台：Playbook + HumanTask
当目标平台没有 connector 时：
1. 读该领域系统提供的平台 **playbook**（如「BOSS 直聘怎么发岗、什么词易违规、发布后回填什么」）——**playbook 属于领域系统，不在本 Hub**。
2. 用 playbook 把产物准备好（优化过的广告文案等）。
3. 创建 **HumanTask** 交给人执行，并定义回填的 `success_criteria`。
4. 人完成并回填后，Agent 继续。

有 connector 时：`Agent → 审批 → connector 执行 → 自动回收 → 继续`。

## 你必须记住的边界
- **状态沉淀在领域系统**：job/简历/评估/stage 流转/待办/审计都留在该系统的 DB，不要塞进对话。
- **本 Hub 不存任务状态**：这份文档只给你词汇和方法；不要向 Hub 申请创建/查询 HumanTask。
- **汇报前查实际状态**：向用户汇报进展前，读领域系统里的真实状态（DB），不要凭对话记忆编造。
- **不确定就说不确定**，不要谎报「已发布/已完成」。

## 下一步
回到你的领域任务：用 `recommend_learning_path` 找到领域系统 → 经用户批准连接 → 在那里用本模型的词汇创建并追踪交接任务。
