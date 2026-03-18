"""情绪工具函数（用于向量化）"""
from typing import Optional
from models.character import CharacterState


def get_emotion_tags(states: Optional[CharacterState]) -> str:
    """将情绪状态转换为语义标签（用于向量化）
    
    Args:
        states: 角色状态对象
    
    Returns:
        情绪语义标签字符串
    """
    if not states:
        return "情绪状态未知"
    
    tags = []
    
    # 情绪标签（0-100）
    if states.emotion >= 70:
        tags.append("情绪高涨 心情愉悦 积极乐观")
    elif states.emotion >= 40:
        tags.append("情绪稳定 心情平静 状态正常")
    elif states.emotion >= 20:
        tags.append("情绪低落 心情不佳 有些沮丧")
    else:
        tags.append("情绪极差 心情沮丧 非常低落")
    
    # 好感度标签
    if states.favorability >= 70:
        tags.append("对玩家非常有好感 关系亲密 愿意接近")
    elif states.favorability >= 40:
        tags.append("对玩家有好感 关系友好 态度友善")
    elif states.favorability >= 0:
        tags.append("对玩家态度中性 关系一般")
    elif states.favorability >= -30:
        tags.append("对玩家有些反感 关系疏远")
    else:
        tags.append("对玩家有敌意 关系紧张 态度恶劣")
    
    # 信任度标签
    if states.trust >= 70:
        tags.append("高度信任玩家 愿意分享秘密")
    elif states.trust >= 40:
        tags.append("信任玩家 愿意合作")
    elif states.trust < 30:
        tags.append("缺乏信任 保持距离 有所防备")
    
    # 其他重要状态
    if states.happiness >= 70:
        tags.append("非常快乐 心情很好")
    if states.sadness >= 70:
        tags.append("非常悲伤 心情沉重")
    if states.stress >= 70:
        tags.append("压力很大 感到紧张")
    if states.anxiety >= 70:
        tags.append("焦虑不安 感到担忧")
    if states.confidence >= 70:
        tags.append("非常自信 充满信心")
    if states.confidence < 30:
        tags.append("缺乏自信 自我怀疑")
    if states.initiative >= 70:
        tags.append("积极主动 愿意行动")
    if states.initiative < 30:
        tags.append("被动消极 不愿主动")
    if states.caution >= 70:
        tags.append("非常谨慎 小心谨慎")
    if states.caution < 30:
        tags.append("不够谨慎 容易冲动")
    if states.dependence >= 70:
        tags.append("非常依赖 需要支持")
    if states.dependence < 30:
        tags.append("独立自主 不依赖他人")
    if states.hostility >= 70:
        tags.append("敌意很强 态度恶劣")
    
    return " ".join(tags) if tags else "情绪状态正常"


def get_all_states_text(states: Optional[CharacterState]) -> str:
    """获取所有状态值的文本描述（用于存储到向量数据库）
    
    Args:
        states: 角色状态对象
    
    Returns:
        包含所有12个状态值的文本描述
    """
    if not states:
        return "状态值未知"
    
    state_texts = [
        f"好感度{states.favorability:.1f}",
        f"信任度{states.trust:.1f}",
        f"敌意{states.hostility:.1f}",
        f"依赖度{states.dependence:.1f}",
        f"情绪值{states.emotion:.1f}",
        f"压力{states.stress:.1f}",
        f"焦虑{states.anxiety:.1f}",
        f"快乐{states.happiness:.1f}",
        f"悲伤{states.sadness:.1f}",
        f"自信度{states.confidence:.1f}",
        f"主动度{states.initiative:.1f}",
        f"谨慎度{states.caution:.1f}",
    ]
    
    return " ".join(state_texts)


def get_state_changes_text(state_changes: dict) -> str:
    """获取状态值变化的文本描述（用于存储玩家选项的影响）
    
    Args:
        state_changes: 状态值变化字典，如 {'favorability': 5, 'trust': 2}
    
    Returns:
        状态值变化文本描述
    """
    if not state_changes:
        return "无状态变化"
    
    change_texts = []
    for key, value in state_changes.items():
        if value > 0:
            change_texts.append(f"{key}增加{value:.1f}")
        elif value < 0:
            change_texts.append(f"{key}减少{abs(value):.1f}")
        else:
            change_texts.append(f"{key}不变")
    
    return " ".join(change_texts) if change_texts else "无状态变化"


def summarize_story_background(story_background: str) -> str:
    """概括故事背景文本（用于向量化存储）
    
    格式：在什么时间、什么地点、玩家和角色做了什么
    
    Args:
        story_background: 原始故事背景文本
    
    Returns:
        概括后的故事背景文本
    """
    # 简单的概括逻辑，可以后续用AI优化
    # 提取关键信息：时间、地点、动作
    
    # 尝试提取时间信息
    import re
    time_patterns = [
        r'(早上|上午|中午|下午|晚上|夜晚|深夜|凌晨)',
        r'(\d+点|\d+时)',
        r'(今天|明天|昨天|现在|当下|此时)',
    ]
    time_info = None
    for pattern in time_patterns:
        match = re.search(pattern, story_background)
        if match:
            time_info = match.group(1)
            break
    
    # 尝试提取地点信息
    location_patterns = [
        r'(在|于)([^，。\n]+?)(教室|食堂|图书馆|操场|宿舍|咖啡厅|公司|办公室|会议室)',
        r'([^，。\n]+?)(教室|食堂|图书馆|操场|宿舍|咖啡厅|公司|办公室|会议室)',
    ]
    location_info = None
    for pattern in location_patterns:
        match = re.search(pattern, story_background)
        if match:
            # Use the last captured group when available; Python regex does not support group(-1).
            location_info = match.group(match.lastindex) if match.lastindex else match.group(0)
            break
    
    # 提取动作信息（简化：取前50个字符）
    action_info = story_background[:100].replace('\n', ' ').strip()
    
    # 组合概括文本
    parts = []
    if time_info:
        parts.append(f"在{time_info}")
    if location_info:
        parts.append(f"{location_info}")
    if action_info:
        parts.append(f"玩家和角色{action_info}")
    
    if parts:
        return "，".join(parts)
    else:
        # 如果无法提取，返回简化版本
        return story_background[:200].replace('\n', ' ').strip()

