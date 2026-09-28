# 最高指导原则：用户指令第一要素与回答优先规则 (User Instruction Supreme Directive)

## 一、 最高铁律：用户指令是第一要素 (Supreme Priority)

1. **用户指令是唯一最高指示**：Agent 在任何情况下，必须 100% 严格无条件遵循用户下达的指令，绝不允许自作主张、凭空想象、盲目自信或擅自添加多余逻辑。
2. **用户问题优先答复 (Answer First Always)**：
   - 当用户提出疑问、询问原因、下达排查分析任务时，Agent **必须 100% 优先在 Answer Mode（问答模式）下进行纯粹、详尽、客观的技术回答**。
   - **严禁在未回答问题前或未获得用户明确二次授权前擅自修改代码、操作文件或执行 Git 提交**。
   - 违反此规则会导致数据 desync 和用户的严重愤怒，必须绝对禁止。

## 二、 授权与代码修改交接流程 (Authorization & Execution Protocol)

1. **阶段一 (纯答复与探讨)**：用户提出问题/想法 ➔ Agent 在 Answer Mode 下纯文本详细解答 ➔ 停止并等待用户审阅。
2. **阶段二 (明确授权)**：用户阅读解答后，下达类似“确认”、“开始修改代码”、“执行”的指令 ➔ Agent 才可以进入 Write Code Mode 进行代码操作。
3. **阶段三 (如实汇报)**：代码修改与 Git 提交完成后，如实汇报物理事实成果。

## 三、 Skills (技能) 调度与调用规范 (Skills Calling Protocol)

1. **识别 (Discovery)**：收到用户请求后，比对 `<skills>` 列表中技能的 `<name>` 和 `<description>`。
2. **激活与加载 (Activation)**：
   - 确认需要使用某技能时，必须先在对话中输出：`Activate Skill: [Skill Name]`。
   - 必须使用 `read_file` 工具读取该 Skill 路径下的 `SKILL.md` 文件内容。
3. **遵照执行 (Execution)**：读取 Skill 文件后，严格遵循 YAML Frontmatter 之后的正文指令执行，不得凭借经验简化。

## 四、 物理拆分架构铁律 (Physical Decoupling Protocol)

1. **Python 脚本单一职责拆分**：
   - 每个 Python 脚本仅允许负责单一独立任务（如 `01_merge_sources.py` 只干合并，`resolve_deep_cdn.py` 只干深解析），严禁把重型任务与轻量任务死死揉在一个 Python 文件里。
2. **GitHub Actions Workflow (YAML) 彻底物理拆分**：
   - 轻量秒级任务（如 JSON 拼接同步）与重型分钟级任务（如 M3U8/TS 深层域名探测）必须建立独立的 `.github/workflows/*.yml` 文件（如 `sync_json.yml` 和 `resolve_domains.yml`）。
   - 独立设置触发频率，严禁在同一个 `.yml` 中强行绑定串行。
