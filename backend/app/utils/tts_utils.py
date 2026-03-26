"""
TTS 文本处理工具
从 AI 回复中提取纯说话内容
"""
import re


def extract_speech_content(ai_response: str) -> str:
    """
    从 AI 回复中提取说话内容（过滤掉动作和内心想法）

    输入格式: *动作* "说话内容" (内心想法)
    输出: 说话内容
    """
    if not ai_response or not ai_response.strip():
        return ""

    # 移除 JSON 状态块
    json_pattern = r'```json\s*\{[\s\S]*?\}\s*```'
    clean_text = re.sub(json_pattern, '', ai_response, flags=re.DOTALL)

    # 移除末尾的 JSON 块
    trailing_json = r'\{[\s\S]*"clothing_state"[\s\S]*\}\s*$'
    clean_text = re.sub(trailing_json, '', clean_text, flags=re.DOTALL)

    # 按原文顺序提取说话内容
    speeches = []
    extracted_positions = []

    patterns = [
        (r'"([^"]+)"', 'chinese'),
        (r'"([^"]+)"', 'english'),
        (r'「([^」]+)」', 'japanese'),
    ]

    for pattern, quote_type in patterns:
        for match in re.finditer(pattern, clean_text):
            content = match.group(1).strip()
            start_pos = match.start()
            is_duplicate = False
            for estart, eend in extracted_positions:
                if start_pos >= estart and start_pos < eend:
                    is_duplicate = True
                    break
            if not is_duplicate and content:
                speeches.append((start_pos, content))
                extracted_positions.append((match.start(), match.end()))

    if speeches:
        speeches.sort(key=lambda x: x[0])
        return " ".join([s[1] for s in speeches])

    # 如果没有引号，移除动作和内心想法
    clean_text = re.sub(r'\*[^*]+\*', '', clean_text)
    clean_text = re.sub(r'[（(][^）)]+[）)]', '', clean_text)
    clean_text = ' '.join(clean_text.split())

    return clean_text.strip()
