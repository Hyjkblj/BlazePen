"""AI图片服务（Facade模式，统一接口）"""
from typing import Dict, Any, Optional, List
from api.services.image.image_generation_service import ImageGenerationService
from api.services.image.image_processing_service import ImageProcessingService
from api.services.image.image_composition_service import ImageCompositionService
from api.services.image.image_storage_service import ImageStorageService
from utils.logger import get_logger

logger = get_logger(__name__)


class ImageService:
    """AI图片服务（Facade模式）
    
    职责：
    - 提供统一的图片服务接口
    - 协调各个子服务（生成、处理、合成、存储）
    - 保持向后兼容性
    """
    
    def __init__(self):
        """初始化图片服务（Facade模式）"""
        # 创建各个子服务
        self.storage_service = ImageStorageService()
        self.generation_service = ImageGenerationService(storage_service=self.storage_service)
        self.processing_service = ImageProcessingService(storage_service=self.storage_service)
        self.composition_service = ImageCompositionService()
        
        # 向后兼容：暴露enabled和provider属性
        self.enabled = self.generation_service.enabled
        self.provider = self.generation_service.provider
        self.volcengine_api_url = self.generation_service.volcengine_api_url
    
    # ========== 图片生成相关方法 ==========
    
    def generate_character_image_prompt(self, request_data: Dict[str, Any], generate_group: bool = True, group_count: int = 3) -> str:
        """根据前端接收的人物设定数据生成完整的图片生成prompt
        
        Args:
            request_data: 前端发送的角色创建请求数据
            generate_group: 是否生成组图（默认：True）
            group_count: 组图数量（默认：3）
            
        Returns:
            专业的中文图片生成prompt
        """
        return self.generation_service.generate_character_image_prompt(request_data, generate_group, group_count)
    
    def generate_scene_image_prompt(self, scene_data: Dict[str, Any]) -> str:
        """根据场景数据生成完整的场景图片生成prompt
        
        Args:
            scene_data: 场景数据
            
        Returns:
            专业的中文场景图片生成prompt
        """
        return self.generation_service.generate_scene_image_prompt(scene_data)
    
    def generate_character_image(self, prompt: str, character_id: Optional[int] = None, 
                                 user_id: Optional[str] = None, image_type: str = 'portrait',
                                 generate_group: bool = True, group_count: int = 3) -> Optional[List[str]]:
        """生成角色图片（支持组图生成，供前端三选一）
        
        Args:
            prompt: 图片生成prompt
            character_id: 角色ID（可选，用于保存图片URL）
            user_id: 玩家ID（可选，用于文件命名）
            image_type: 图片类型（portrait=立绘, avatar=头像，默认：portrait）
            generate_group: 是否生成组图（默认：True，生成3张图片供前端选择）
            group_count: 组图数量（默认：3）
            
        Returns:
            图片URL列表（如果生成成功），否则返回None
        """
        return self.generation_service.generate_character_image(
            prompt, character_id, user_id, image_type, generate_group, group_count
        )
    
    def generate_character_image_by_data(self, request_data: Dict[str, Any], character_id: Optional[int] = None,
                                         user_id: Optional[str] = None, image_type: str = 'portrait',
                                         generate_group: bool = True, group_count: int = 3) -> Optional[List[str]]:
        """根据角色数据生成人物图片（便捷方法，支持组图）
        
        Args:
            request_data: 前端发送的角色创建请求数据
            character_id: 角色ID（可选）
            user_id: 玩家ID（可选，用于文件命名）
            image_type: 图片类型（portrait=立绘, avatar=头像，默认：portrait）
            generate_group: 是否生成组图（默认：True，生成3张图片供前端选择）
            group_count: 组图数量（默认：3）
            
        Returns:
            图片URL列表，如果失败返回None
        """
        return self.generation_service.generate_character_image_by_data(
            request_data, character_id, user_id, image_type, generate_group, group_count
        )
    
    def generate_scene_image(self, scene_data: Dict[str, Any], scene_id: Optional[str] = None,
                            user_id: Optional[str] = None) -> Optional[str]:
        """生成场景图片
        
        Args:
            scene_data: 场景数据（包含scene_id, scene_name, scene_description等）
            scene_id: 场景ID（可选，如果scene_data中没有提供）
            user_id: 玩家ID（可选，用于文件命名）
            
        Returns:
            图片URL，如果失败返回None
        """
        return self.generation_service.generate_scene_image(scene_data, scene_id, user_id)
    
    # ========== 图片处理相关方法 ==========
    
    def remove_background_with_rembg(self, image_path: str, output_path: Optional[str] = None, 
                                     character_id: Optional[int] = None, 
                                     rename_to_standard: bool = False) -> Optional[str]:
        """使用rembg的isnet-general-use模型去除图片背景（高质量）
        
        Args:
            image_path: 输入图片路径（本地文件路径或URL）
            output_path: 输出图片路径（可选，如果不提供则自动生成）
            character_id: 角色ID（用于文件命名）
            rename_to_standard: 是否重命名为标准格式（默认：False）
            
        Returns:
            处理后的图片路径（PNG格式，透明背景），如果失败返回None
        """
        return self.processing_service.remove_background_with_rembg(
            image_path, output_path, character_id, rename_to_standard
        )
    
    # ========== 图片合成相关方法 ==========
    
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
        return self.composition_service.composite_scene_with_character(
            scene_image_path, character_image_path, character_id, scene_id, user_id
        )
    
    # ========== 文件管理相关方法 ==========
    
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
        return self.storage_service.delete_unselected_character_images(
            character_id, image_urls, selected_index
        )
    
    def get_latest_character_image_path(self, character_id: int) -> Optional[str]:
        """获取角色最新的图片本地路径（优先返回去除背景后的透明图片）
        
        Args:
            character_id: 角色ID
            
        Returns:
            最新图片的本地路径（优先透明背景图片），如果不存在返回None
        """
        return self.storage_service.get_latest_character_image_path(character_id)
    
    def get_latest_scene_image_path(self, scene_id: str) -> Optional[str]:
        """获取场景图片本地路径（从smallscenes目录通过场景名称匹配，随机选择一个）
        
        Args:
            scene_id: 场景ID
            
        Returns:
            匹配的图片本地路径，如果不存在返回None
        """
        return self.storage_service.get_latest_scene_image_path(scene_id)
    
    # ========== 向后兼容：内部方法（已迁移到子服务） ==========
    
    def _save_image_to_local(self, image_url: str, character_id: Optional[int] = None,
                            user_id: Optional[str] = None, image_type: str = 'portrait',
                            scene_id: Optional[str] = None, scene_name: Optional[str] = None,
                            image_index: Optional[int] = None) -> Optional[str]:
        """下载并保存图片到本地（向后兼容方法）
        
        注意：此方法已迁移到ImageStorageService，保留此方法仅用于向后兼容。
        新代码应直接使用storage_service.save_image()。
        """
        return self.storage_service.save_image(
            image_url, character_id, user_id, image_type, scene_id, scene_name, image_index
        )
    
    def _get_next_version(self, save_dir: str, base_filename: str, ext: str) -> int:
        """获取下一个版本号（向后兼容方法）
        
        注意：此方法已迁移到ImageStorageService，保留此方法仅用于向后兼容。
        """
        return self.storage_service.get_next_version(save_dir, base_filename, ext)
    
    def _get_character_info(self, character_id: int) -> Dict[str, str]:
        """获取角色信息（向后兼容方法）
        
        注意：此方法已迁移到ImageStorageService，保留此方法仅用于向后兼容。
        """
        return self.storage_service.get_character_info(character_id)
