"""
Prompt 加载工具
从 backend/app/prompts/ 文件夹加载 Markdown 提示词文件
- CHAT/ : AI角色聊天相关提示词
- TTI/  : 文生图相关提示词
"""
import os
import re


def get_prompts_dir() -> str:
    """获取 prompts 目录路径"""
    # 从 backend/app/utils/prompts.py -> backend/app/utils/ -> backend/app/prompts/
    current_file = os.path.abspath(__file__)
    app_dir = os.path.dirname(os.path.dirname(current_file))
    return os.path.join(app_dir, 'prompts')


def load_markdown(filename: str) -> str:
    """
    从 prompts 目录加载 Markdown 文件，支持子文件夹路径

    Args:
        filename: 文件名或相对路径（如 'CHAT/roleplay_system.md' 或 'TTI/prompt_generator.md'）

    Returns:
        文件内容字符串
    """
    prompts_dir = get_prompts_dir()
    filepath = os.path.join(prompts_dir, filename)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"[Prompts] 文件不存在: {filepath}")
        raise
    except Exception as e:
        print(f"[Prompts] 加载失败 {filepath}: {e}")
        raise


def parse_yaml_from_markdown(content: str) -> dict:
    """
    从 Markdown 内容中提取 YAML 配置区

    Args:
        content: Markdown 文件内容

    Returns:
        解析后的 YAML 字典
    """
    import yaml
    # 查找 ```yaml ... ``` 代码块
    yaml_match = re.search(r'```yaml\n(.*?)\n```', content, re.DOTALL)
    if yaml_match:
        try:
            return yaml.safe_load(yaml_match.group(1)) or {}
        except yaml.YAMLError as e:
            print(f"[Prompts] YAML解析错误: {e}")
            return {}
    return {}


# 缓存提示词内容
_prompt_cache = {}


# ============================================================
# CHAT 模块 - AI角色聊天
# ============================================================

def get_roleplay_system_prompt() -> str:
    """获取角色扮演系统提示词"""
    if 'roleplay_system' not in _prompt_cache:
        _prompt_cache['roleplay_system'] = load_markdown(
            'CHAT/roleplay_system.md')
    return _prompt_cache['roleplay_system']


def get_roleplay_system_fallback_prompt() -> str:
    """获取角色扮演 fallback 系统提示词（主文件加载失败时使用）"""
    if 'roleplay_system_fallback' not in _prompt_cache:
        _prompt_cache['roleplay_system_fallback'] = load_markdown(
            'CHAT/roleplay_system_fallback.md')
    return _prompt_cache['roleplay_system_fallback']


def get_roleplay_story_prompt() -> str:
    """获取剧情模式角色扮演系统提示词"""
    if 'roleplay_story' not in _prompt_cache:
        _prompt_cache['roleplay_story'] = load_markdown(
            'CHAT/roleplay_story.md')
    return _prompt_cache['roleplay_story']


def get_appearance_tags_generator_prompt() -> str:
    """获取外貌描述转SD Tags生成提示词"""
    if 'appearance_tags_generator' not in _prompt_cache:
        _prompt_cache['appearance_tags_generator'] = load_markdown(
            'CHAT/appearance_tags_generator.md')
    return _prompt_cache['appearance_tags_generator']


def get_role_generator_prompt() -> str:
    """获取角色生成器提示词"""
    if 'role_generator' not in _prompt_cache:
        _prompt_cache['role_generator'] = load_markdown(
            'CHAT/role_generator.md')
    return _prompt_cache['role_generator']


def get_voice_config() -> dict:
    """获取声音配置（YAML）"""
    if 'voice_config' not in _prompt_cache:
        content = load_markdown('CHAT/voice_config.md')
        _prompt_cache['voice_config'] = parse_yaml_from_markdown(content)
    return _prompt_cache['voice_config']


# ============================================================
# TTI 模块 - 文生图
# ============================================================

def get_scene_analyzer_prompt() -> str:
    """获取场景分析提示词"""
    if 'scene_analyzer' not in _prompt_cache:
        _prompt_cache['scene_analyzer'] = load_markdown(
            'TTI/scene_analyzer.md')
    return _prompt_cache['scene_analyzer']


def get_visual_describer_prompt() -> str:
    """获取视觉描述生成提示词"""
    if 'visual_describer' not in _prompt_cache:
        _prompt_cache['visual_describer'] = load_markdown(
            'TTI/visual_describer.md')
    return _prompt_cache['visual_describer']


def get_image_generation_config() -> dict:
    """获取文生图配置（YAML）- Flux架构版本"""
    # 使用新缓存键强制重新加载（version 3.0 更新）
    if 'image_generation_config_v3' not in _prompt_cache:
        content = load_markdown('TTI/image_generation.md')
        _prompt_cache['image_generation_config_v3'] = parse_yaml_from_markdown(
            content)
    return _prompt_cache['image_generation_config_v3']


def get_prompt_generator_prompt() -> str:
    """获取Flux/DiT Prompt生成提示词"""
    # 使用新缓存键强制重新加载（Flux架构更新）
    if 'flux_prompt_generator' not in _prompt_cache:
        _prompt_cache['flux_prompt_generator'] = load_markdown(
            'TTI/prompt_generator.md')
    return _prompt_cache['flux_prompt_generator']


def clear_cache():
    """清除提示词缓存（用于热更新）"""
    _prompt_cache.clear()
