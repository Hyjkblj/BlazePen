"""图片处理服务（负责图片处理操作，如背景去除）"""
from typing import Optional
import sys
import os
from datetime import datetime
import re

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config
from utils.logger import get_logger
from utils.path_utils import decode_filename

logger = get_logger(__name__)

# 尝试导入依赖
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow未安装，图片处理功能将不可用。请运行: pip install Pillow")

try:
    from rembg import remove, new_session
    REMBG_AVAILABLE = True
except Exception as e:
    REMBG_AVAILABLE = False
    logger.warning(f"rembg导入失败，背景去除功能将不可用: {e}")


class ImageProcessingService:
    """图片处理服务（负责图片处理操作，如背景去除）
    
    职责：
    - 使用rembg去除图片背景
    - 图片格式转换
    - 其他图片处理操作
    """
    
    def __init__(self, storage_service=None):
        """初始化图片处理服务
        
        Args:
            storage_service: 图片存储服务实例（用于获取角色信息、版本号等）
        """
        self.storage_service = storage_service
        
        # 初始化rembg会话（使用isnet-general-use模型）
        self.rembg_session = None
        if REMBG_AVAILABLE:
            try:
                # 使用isnet-general-use模型（高质量通用模型）
                self.rembg_session = new_session('isnet-general-use')
                logger.info("rembg背景去除服务已初始化 - 使用模型: isnet-general-use")
            except Exception as e:
                logger.warning(f"rembg会话初始化失败: {e}", exc_info=True)
                self.rembg_session = None
    
    def remove_background_with_rembg(self, image_path: str, output_path: Optional[str] = None, 
                                     character_id: Optional[int] = None, 
                                     rename_to_standard: bool = False) -> Optional[str]:
        """使用rembg的isnet-general-use模型去除图片背景（高质量）
        
        Args:
            image_path: 输入图片路径（本地文件路径或URL）
            output_path: 输出图片路径（可选，如果不提供则自动生成）
            character_id: 角色ID（用于文件命名）
            rename_to_standard: 是否重命名为标准格式（默认：False，使用基于原文件名的命名）
            
        Returns:
            处理后的图片路径（PNG格式，透明背景），如果失败返回None
        """
        if not REMBG_AVAILABLE:
            # 让上层能区分“功能不可用”和“处理失败”，避免直接 500。
            raise RuntimeError("rembg_unavailable")
        
        if not PIL_AVAILABLE:
            raise RuntimeError("pillow_unavailable")
        
        if not self.rembg_session:
            raise RuntimeError("rembg_session_unavailable")
        
        try:
            from io import BytesIO
            import requests
            
            # 读取输入图片
            input_bytes = None
            if image_path.startswith('http://') or image_path.startswith('https://'):
                # 从URL下载
                response = requests.get(image_path, timeout=30)
                if response.status_code == 200:
                    input_bytes = response.content
                else:
                    logger.warning(f"下载图片失败: HTTP {response.status_code}")
                    return None
            elif image_path.startswith('/static/'):
                # 静态文件URL路径，转换为实际文件系统路径
                decoded_filename = decode_filename(os.path.basename(image_path))
                
                logger.debug(f"静态文件URL: {image_path}")
                logger.debug(f"解码后的文件名: {decoded_filename}")
                
                # 根据路径判断文件所在目录
                actual_path = None
                if '/images/characters/' in image_path:
                    # 角色图片
                    if os.path.isabs(config.IMAGE_SAVE_DIR):
                        actual_path = os.path.join(config.IMAGE_SAVE_DIR, decoded_filename)
                    else:
                        actual_path = os.path.join(backend_dir, config.IMAGE_SAVE_DIR, decoded_filename)
                elif '/images/scenes/' in image_path:
                    # 大场景图片
                    if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
                        actual_path = os.path.join(config.SCENE_IMAGE_SAVE_DIR, decoded_filename)
                    else:
                        actual_path = os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR, decoded_filename)
                elif '/images/smallscenes/' in image_path:
                    # 小场景图片
                    if hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR'):
                        if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
                            actual_path = os.path.join(config.SMALL_SCENE_IMAGE_SAVE_DIR, decoded_filename)
                        else:
                            actual_path = os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR, decoded_filename)
                
                logger.debug(f"转换后的实际路径: {actual_path}")
                
                if actual_path and os.path.exists(actual_path):
                    with open(actual_path, 'rb') as f:
                        input_bytes = f.read()
                    logger.debug(f"成功读取文件: {actual_path}")
                else:
                    logger.warning(f"图片文件不存在: {image_path} (实际路径: {actual_path})")
                    return None
            else:
                # 本地文件路径
                if os.path.exists(image_path):
                    with open(image_path, 'rb') as f:
                        input_bytes = f.read()
                else:
                    logger.warning(f"图片文件不存在: {image_path}")
                    return None
            
            # 使用rembg去除背景
            logger.debug(f"开始处理图片: {image_path}")
            output_bytes = remove(input_bytes, session=self.rembg_session)
            
            # 确定输出路径
            if not output_path:
                # 自动生成输出路径（使用角色图片保存目录）
                if os.path.isabs(config.IMAGE_SAVE_DIR):
                    base_dir = config.IMAGE_SAVE_DIR
                else:
                    base_dir = os.path.join(backend_dir, config.IMAGE_SAVE_DIR)
                
                if character_id:
                    if rename_to_standard:
                        # 重命名为标准格式：{玩家ID}_{角色ID:04d}_{角色名称}_portrait_v{版本号}_{时间戳}.png
                        # 获取角色信息（如果提供了存储服务）
                        if self.storage_service:
                            character_info = self.storage_service.get_character_info(character_id)
                            character_name = character_info.get('name', f'角色{character_id}')
                        else:
                            character_name = f'角色{character_id}'
                        
                        safe_name = re.sub(r'[<>:"/\\|?*\s]', '_', character_name).strip()
                        if not safe_name:
                            safe_name = '角色'
                        
                        # 使用UNKNOWN作为默认用户ID
                        safe_user_id = 'UNKNOWN'
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        
                        # 构建标准文件名（不包含_img索引，因为这是唯一图片）
                        base_filename = f"{safe_user_id}_{character_id:04d}_{safe_name}_portrait"
                        
                        # 确定版本号（如果提供了存储服务）
                        if self.storage_service:
                            version = self.storage_service.get_next_version(base_dir, base_filename, '.png')
                        else:
                            version = 1
                        
                        # 完整文件名（标准格式）
                        filename = f"{base_filename}_v{version}_{timestamp}.png"
                        output_path = os.path.join(base_dir, filename)
                        logger.debug(f"将重命名为标准格式: {filename}")
                    else:
                        # 使用基于原文件名的命名逻辑（去掉_img1/img2/img3后缀，保留其他部分）
                        # 从image_path中提取原始文件名
                        if image_path.startswith('/static/'):
                            # 静态文件URL，提取文件名并解码
                            decoded_filename = decode_filename(os.path.basename(image_path))
                            base_name = os.path.splitext(decoded_filename)[0]
                        else:
                            # 本地文件路径
                            base_name = os.path.splitext(os.path.basename(image_path))[0]
                        
                        # 移除URL参数（如果有）
                        base_name = base_name.split('?')[0]
                        
                        # 去掉_img1/img2/img3后缀（如果存在），保留其他部分
                        base_name = re.sub(r'_img\d+', '', base_name)
                        
                        # 确保文件名以.png结尾
                        output_path = os.path.join(base_dir, f"{base_name}.png")
                        
                        # 如果文件已存在，添加时间戳后缀
                        if os.path.exists(output_path):
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                            base_name_with_timestamp = f"{base_name}_{timestamp}"
                            output_path = os.path.join(base_dir, f"{base_name_with_timestamp}.png")
                        
                        logger.debug(f"使用基于原文件名的命名逻辑: {os.path.basename(output_path)}")
                else:
                    # 使用时间戳
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_path = os.path.join(base_dir, f"removed_bg_{timestamp}.png")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 保存处理后的图片
            with open(output_path, 'wb') as f:
                f.write(output_bytes)
            
            logger.info(f"背景去除完成，保存到: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"背景去除失败: {e}", exc_info=True)
            return None
