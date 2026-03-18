"""路径处理工具函数"""
import os
from typing import Optional
from urllib.parse import quote, unquote


def get_absolute_path(relative_path: str, base_file: Optional[str] = None) -> str:
    """将相对路径转换为绝对路径
    
    Args:
        relative_path: 相对路径
        base_file: 基准文件路径（用于计算backend目录），如果为None则使用调用文件
        
    Returns:
        绝对路径
    """
    if os.path.isabs(relative_path):
        return relative_path
    
    if base_file is None:
        # 使用调用栈获取调用文件
        import inspect
        frame = inspect.currentframe().f_back
        base_file = frame.f_globals.get('__file__', __file__)
    
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(base_file))))
    return os.path.join(backend_dir, relative_path)


def encode_filename(filepath: str) -> str:
    """URL编码文件名
    
    Args:
        filepath: 文件路径
        
    Returns:
        URL编码后的文件名
    """
    filename = os.path.basename(filepath)
    return quote(filename, safe='')


def decode_filename(filename: str) -> str:
    """URL解码文件名
    
    Args:
        filename: URL编码的文件名
        
    Returns:
        解码后的文件名
    """
    return unquote(filename)


def get_static_url(filepath: str, static_type: str = 'characters') -> str:
    """根据文件路径生成静态文件URL
    
    Args:
        filepath: 文件绝对路径
        static_type: 静态文件类型（characters/scenes/smallscenes/composite/audio）
        
    Returns:
        静态文件URL路径
    """
    filename = encode_filename(filepath)
    
    url_map = {
        'characters': '/static/images/characters',
        'scenes': '/static/images/scenes',
        'smallscenes': '/static/images/smallscenes',
        'composite': '/static/images/composite',
        'audio': '/static/audio/cache'
    }
    
    base_url = url_map.get(static_type, '/static')
    return f"{base_url}/{filename}"


def get_actual_path_from_static_url(static_url: str, config_dir: str, backend_dir: str = None) -> Optional[str]:
    """将静态文件URL转换为实际文件系统路径
    
    Args:
        static_url: 静态文件URL（如 /static/images/characters/filename.png）
        config_dir: 配置的目录路径（可能是相对或绝对路径）
        backend_dir: backend目录路径（如果config_dir是相对路径时需要）
        
    Returns:
        实际文件系统路径，如果无法确定则返回None
    """
    if not static_url.startswith('/static/'):
        return None
    
    # 提取文件名并解码
    filename = decode_filename(os.path.basename(static_url))
    
    # 确定实际路径
    if os.path.isabs(config_dir):
        return os.path.join(config_dir, filename)
    elif backend_dir:
        return os.path.join(backend_dir, config_dir, filename)
    else:
        return None
