"""辅助工具函数"""
from typing import Dict, Any


def format_state_changes(state_changes: Dict[str, float]) -> str:
    """格式化状态值变化显示"""
    if not state_changes:
        return "无变化"
    
    lines = []
    for state, change in state_changes.items():
        sign = "+" if change > 0 else ""
        lines.append(f"  {state}: {sign}{change:.1f}")
    
    return "\n".join(lines)


def clamp_value(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """限制数值在指定范围内"""
    return max(min_val, min(max_val, value))

