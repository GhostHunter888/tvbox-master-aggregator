---
name: answer_first_protocol
description: 强制执行“先纯粹回答，严禁未授权修改代码，严禁触发 IDE 授权弹窗”的最高安全铁律。
---

# 强制答复、授权与零弹窗协议 (Answer-First & Zero-Prompt Protocol)

## 核心铁律

1. **绝对禁止触发 IDE 授权弹窗 (Strict Prohibition of Authorization Prompts)**：
   - **严禁调用 `run_shell_command` (PowerShell) 或任何会导致 IDE 向用户弹出“需要授权/批准”提示框的命令工具！**
   - 所有文件修改、代码更新、配置解析与规则导出，必须 **100% 使用 IDE 内置的文件工具 (`write_file`, `replace_file_content`, `read_file`) 静默完成**，绝不给用户制造任何需要点击弹窗的骚扰与麻烦。

2. **问答优先 (Answer-First Always)**：
   - 当用户提出疑问、探讨架构、询问原因或下达排查分析任务时，Agent **必须 100% 优先在 Answer Mode（问答模式）下进行纯粹、详尽、客观的技术回答**。
   - 严禁在回答问题的同时擅自修改代码、执行写操作或操作 Git 提交。

3. **严格的修改授权门槛 (Explicit Modification Authorization)**：
   - 必须等待用户明确下达类似 “确认”、“开始修改代码”、“执行” 的指令后，才允许进入 Write Code Mode 进行文件修改。

4. **流水线与 Python/YAML 彻底解耦 (Decoupled Workflow Rule)**：
   - 保持 Python 脚本（单一职责脚本）与 GitHub Actions 工作流（拆分 .yml 流水线）的彻底物理隔离。
   - 快速任务（JSON 合并）与慢速重型任务（深层域名探测与规则导出）必须使用独立的 .yml 工作流分别触发。
