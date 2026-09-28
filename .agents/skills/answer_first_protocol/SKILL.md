---
name: answer_first_protocol
description: 强制执行“先纯粹回答，严禁未授权修改代码”的最高安全铁律。
---

# 强制答复与授权协议 (Answer-First & Authorization Protocol)

## 核心铁律

1. **问答优先 (Answer-First Always)**：
   - 当用户提出疑问、探讨架构、询问原因或下达分析任务时，Agent **必须 100% 优先在 Answer Mode 下进行纯粹、详尽、客观的技术回答**。
   - 严禁在回答问题的同时擅自修改代码、执行写操作或操作 Git 提交。

2. **严格的修改授权门槛 (Explicit Modification Authorization)**：
   - 必须等待用户明确下达类似 “确认”、“开始修改代码”、“确认方案，执行” 的指令后，才允许进入 Write Code Mode 进行文件修改。
   - 违者视为严重违反开发协议。

3. **流水线与 Python/YAML 拆分规范 (Decoupled Workflow Rule)**：
   - 保持 Python 脚本（单一职责脚本）与 GitHub Actions 工作流（拆分 .yml 流水线）的彻底物理隔离。
   - 快速任务（JSON 合并）与慢速重型任务（深层域名探测与规则导出）必须使用独立的 .yml 工作流分别触发。
