"""图片合成服务（负责将场景图和人物图合成）"""
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
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow未安装，图片合成功能将不可用。请运行: pip install Pillow")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests未安装，无法下载图片")


class ImageCompositionService:
    """图片合成服务（负责将场景图和人物图合成）
    
    职责：
    - 将场景图和人物图合成
    - 处理透明背景
    - 调整图片大小和位置
    """
    
    def __init__(self):
        """初始化图片合成服务"""
        if not PIL_AVAILABLE:
            logger.warning("Pillow未安装，图片合成功能将不可用")
    
    def composite_scene_with_character(self, scene_image_path: str, character_image_path: str,
                                       character_id: Optional[int] = None, scene_id: Optional[str] = None,
                                       user_id: Optional[str] = None) -> Optional[str]:
        """将场景图和人物图合成（场景图作为背景，人物图叠加在上方）
        
        Args:
            scene_image_path: 场景图片本地路径或URL
            character_image_path: 人物图片本地路径或URL（纯白背景，合成时会自动去除）
            character_id: 角色ID（用于文件命名）
            scene_id: 场景ID（用于文件命名）
            user_id: 玩家ID（用于文件命名）
            
        Returns:
            合成后的图片本地路径，如果失败返回None
        """
        if not PIL_AVAILABLE:
            logger.warning("Pillow未安装，无法进行图片合成")
            return None
        
        try:
            # 处理玩家ID
            if not user_id:
                user_id = 'UNKNOWN'
            safe_user_id = re.sub(r'[<>:"/\\|?*\s]', '_', user_id)[:20]
            
            # 下载或读取场景图片
            scene_img = self._load_image(scene_image_path, 'scenes')
            if not scene_img:
                return None
            
            # 下载或读取人物图片
            character_img = self._load_image(character_image_path, 'characters')
            if not character_img:
                return None
            
            # 确保人物图片有透明通道（RGBA模式）
            if character_img.mode != 'RGBA':
                character_img = character_img.convert('RGBA')
            
            # 去除纯白背景：将纯白色像素转换为透明
            character_img = self._remove_white_background(character_img)
            
            # 确保场景图片是RGB模式（合成后转换为RGBA）
            if scene_img.mode != 'RGB':
                scene_img = scene_img.convert('RGB')
            
            # 场景图尺寸（16:9，1920x1080）
            scene_width, scene_height = scene_img.size
            logger.debug(f"场景图尺寸: {scene_width}x{scene_height}")
            
            # 调整人物图片大小（保持宽高比，高度约为场景高度的80-85%）
            target_character_height = int(scene_height * 0.85)
            char_width, char_height = character_img.size
            aspect_ratio = char_width / char_height
            target_character_width = int(target_character_height * aspect_ratio)
            
            # 如果人物宽度超过场景宽度，按宽度缩放
            if target_character_width > scene_width * 0.9:
                target_character_width = int(scene_width * 0.9)
                target_character_height = int(target_character_width / aspect_ratio)
            
            logger.debug(f"人物图原始尺寸: {char_width}x{char_height}")
            logger.debug(f"人物图调整后尺寸: {target_character_width}x{target_character_height}")
            
            # 调整人物图片大小（使用高质量重采样）
            character_img_resized = character_img.resize(
                (target_character_width, target_character_height),
                Image.Resampling.LANCZOS
            )
            
            # 创建合成画布（使用场景图作为背景）
            composite = Image.new('RGBA', (scene_width, scene_height))
            composite.paste(scene_img, (0, 0))
            
            # 计算人物图片在场景中的位置（完全居中）
            char_x = (scene_width - target_character_width) // 2
            char_y = (scene_height - target_character_height) // 2
            
            logger.debug(f"人物图位置: ({char_x}, {char_y})")
            
            # 将人物图片叠加到场景图上（使用alpha通道进行透明合成）
            composite.paste(character_img_resized, (char_x, char_y), character_img_resized)
            
            # 转换为RGB模式（保存为JPEG格式）
            composite_rgb = composite.convert('RGB')
            
            # 创建保存目录
            if os.path.isabs(config.COMPOSITE_IMAGE_SAVE_DIR):
                save_dir = config.COMPOSITE_IMAGE_SAVE_DIR
            else:
                save_dir = os.path.join(backend_dir, config.COMPOSITE_IMAGE_SAVE_DIR)
            os.makedirs(save_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_scene_id = re.sub(r'[<>:"/\\|?*\s]', '_', scene_id or 'unknown')[:30]
            safe_character_id = f"{character_id:04d}" if character_id else "0000"
            
            filename = f"{safe_user_id}_{safe_character_id}_SCENE_{safe_scene_id}_composite_v1_{timestamp}.jpg"
            filepath = os.path.join(save_dir, filename)
            
            # 保存合成图片（JPEG格式，高质量）
            composite_rgb.save(filepath, 'JPEG', quality=95)
            
            logger.info(f"合成图片已保存: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"图片合成失败: {e}", exc_info=True)
            return None
    
    def _load_image(self, image_path: str, image_type: str) -> Optional[Image.Image]:
        """加载图片（支持URL、静态文件路径、本地文件路径）
        
        Args:
            image_path: 图片路径（URL、静态文件路径或本地文件路径）
            image_type: 图片类型（'characters', 'scenes', 'smallscenes'）
            
        Returns:
            PIL Image对象，如果失败返回None
        """
        try:
            if image_path.startswith('http://') or image_path.startswith('https://'):
                # 从URL下载
                if not REQUESTS_AVAILABLE:
                    logger.warning("requests未安装，无法下载图片")
                    return None
                
                response = requests.get(image_path, timeout=30)
                if response.status_code == 200:
                    from io import BytesIO
                    return Image.open(BytesIO(response.content))
                else:
                    logger.warning(f"下载图片失败: HTTP {response.status_code}")
                    return None
            elif image_path.startswith('/static/'):
                # 静态文件URL路径，转换为实际文件系统路径
                decoded_filename = decode_filename(os.path.basename(image_path))
                
                # 根据图片类型确定目录
                actual_path = None
                if image_type == 'characters':
                    if os.path.isabs(config.IMAGE_SAVE_DIR):
                        actual_path = os.path.join(config.IMAGE_SAVE_DIR, decoded_filename)
                    else:
                        actual_path = os.path.join(backend_dir, config.IMAGE_SAVE_DIR, decoded_filename)
                elif image_type == 'scenes':
                    if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
                        actual_path = os.path.join(config.SCENE_IMAGE_SAVE_DIR, decoded_filename)
                    else:
                        actual_path = os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR, decoded_filename)
                elif image_type == 'smallscenes':
                    if hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR'):
                        if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
                            actual_path = os.path.join(config.SMALL_SCENE_IMAGE_SAVE_DIR, decoded_filename)
                        else:
                            actual_path = os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR, decoded_filename)
                
                if actual_path and os.path.exists(actual_path):
                    logger.debug(f"从静态文件路径转换为实际路径: {image_path} -> {actual_path}")
                    return Image.open(actual_path)
                else:
                    logger.warning(f"图片文件不存在: {image_path} (实际路径: {actual_path})")
                    return None
            else:
                # 本地文件路径
                if os.path.exists(image_path):
                    return Image.open(image_path)
                else:
                    logger.warning(f"图片文件不存在: {image_path}")
                    return None
        except Exception as e:
            logger.error(f"加载图片失败: {e}", exc_info=True)
            return None
    
    def _remove_white_background(self, img: Image.Image) -> Image.Image:
        """去除纯白背景（将纯白色像素转换为透明）
        
        Args:
            img: PIL Image对象（RGBA模式）
            
        Returns:
            处理后的图片
        """
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 获取图片数据
        data = img.getdata()
        new_data = []
        
        # 阈值：RGB值都大于等于245的像素视为纯白背景
        threshold = 245
        
        white_pixel_count = 0
        total_pixel_count = len(data)
        
        for item in data:
            # 如果像素是纯白色或接近纯白色，设置为透明
            if item[0] >= threshold and item[1] >= threshold and item[2] >= threshold:
                new_data.append((255, 255, 255, 0))  # 透明
                white_pixel_count += 1
            else:
                new_data.append(item)
        
        img.putdata(new_data)
        white_percentage = (white_pixel_count / total_pixel_count * 100) if total_pixel_count > 0 else 0
        logger.debug(f"已去除白色背景: {white_pixel_count}/{total_pixel_count} 像素 ({white_percentage:.1f}%)")
        
        return img
