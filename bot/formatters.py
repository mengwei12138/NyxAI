"""
文本格式化模块
"""

import re


def format_states_display(states: dict) -> str:
    """格式化状态显示"""
    lines = ["📊 *当前状态*", ""]

    # 防御性处理：如果是列表格式，转换为字典
    if isinstance(states, list):
        states_dict = {}
        for state in states:
            if isinstance(state, dict):
                key = state.get('state_name', state.get('key', 'unknown'))
                states_dict[key] = {
                    'value': state.get('current_value') or state.get('default_value') or state.get('value', ''),
                    'desc': state.get('description') or state.get('desc', '')
                }
        states = states_dict

    for key, state in states.items():
        value = state['value']
        desc = state.get('desc', '')
        # 截断过长的描述
        if len(desc) > 30:
            desc = desc[:27] + "..."
        lines.append(f"▶ *{key}*: `{value}`")
        if desc:
            lines.append(f"  _{desc}_")
    return "\n".join(lines)


def format_ai_response(text: str) -> str:
    """
    格式化 AI 回复，区分动作、对话和内心想法
    将 *动作* → 🎭 动作
    将 "对话" → 💬 对话
    将 (内心想法) → 💭 内心想法
    """
    # 移除可能的 JSON 块（匹配 ```json ... ```）
    text = re.sub(r'```json\s*\{[\s\S]*?\}\s*```', '', text, flags=re.DOTALL)
    text = text.strip()

    if not text:
        return text

    result_lines = []

    # 提取动作 *...* （匹配 * 包围的内容，但排除 ** 加粗语法）
    action_match = re.search(r'\*([^*\n]+?)\*', text)
    if action_match:
        action = action_match.group(1).strip()
        if action:
            result_lines.append(f"🎭 *动作*: {action}")

    # 提取对话：匹配所有常见引号对
    # "..."（中文左右双引号）、"..."（直引号）、「...」（日文/中文书名号）
    dialogue_match = re.search(r'["\u201c]([^\u201d"\n]+?)[\u201d"]', text)
    if not dialogue_match:
        dialogue_match = re.search(r'「([^」\n]+?)」', text)
    if dialogue_match:
        dialogue = dialogue_match.group(1).strip()
        if dialogue:
            result_lines.append(f"💬 *说话*: 「{dialogue}」")

    # 提取内心想法：匹配英文圆括号 (...) 和中文全角括号 （...）
    thought_match = re.search(r'[(\uff08]([^)\uff09\n]+?)[)\uff09]', text)
    if thought_match:
        thought = thought_match.group(1).strip()
        if thought:
            result_lines.append(f"💭 *内心*: （{thought}）")

    # 如果没有匹配到任何格式，返回原文
    if not result_lines:
        return text

    return "\n\n".join(result_lines)


def format_character_info(profile: dict, full: bool = False) -> str:
    """
    格式化角色信息

    Args:
        profile: 角色配置字典
        full: 是否显示完整信息（不截断）
    """
    if full:
        # 完整显示模式（选择角色后展示）
        return f"""🎭 *{profile['name']}*

📖 *人设*:
{profile['persona']}

🎬 *场景*:
{profile['scenario']}

👤 *用户设定*:
{profile['user_persona']}"""
    else:
        # 截断显示模式（列表预览）
        return f"""🎭 *{profile['name']}*

📖 *人设*: {profile['persona'][:100]}...

🎬 *场景*: {profile['scenario'][:100]}...

👤 *用户设定*: {profile['user_persona'][:100]}..."""
