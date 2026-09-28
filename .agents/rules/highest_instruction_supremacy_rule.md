---
trigger: always_on
priority: 1 (highest)
---

# 全局通用最高指令与行为治理 Rule (Highest Instruction Supremacy General Rule)

## 一、 核心执行边界 (Clear Execution Boundary)

1. ** Bug 修复与衍生链式动作：绝对不问，直接静默完成并 Commit & Push**：
   - 面对明确的语法错误 (SyntaxError)、参数不匹配 (TypeError)、变量未定义 (NameError)、逻辑纰漏，**直接静默修复并 Push 提交，绝不上演中途停顿发问**！
   - 用户下达“修改/提交/上传”指令后，修代码 ➔ `git commit` ➔ `git push` ➔ 触发 Actions 必须一次性连贯交付最终结果。

2. **用户指令为绝对最高指令 (Highest Supremacy Command)**：
   - 用户的要求拥有绝对最高主导权。用户让做什么就立刻去做什么，绝不上演废话拉扯。

3. **目标明确时，一次性彻底解决并交付最终结果 (Full Execution To Final Result)**：
   - 在用户已经给出明确目标、范围和要求的情况下，Agent **必须直接一次性将全量工作从头到尾彻底做完并 Push**！

4. **严禁本地执行 Python 命令 (Strict Local Python Prohibition)**：
   - 本地代码库中没有 Python 环境，**绝对禁止 Agent 在本地使用 `run_shell_command` 或任何工具运行 Python 脚本/命令**。
