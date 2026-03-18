"""统一日志系统"""
import logging
import sys
import os
from typing import Optional

# 尝试导入jsonlogger（可选）
try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False


def setup_logger(
    name: str,
    level: Optional[str] = None,
    use_json: bool = False
) -> logging.Logger:
    """设置结构化日志
    
    Args:
        name: 日志器名称（通常是 __name__）
        level: 日志级别（DEBUG/INFO/WARNING/ERROR），如果为None则从环境变量读取
        use_json: 是否使用JSON格式（生产环境推荐）
        
    Returns:
        配置好的Logger实例
    """
    logger = logging.getLogger(name)
    
    # 如果已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 确定日志级别
    if level is None:
        level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logger.setLevel(getattr(logging, level, logging.INFO))
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level, logging.INFO))
    
    # 选择格式化器
    if use_json and JSON_LOGGER_AVAILABLE:
        formatter = jsonlogger.JsonFormatter(
            '%(asctime)s %(name)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """获取日志器（便捷方法）
    
    Args:
        name: 日志器名称（通常是 __name__）
        
    Returns:
        Logger实例
    """
    return setup_logger(name)
