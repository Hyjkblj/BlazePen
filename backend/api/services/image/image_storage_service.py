"""图片存储服务（负责文件管理：保存、删除、查找）"""
from typing import Optional, List, Dict
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

logger = get_logger(__name__)

# 尝试导入依赖
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow未安装，图片格式转换功能将不可用")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests未安装，无法下载图片")


class ImageStorageService:
    """图片存储服务（负责文件管理：保存、删除、查找）
    
    职责：
    - 保存图片到本地
    - 删除图片文件
    - 查找图片文件
    - 获取版本号
    - 获取角色信息（用于文件命名）
    """
    
    def save_image(self, image_url: str, character_id: Optional[int] = None,
                   user_id: Optional[str] = None, image_type: str = 'portrait',
                   scene_id: Optional[str] = None, scene_name: Optional[str] = None,
                   image_index: Optional[int] = None) -> Optional[str]:
        """下载并保存图片到本地（使用详细命名规范）
        
        人物图片命名格式：{玩家ID}_{角色ID:04d}_{角色名称}_{状态类型}_v{版本号}_{时间戳}.{扩展名}
        示例：USER001_0042_Alice_portrait_v1_20241220_143025.jpg
        
        场景图片命名格式：{玩家ID}_SCENE_{场景ID}_{场景名称}_scene_v{版本号}_{时间戳}.{扩展名}
        示例：USER001_SCENE_school_学校_scene_v1_20241220_143025.jpg
        
        Args:
            image_url: 图片URL
            character_id: 角色ID（人物图片必需，场景图片为None）
            user_id: 玩家ID（可选，如果未提供则使用'UNKNOWN'）
            image_type: 图片类型（portrait=立绘, avatar=头像, scene=场景图，默认：portrait）
            scene_id: 场景ID（场景图片必需，人物图片为None）
            scene_name: 场景名称（场景图片可选）
            image_index: 组图索引（1, 2, 3等，可选）
            
        Returns:
            本地文件路径，如果失败返回None
        """
        try:
            # 处理玩家ID
            if not user_id:
                user_id = 'UNKNOWN'
            safe_user_id = re.sub(r'[<>:"/\\|?*\s]', '_', user_id)[:20]
            
            # 根据图片类型选择保存目录
            save_dir = self._get_save_directory(image_type, scene_id)
            if not save_dir:
                logger.error("无法确定保存目录")
                return None
            
            os.makedirs(save_dir, exist_ok=True)
            
            # 下载图片
            if not REQUESTS_AVAILABLE:
                logger.error("requests未安装，无法下载图片")
                return None
            
            img_response = requests.get(image_url, timeout=30)
            if img_response.status_code != 200:
                logger.warning(f"下载图片失败: HTTP {img_response.status_code}")
                return None
            
            # 确定文件扩展名（从Content-Type或URL）
            ext = self._determine_extension(image_url, img_response, character_id)
            
            # 规范化图片类型
            normalized_type = self._normalize_image_type(image_type)
            
            # 根据图片类型生成不同的文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # 如果是组图中的一张，添加索引
            index_suffix = f"_img{image_index}" if image_index else ""
            
            if image_type == 'scene':
                base_filename = self._generate_scene_filename(
                    safe_user_id, scene_id, scene_name, normalized_type, index_suffix
                )
            else:
                base_filename = self._generate_character_filename(
                    safe_user_id, character_id, normalized_type, index_suffix
                )
            
            if not base_filename:
                return None
            
            # 确定版本号（检查已存在的文件）
            version = self.get_next_version(save_dir, base_filename, ext)
            
            # 完整文件名
            filename = f"{base_filename}_v{version}_{timestamp}{ext}"
            filepath = os.path.join(save_dir, filename)
            
            # 保存文件
            self._save_image_file(img_response, filepath, character_id, ext)
            
            logger.info(f"图片已保存: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"保存图片到本地失败: {e}", exc_info=True)
            return None
    
    def delete_unselected_character_images(self, character_id: int, image_urls: List[str], 
                                           selected_index: int) -> int:
        """删除未选中的角色图片
        
        Args:
            character_id: 角色ID
            image_urls: 所有图片URL列表（3张图片的URL）
            selected_index: 选中的图片索引（0, 1, 2）
            
        Returns:
            删除的图片数量
        """
        deleted_count = 0
        try:
            # 获取保存目录
            if os.path.isabs(config.IMAGE_SAVE_DIR):
                save_dir = config.IMAGE_SAVE_DIR
            else:
                save_dir = os.path.join(backend_dir, config.IMAGE_SAVE_DIR)
            
            if not os.path.exists(save_dir):
                return 0
            
            # 从URL中提取文件名（去除路径和参数）
            selected_url = image_urls[selected_index] if selected_index < len(image_urls) else None
            
            # 构建选中图片的文件名（从URL中提取）
            selected_filename = None
            if selected_url:
                # 从URL中提取文件名（可能是完整URL或相对路径）
                if '/static/images/characters/' in selected_url:
                    selected_filename = selected_url.split('/static/images/characters/')[-1].split('?')[0]
                elif '/characters/' in selected_url:
                    selected_filename = selected_url.split('/characters/')[-1].split('?')[0]
                else:
                    # 尝试从URL中提取文件名
                    selected_filename = os.path.basename(selected_url).split('?')[0]
            
            # 查找该角色的所有图片文件（包含_img索引的组图）
            character_id_str = f"{character_id:04d}"
            pattern = re.compile(rf"^[^_]+_{re.escape(character_id_str)}_[^_]+_portrait_img\d+_v\d+_\d{{8}}_\d{{6}}\.(png|jpg|jpeg|webp)$", re.IGNORECASE)
            
            for filename in os.listdir(save_dir):
                if pattern.match(filename):
                    filepath = os.path.join(save_dir, filename)
                    
                    # 检查是否是选中的图片
                    is_selected = False
                    if selected_filename:
                        # 通过文件名匹配（忽略时间戳和版本号，只匹配基础部分）
                        base_match = re.match(rf"^([^_]+_{re.escape(character_id_str)}_[^_]+_portrait_img\d+)_", filename)
                        if base_match:
                            base_part = base_match.group(1)
                            if base_part in selected_filename or selected_filename.startswith(base_part.split('_img')[0]):
                                # 进一步检查索引是否匹配
                                img_match = re.search(r'_img(\d+)', filename)
                                selected_img_match = re.search(r'_img(\d+)', selected_filename) if selected_filename else None
                                if img_match and selected_img_match:
                                    img_index = int(img_match.group(1)) - 1  # img1 -> index 0
                                    selected_img_index = int(selected_img_match.group(1)) - 1
                                    if img_index == selected_index and selected_img_index == selected_index:
                                        is_selected = True
                                elif filename == selected_filename:
                                    is_selected = True
                    
                    # 如果文件名包含_img，且不是选中的，则删除
                    if not is_selected and '_img' in filename:
                        try:
                            os.remove(filepath)
                            deleted_count += 1
                            logger.info(f"已删除未选中的图片: {filename}")
                        except Exception as e:
                            logger.warning(f"删除图片失败 {filename}: {e}", exc_info=True)
            
            return deleted_count
        except Exception as e:
            logger.error(f"删除未选中图片失败: {e}", exc_info=True)
            return deleted_count
    
    def get_latest_character_image_path(self, character_id: int) -> Optional[str]:
        """获取角色最新的图片本地路径（优先返回去除背景后的透明图片）
        
        Args:
            character_id: 角色ID
            
        Returns:
            最新图片的本地路径（优先透明背景图片），如果不存在返回None
        """
        try:
            # 获取保存目录
            if os.path.isabs(config.IMAGE_SAVE_DIR):
                save_dir = config.IMAGE_SAVE_DIR
            else:
                save_dir = os.path.join(backend_dir, config.IMAGE_SAVE_DIR)
            
            if not os.path.exists(save_dir):
                return None
            
            # 构建匹配模式
            character_id_str = f"{character_id:04d}"
            # 匹配去除背景后的透明图片（不包含_img1/img2/img3后缀）
            pattern_transparent = re.compile(rf"^[^_]+_{re.escape(character_id_str)}_[^_]+_portrait_v\d+_\d{{8}}_\d{{6}}\.(png|jpg|jpeg|webp)$", re.IGNORECASE)
            # 匹配原始图片（包含_img1/img2/img3后缀）
            pattern_original = re.compile(rf"^[^_]+_{re.escape(character_id_str)}_[^_]+_portrait_img\d+_v\d+_\d{{8}}_\d{{6}}\.(png|jpg|jpeg|webp)$", re.IGNORECASE)
            
            # 分别查找透明图片和原始图片
            transparent_files = []
            original_files = []
            
            for filename in os.listdir(save_dir):
                filepath = os.path.join(save_dir, filename)
                mtime = os.path.getmtime(filepath)
                
                if pattern_transparent.match(filename):
                    transparent_files.append((filepath, mtime))
                elif pattern_original.match(filename):
                    original_files.append((filepath, mtime))
            
            # 优先返回透明背景图片（按修改时间排序，返回最新的）
            if transparent_files:
                transparent_files.sort(key=lambda x: x[1], reverse=True)
                selected = transparent_files[0][0]
                logger.debug(f"角色 {character_id} 找到透明背景图片: {os.path.basename(selected)}")
                return selected
            
            # 如果没有透明图片，返回原始图片（按修改时间排序，返回最新的）
            if original_files:
                original_files.sort(key=lambda x: x[1], reverse=True)
                selected = original_files[0][0]
                logger.debug(f"角色 {character_id} 未找到透明背景图片，使用原始图片: {os.path.basename(selected)}")
                return selected
            
            return None
            
        except Exception as e:
            logger.warning(f"获取角色图片路径失败: {e}", exc_info=True)
            return None
    
    def get_latest_scene_image_path(self, scene_id: str) -> Optional[str]:
        """获取场景图片本地路径（从smallscenes目录通过场景名称匹配，随机选择一个）
        
        Args:
            scene_id: 场景ID
            
        Returns:
            匹配的图片本地路径，如果不存在返回None
        """
        try:
            import random
            from data.scenes import SUB_SCENES
            
            # 只从smallscenes目录查找
            if not hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR'):
                return None
            
            if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
                small_scene_dir = config.SMALL_SCENE_IMAGE_SAVE_DIR
            else:
                small_scene_dir = os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR)
            
            if not os.path.exists(small_scene_dir):
                return None
            
            # 获取场景的中文名称（用于匹配文件名）
            scene_info = SUB_SCENES.get(scene_id, {})
            scene_name_cn = scene_info.get('name', '')  # 中文名称，如"食堂"、"教室"等
            
            if not scene_name_cn:
                logger.warning(f"未找到场景 {scene_id} 的中文名称，无法匹配图片")
                return None
            
            # 通过中文名称匹配文件名
            matching_files = []
            
            for filename in os.listdir(small_scene_dir):
                # 只匹配图片文件
                if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    continue
                
                # 使用中文名称进行匹配
                if scene_name_cn in filename:
                    filepath = os.path.join(small_scene_dir, filename)
                    matching_files.append(filepath)
            
            if not matching_files:
                logger.warning(f"在smallscenes目录中未找到包含中文名称 '{scene_name_cn}' 的图片文件")
                return None
            
            # 随机选择一个匹配的文件
            selected_file = random.choice(matching_files)
            logger.debug(f"场景 {scene_id} (中文名称: {scene_name_cn}) 通过中文名称匹配到 {len(matching_files)} 个文件，随机选择: {os.path.basename(selected_file)}")
            return selected_file
            
        except Exception as e:
            logger.warning(f"获取场景图片路径失败: {e}", exc_info=True)
            return None
    
    def get_next_version(self, save_dir: str, base_filename: str, ext: str) -> int:
        """获取下一个版本号
        
        检查目录中已存在的同名文件，返回下一个版本号
        
        Args:
            save_dir: 保存目录
            base_filename: 基础文件名（不含版本号和时间戳）
            ext: 文件扩展名
            
        Returns:
            下一个版本号（从1开始）
        """
        try:
            if not os.path.exists(save_dir):
                return 1
            
            # 构建匹配模式：{base_filename}_v{数字}_{时间戳}{ext}
            pattern = re.compile(rf"^{re.escape(base_filename)}_v(\d+)_\d{{8}}_\d{{6}}{re.escape(ext)}$")
            
            max_version = 0
            for filename in os.listdir(save_dir):
                match = pattern.match(filename)
                if match:
                    version = int(match.group(1))
                    max_version = max(max_version, version)
            
            return max_version + 1
        except Exception as e:
            logger.warning(f"获取版本号失败: {e}，使用默认版本号1", exc_info=True)
            return 1
    
    def get_character_info(self, character_id: int) -> Dict[str, str]:
        """获取角色信息（用于文件命名）
        
        Args:
            character_id: 角色ID
            
        Returns:
            包含角色信息的字典
        """
        try:
            from database.db_manager import DatabaseManager
            db_manager = DatabaseManager()
            character = db_manager.get_character(character_id)
            if character:
                return {
                    'name': character.name or f'角色{character_id}',
                    'gender': character.gender or ''
                }
        except Exception as e:
            logger.warning(f"获取角色信息失败: {e}", exc_info=True)
        
        return {
            'name': f'角色{character_id}',
            'gender': ''
        }
    
    def _get_save_directory(self, image_type: str, scene_id: Optional[str] = None) -> Optional[str]:
        """获取保存目录
        
        Args:
            image_type: 图片类型
            scene_id: 场景ID（场景图片需要）
            
        Returns:
            保存目录路径，如果失败返回None
        """
        try:
            if image_type == 'scene':
                # 场景图片保存：判断是小场景还是大场景
                from data.scenes import SUB_SCENES, MAJOR_SCENES
                is_small_scene = scene_id and scene_id in SUB_SCENES
                is_major_scene = scene_id and scene_id in MAJOR_SCENES
                
                if is_small_scene:
                    # 小场景图片保存到smallscenes目录
                    if hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR'):
                        if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
                            return config.SMALL_SCENE_IMAGE_SAVE_DIR
                        else:
                            return os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR)
                    else:
                        # 如果没有配置smallscenes目录，使用scenes目录
                        if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
                            return config.SCENE_IMAGE_SAVE_DIR
                        else:
                            return os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR)
                elif is_major_scene:
                    # 大场景图片保存到scenes目录
                    if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
                        return config.SCENE_IMAGE_SAVE_DIR
                    else:
                        return os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR)
                else:
                    # 未知场景，默认保存到smallscenes目录
                    if hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR'):
                        if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
                            return config.SMALL_SCENE_IMAGE_SAVE_DIR
                        else:
                            return os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR)
                    else:
                        if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
                            return config.SCENE_IMAGE_SAVE_DIR
                        else:
                            return os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR)
            else:
                # 人物图片保存到角色图片目录
                if os.path.isabs(config.IMAGE_SAVE_DIR):
                    return config.IMAGE_SAVE_DIR
                else:
                    return os.path.join(backend_dir, config.IMAGE_SAVE_DIR)
        except Exception as e:
            logger.warning(f"判断场景类型失败: {e}，默认保存到smallscenes目录", exc_info=True)
            if hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR'):
                if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
                    return config.SMALL_SCENE_IMAGE_SAVE_DIR
                else:
                    return os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR)
            else:
                if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
                    return config.SCENE_IMAGE_SAVE_DIR
                else:
                    return os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR)
    
    def _determine_extension(self, image_url: str, img_response, character_id: Optional[int] = None) -> str:
        """确定文件扩展名
        
        Args:
            image_url: 图片URL
            img_response: 响应对象
            character_id: 角色ID（人物图片固定使用PNG）
            
        Returns:
            文件扩展名
        """
        if character_id is not None:
            # 人物图片：固定使用PNG格式
            return '.png'
        else:
            # 场景图片：根据Content-Type或URL推断
            content_type = img_response.headers.get('Content-Type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                return '.jpg'
            elif 'png' in content_type:
                return '.png'
            elif 'webp' in content_type:
                return '.webp'
            else:
                # 从URL推断
                if '.jpg' in image_url.lower() or '.jpeg' in image_url.lower():
                    return '.jpg'
                elif '.png' in image_url.lower():
                    return '.png'
                elif '.webp' in image_url.lower():
                    return '.webp'
                else:
                    return '.jpg'  # 默认使用jpg
    
    def _normalize_image_type(self, image_type: str) -> str:
        """规范化图片类型
        
        Args:
            image_type: 原始图片类型
            
        Returns:
            规范化后的图片类型
        """
        image_type_map = {
            'portrait': 'portrait',  # 立绘
            'avatar': 'avatar',      # 头像
            'scene': 'scene',        # 场景图
            'fullbody': 'fullbody',  # 全身像
            'bust': 'bust'          # 半身像
        }
        return image_type_map.get(image_type.lower(), 'portrait')
    
    def _generate_scene_filename(self, safe_user_id: str, scene_id: Optional[str], 
                                 scene_name: Optional[str], normalized_type: str, 
                                 index_suffix: str) -> Optional[str]:
        """生成场景图片文件名
        
        Args:
            safe_user_id: 安全的用户ID
            scene_id: 场景ID
            scene_name: 场景名称
            normalized_type: 规范化后的图片类型
            index_suffix: 索引后缀
            
        Returns:
            基础文件名，如果失败返回None
        """
        if not scene_id:
            scene_id = 'unknown'
        if not scene_name:
            # 尝试从场景ID获取名称
            try:
                from data.scenes import SCENES
                scene_info = SCENES.get(scene_id, {})
                scene_name = scene_info.get('name', scene_id)
            except:
                scene_name = scene_id
        
        # 清理场景名称
        safe_scene_name = re.sub(r'[<>:"/\\|?*\s]', '_', scene_name)
        safe_scene_name = safe_scene_name.strip()
        if not safe_scene_name:
            safe_scene_name = '场景'
        
        # 清理场景ID
        safe_scene_id = re.sub(r'[<>:"/\\|?*\s]', '_', scene_id)[:30]
        
        return f"{safe_user_id}_SCENE_{safe_scene_id}_{safe_scene_name}_{normalized_type}{index_suffix}"
    
    def _generate_character_filename(self, safe_user_id: str, character_id: Optional[int],
                                    normalized_type: str, index_suffix: str) -> Optional[str]:
        """生成角色图片文件名
        
        Args:
            safe_user_id: 安全的用户ID
            character_id: 角色ID
            normalized_type: 规范化后的图片类型
            index_suffix: 索引后缀
            
        Returns:
            基础文件名，如果失败返回None
        """
        if not character_id:
            logger.warning("人物图片需要character_id")
            return None
        
        # 获取角色信息（用于文件名）
        character_info = self.get_character_info(character_id)
        character_name = character_info.get('name', f'角色{character_id}')
        
        # 清理角色名称中的非法字符
        safe_name = re.sub(r'[<>:"/\\|?*\s]', '_', character_name)
        safe_name = safe_name.strip()
        if not safe_name:
            safe_name = '角色'
        
        return f"{safe_user_id}_{character_id:04d}_{safe_name}_{normalized_type}{index_suffix}"
    
    def _save_image_file(self, img_response, filepath: str, character_id: Optional[int], ext: str):
        """保存图片文件
        
        Args:
            img_response: 响应对象
            filepath: 保存路径
            character_id: 角色ID（人物图片需要转换为PNG）
            ext: 文件扩展名
        """
        # 如果是人物图片且需要转换为PNG，使用PIL进行转换
        if character_id is not None and ext == '.png':
            # 检查下载的图片是否已经是PNG格式
            content_type = img_response.headers.get('Content-Type', '')
            is_png = 'png' in content_type or filepath.lower().endswith('.png')
            
            if is_png:
                # 如果已经是PNG，直接保存
                with open(filepath, 'wb') as f:
                    f.write(img_response.content)
            else:
                # 如果不是PNG，使用PIL转换为PNG
                if PIL_AVAILABLE:
                    try:
                        from io import BytesIO
                        # 从响应内容创建PIL Image对象
                        img = Image.open(BytesIO(img_response.content))
                        
                        # 人物图片使用纯白背景，保存为PNG格式
                        if img.mode == 'RGBA':
                            img.save(filepath, 'PNG')
                        else:
                            img.save(filepath, 'PNG')
                        
                        logger.debug(f"已将图片转换为PNG格式（纯白背景）: {filepath}")
                    except Exception as e:
                        logger.warning(f"图片格式转换失败，使用原始格式保存: {e}", exc_info=True)
                        # 转换失败，直接保存原始内容
                        with open(filepath, 'wb') as f:
                            f.write(img_response.content)
                else:
                    # PIL不可用，直接保存原始内容（但文件名仍然是.png）
                    logger.warning("Pillow未安装，无法转换图片格式，直接保存原始内容")
                    with open(filepath, 'wb') as f:
                        f.write(img_response.content)
        else:
            # 场景图片或其他情况，直接保存
            with open(filepath, 'wb') as f:
                f.write(img_response.content)
