"""生图大模型服务（统一接口，支持多提供商）"""
from typing import Optional, List, Dict, Any
import os
import sys

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config
from utils.logger import get_logger

logger = get_logger(__name__)

# 尝试导入依赖
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import dashscope
    from dashscope import ImageSynthesis
    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    dashscope = None
    ImageSynthesis = None


class ImageModelService:
    """生图大模型服务（用于图片生成：角色、场景等）
    
    职责：
    - 图片生成（角色立绘、场景图）
    - 支持多提供商（volcengine seedream、dashscope 通义万相）
    - 统一的接口和错误处理
    """
    
    def __init__(self, provider: Optional[str] = None):
        """初始化生图大模型服务
        
        Args:
            provider: 提供商名称（'volcengine', 'dashscope', 'auto'），如果为None则自动检测
        """
        self.provider = provider or self._auto_detect_provider()
        self.enabled = False
        self.api_url = None
        
        if self.provider == 'volcengine':
            self._init_volcengine()
        elif self.provider == 'dashscope':
            self._init_dashscope()
        
        if self.enabled:
            logger.info(f"生图大模型已启用 - 提供商: {self.provider}, 模型: {self.get_model()}")
    
    def _auto_detect_provider(self) -> str:
        """自动检测可用的提供商"""
        # 优先检查火山引擎
        if REQUESTS_AVAILABLE and config.VOLCENGINE_ARK_API_KEY and config.VOLCENGINE_ARK_API_KEY.strip():
            return 'volcengine'
        # 其次检查DashScope
        if DASHSCOPE_AVAILABLE and config.DASHSCOPE_API_KEY:
            return 'dashscope'
        return 'volcengine'  # 默认
    
    def _init_volcengine(self):
        """初始化火山引擎生图服务"""
        if not REQUESTS_AVAILABLE:
            logger.warning("requests未安装，火山引擎生图功能不可用")
            return
        
        volcengine_key = config.VOLCENGINE_ARK_API_KEY.strip() if config.VOLCENGINE_ARK_API_KEY else ''
        if not volcengine_key:
            logger.warning("未配置VOLCENGINE_ARK_API_KEY，火山引擎生图功能不可用")
            return
        
        # 构建API端点
        region_map = {
            'cn-beijing': 'ark.cn-beijing.volces.com',
            'cn-north-1': 'ark.cn-beijing.volces.com',
        }
        host = region_map.get(config.VOLCENGINE_REGION, 'ark.cn-beijing.volces.com')
        self.api_url = f"https://{host}/api/v3/images/generations"
        self.enabled = True
    
    def _init_dashscope(self):
        """初始化DashScope生图服务"""
        if not DASHSCOPE_AVAILABLE:
            logger.warning("dashscope未安装，通义万相生图功能不可用")
            return
        
        if not config.DASHSCOPE_API_KEY:
            logger.warning("未配置DASHSCOPE_API_KEY，通义万相生图功能不可用")
            return
        
        dashscope.api_key = config.DASHSCOPE_API_KEY
        self.enabled = True
    
    def get_model(self) -> str:
        """获取当前使用的模型名称"""
        if self.provider == 'volcengine':
            return config.VOLCENGINE_IMAGE_MODEL
        elif self.provider == 'dashscope':
            return 'wanx-v1'  # 通义万相默认模型
        return 'unknown'
    
    def get_provider(self) -> str:
        """获取当前使用的提供商名称"""
        return self.provider if self.enabled else "none"
    
    def generate_image(
        self,
        prompt: str,
        size: str = "1440x2560",
        response_format: str = "url",
        watermark: bool = False,
        **kwargs
    ) -> Optional[str]:
        """生成图片（统一接口）
        
        Args:
            prompt: 图片生成提示词
            size: 图片尺寸（如 "1440x2560", "2K", "4K"）
            response_format: 返回格式（"url" 或 "b64_json"）
            watermark: 是否带水印
            **kwargs: 其他参数
            
        Returns:
            图片URL或base64字符串，如果失败返回None
        """
        if not self.enabled:
            logger.warning("生图大模型服务未启用")
            return None
        
        try:
            if self.provider == 'volcengine':
                return self._generate_with_volcengine(prompt, size, response_format, watermark, **kwargs)
            elif self.provider == 'dashscope':
                return self._generate_with_dashscope(prompt, size, response_format, watermark, **kwargs)
            else:
                logger.warning(f"未知的生图提供商: {self.provider}")
                return None
        except Exception as e:
            logger.error(f"生图大模型生成失败: {e}", exc_info=True)
            return None
    
    def _generate_with_volcengine(
        self,
        prompt: str,
        size: str,
        response_format: str,
        watermark: bool,
        **kwargs
    ) -> Optional[str]:
        """使用火山引擎生成图片"""
        headers = {
            "Authorization": f"Bearer {config.VOLCENGINE_ARK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": config.VOLCENGINE_IMAGE_MODEL,
            "prompt": prompt,
            "size": size,
            "response_format": response_format,
            "watermark": watermark,
            "stream": False,
            **kwargs
        }
        
        response = requests.post(
            self.api_url,
            headers=headers,
            json=payload,
            timeout=120
        )
        
        if response.status_code != 200:
            raise ValueError(f"火山引擎生图失败: HTTP {response.status_code}, {response.text[:200]}")
        
        data = response.json()
        if 'data' in data and len(data['data']) > 0:
            image_obj = data['data'][0]
            if response_format == "url":
                return image_obj.get('url')
            elif response_format == "b64_json":
                return image_obj.get('b64_json')
        
        raise ValueError("火山引擎返回格式异常")
    
    def _generate_with_dashscope(
        self,
        prompt: str,
        size: str,
        response_format: str,
        watermark: bool,
        **kwargs
    ) -> Optional[str]:
        """使用DashScope生成图片"""
        response = ImageSynthesis.call(
            model='wanx-v1',
            prompt=prompt,
            size=size,
            n=1,
            **kwargs
        )
        
        if response.status_code == 200:
            if hasattr(response, 'output') and hasattr(response.output, 'results'):
                if len(response.output.results) > 0:
                    result = response.output.results[0]
                    if response_format == "url":
                        return result.get('url')
                    elif response_format == "b64_json":
                        return result.get('b64_json')
        
        raise ValueError(f"DashScope生图失败: {response.status_code}")
