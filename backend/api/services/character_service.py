"""角色服务"""
from typing import Dict, Any, Optional, List
from database.db_manager import DatabaseManager
from game.character_creator import CharacterCreator
from data.player_choices import GENDER_OPTIONS, APPEARANCE_OPTIONS, PERSONALITY_OPTIONS
from api.services.image_service import ImageService
from utils.logger import get_logger
import random

logger = get_logger(__name__)


class CharacterNotFoundError(LookupError):
    """Raised when character does not exist."""

    def __init__(self, character_id: int):
        self.character_id = int(character_id)
        super().__init__(f"character not found: {self.character_id}")


class CharacterService:
    """角色服务"""
    
    def __init__(self, image_service: Optional[ImageService] = None):
        """初始化角色服务
        
        Args:
            image_service: 图片服务实例，如果为None则自动创建
        """
        self.db_manager = DatabaseManager()
        self.character_creator = CharacterCreator(self.db_manager)
        self.image_service = image_service or ImageService()  # 初始化图片生成服务
    
    def _parse_character_data(self, request_data: Dict[str, Any]) -> Dict[str, str]:
        """解析前端发送的JSON数据，生成完整的人物设定描述
        
        Args:
            request_data: 创建角色请求数据
            
        Returns:
            包含解析后数据的字典
        """
        name = request_data.get('name', '未命名角色')
        
        # 解析性别
        gender = request_data.get('gender', '')
        if gender == 'male':
            gender_str = '男'
        elif gender == 'female':
            gender_str = '女'
        else:
            gender_str = random.choice(GENDER_OPTIONS)
        
        # 解析外观数据
        appearance = request_data.get('appearance', {})
        appearance_parts = []
        
        if isinstance(appearance, dict):
            # 提取关键词
            keywords = appearance.get('keywords', [])
            if isinstance(keywords, list) and len(keywords) > 0:
                appearance_parts.extend(keywords)
            
            # 提取身高
            height = appearance.get('height')
            if height:
                appearance_parts.append(f'身高{height}cm')
            
            # 提取体重
            weight = appearance.get('weight')
            if weight:
                appearance_parts.append(f'体重{weight}kg')
            
            # 如果有description字段，也加入
            description = appearance.get('description')
            if description:
                appearance_parts.append(description)
        
        # 如果没有外观数据，使用默认值
        if not appearance_parts:
            appearance_parts = [random.choice(APPEARANCE_OPTIONS)]
        
        appearance_str = '，'.join(appearance_parts) if appearance_parts else random.choice(APPEARANCE_OPTIONS)
        
        # 解析性格数据
        personality = request_data.get('personality', {})
        personality_parts = []
        
        if isinstance(personality, dict):
            # 提取关键词
            keywords = personality.get('keywords', [])
            if isinstance(keywords, list) and len(keywords) > 0:
                personality_parts.extend(keywords)
            
            # 如果有traits字段
            traits = personality.get('traits', [])
            if isinstance(traits, list) and len(traits) > 0:
                personality_parts.extend(traits)
        
        # 如果没有性格数据，使用默认值
        if not personality_parts:
            personality_parts = [random.choice(PERSONALITY_OPTIONS)]
        
        personality_str = '，'.join(personality_parts) if personality_parts else random.choice(PERSONALITY_OPTIONS)
        
        # 解析背景数据
        background = request_data.get('background', {})
        background_str = ''
        
        if isinstance(background, dict):
            style = background.get('style')
            if style:
                background_str = f'风格：{style}'
        
        # 解析年龄
        age = request_data.get('age')
        age_str = f'{age}岁' if age else ''
        
        # 生成完整的人物设定描述（用于AI prompt）
        character_prompt_parts = [
            f'姓名：{name}',
            f'性别：{gender_str}',
        ]
        
        if age_str:
            character_prompt_parts.append(age_str)
        
        character_prompt_parts.extend([
            f'外观：{appearance_str}',
            f'性格：{personality_str}',
        ])
        
        if background_str:
            character_prompt_parts.append(background_str)
        
        character_prompt = '；'.join(character_prompt_parts)
        
        return {
            'name': name,
            'gender': gender_str,
            'appearance': appearance_str,
            'personality': personality_str,
            'background': background_str,
            'age': age_str,
            'character_prompt': character_prompt  # 完整的人物设定prompt
        }
    
    def create_character(self, request_data: Dict[str, Any]) -> int:
        """创建角色（重构版：将前端数据作为字典存储）
        
        Args:
            request_data: 创建角色请求数据，包含：
                - name: 角色名称
                - appearance: 外观设定（字典，包含keywords, height, weight等）
                - personality: 性格设定（字典）
                - background: 背景设定（字典）
                - gender: 性别（可选）
                - age: 年龄（可选）
                - weight: 体重（在appearance中）
            
        Returns:
            角色ID（用于与ChromaDB关联的key）
        """
        # 解析前端发送的JSON数据（用于AI生成和兼容）
        parsed_data = self._parse_character_data(request_data)
        
        scene_id = request_data.get('initial_scene', 'school')
        
        # 构建完整的角色数据字典（存储到character_data字段）
        character_data_dict = {
            'name': request_data.get('name', '未命名角色'),
            'gender': request_data.get('gender', ''),
            'age': request_data.get('age'),
            'identity_code': request_data.get('identity_code'),
            'appearance': request_data.get('appearance', {}),
            'personality': request_data.get('personality', {}),
            'background': request_data.get('background', {}),
            'initial_scene': scene_id,
            # 提取体重（如果存在）
            'weight': request_data.get('appearance', {}).get('weight'),
            # 提取身高（如果存在）
            'height': request_data.get('appearance', {}).get('height'),
            # 保留解析后的文本描述（用于AI生成）
            'appearance_text': parsed_data.get('appearance', ''),
            'personality_text': parsed_data.get('personality', ''),
        }
        
        # 创建角色（将完整的字典数据存储到character_data字段）
        character_id = self.character_creator.create_character(
            name=parsed_data['name'],
            gender=parsed_data['gender'],
            appearance=parsed_data['appearance'],
            personality=parsed_data['personality'],
            scene_id=scene_id,
            character_data=character_data_dict  # 传递完整的字典数据
        )
        
        # 返回角色ID（作为与ChromaDB关联的key）
        return character_id
    
    def get_character(self, character_id: int) -> Dict[str, Any]:
        """获取角色信息（重构版：优先返回character_data字典）
        
        Args:
            character_id: 角色ID（与ChromaDB关联的key）
        
        Returns:
            角色信息字典，包含完整的character_data数据
        """
        try:
            character_info = self.character_creator.get_character_info(character_id)
        except ValueError as exc:
            raise CharacterNotFoundError(character_id=character_id) from exc
        
        # 优先使用character_data字段（新系统）
        # 检查是否是字典类型（新系统）还是字符串类型（旧系统）
        appearance_value = character_info.get('appearance')
        is_new_system = isinstance(appearance_value, dict) or character_info.get('character_data') is not None
        
        if is_new_system:
            # 新系统：直接返回character_data字典或从character_info中提取
            # 确保character_id存在且有效
            char_id = character_info.get('id') or character_info.get('character_id')
            if not char_id:
                logger.warning(f"角色信息中缺少character_id，尝试使用传入的参数: {character_info}")
                # 使用传入的character_id参数
                char_id = character_id
            
            if not char_id:
                logger.error(f"无法获取有效的character_id: character_info={character_info}, character_id参数={character_id}")
            
            return {
                'character_id': str(char_id) if char_id else None,
                'name': character_info.get('name', ''),
                'gender': character_info.get('gender', ''),
                'age': character_info.get('age'),
                'identity_code': character_info.get('identity_code'),
                'height': character_info.get('height'),
                'weight': character_info.get('weight'),
                'appearance': character_info.get('appearance', {}),
                'personality': character_info.get('personality', {}),
                'background': character_info.get('background', {}),
                'initial_scene': character_info.get('initial_scene', character_info.get('scene_id', 'school')),
                'identity': character_info.get('initial_scene', character_info.get('scene_id', 'school'))
            }
        
        # 兼容旧系统：从attributes中提取结构化数据
        import json
        attributes = character_info.get('attributes', {})
        
        # 提取年龄
        age = None
        if 'age' in attributes:
            try:
                age = int(attributes['age'])
            except:
                pass
        
        # 提取原始性别
        gender_raw = attributes.get('gender_raw', '')
        if not gender_raw:
            gender_db = character_info.get('gender', '')
            if gender_db == '男':
                gender_raw = 'male'
            elif gender_db == '女':
                gender_raw = 'female'
        
        # 提取结构化外观数据
        appearance_data = {}
        if 'appearance_data' in attributes:
            try:
                appearance_data = json.loads(attributes['appearance_data'])
            except:
                pass
        
        # 如果没有结构化数据，从原始数据重建
        if not appearance_data:
            appearance_data = {
                'keywords': character_info['appearance'].split('，') if '，' in character_info['appearance'] else [character_info['appearance']],
            }
            import re
            appearance_str = character_info['appearance']
            height_match = re.search(r'身高(\d+)cm', appearance_str)
            weight_match = re.search(r'体重(\d+)kg', appearance_str)
            if height_match:
                appearance_data['height'] = int(height_match.group(1))
            if weight_match:
                appearance_data['weight'] = int(weight_match.group(1))
        
        # 提取结构化性格数据
        personality_data = {}
        if 'personality_data' in attributes:
            try:
                personality_data = json.loads(attributes['personality_data'])
            except:
                pass
        
        if not personality_data:
            personality_data = {
                'keywords': character_info['personality'].split('，') if '，' in character_info['personality'] else [character_info['personality']],
            }
        
        # 提取结构化背景数据
        background_data = {}
        if 'background_data' in attributes:
            try:
                background_data = json.loads(attributes['background_data'])
            except:
                pass
        
        # 转换为API响应格式
        # 确保character_id存在且有效
        char_id = character_info.get('id')
        if not char_id:
            logger.warning(f"角色信息中缺少id字段，尝试使用传入的参数: {character_info}")
            # 使用传入的character_id参数
            char_id = character_id
        
        if not char_id:
            logger.error(f"无法获取有效的character_id: character_info={character_info}, character_id参数={character_id}")
        
        return {
            'character_id': str(char_id) if char_id else None,
            'name': character_info.get('name', ''),
            'height': appearance_data.get('height'),
            'weight': appearance_data.get('weight'),
            'age': age,
            'identity_code': attributes.get('identity_code'),
            'gender': gender_raw or (character_info.get('gender') if character_info.get('gender') in ['male', 'female'] else None),
            'appearance': {
                'keywords': appearance_data.get('keywords', []),
                'height': appearance_data.get('height'),
                'weight': appearance_data.get('weight'),
            },
            'personality': {
                'keywords': personality_data.get('keywords', []),
            },
            'background': background_data,
            'identity': character_info.get('scene_id', 'school'),
            'initial_scene': character_info.get('scene_id', 'school')
        }
    
    def get_character_images(self, character_id: int) -> list:
        """根据角色ID从本地文件系统获取角色图片列表（根据格式化命名）
        
        查找格式：{玩家ID}_{角色ID:04d}_{角色名称}_{状态类型}_v{版本号}_{时间戳}.{扩展名}
        示例：USER001_0042_Alice_portrait_v1_20241220_143025.jpg
        
        Args:
            character_id: 角色ID
            
        Returns:
            图片URL列表（本地文件路径，通过静态文件服务访问）
        """
        try:
            import os
            import re
            import config
            
            # 获取保存目录
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if os.path.isabs(config.IMAGE_SAVE_DIR):
                save_dir = config.IMAGE_SAVE_DIR
            else:
                save_dir = os.path.join(backend_dir, config.IMAGE_SAVE_DIR)
            
            if not os.path.exists(save_dir):
                logger.warning(f"图片保存目录不存在: {save_dir}")
                return []
            
            # 构建匹配模式：查找该角色的所有图片
            # 格式：{玩家ID}_{角色ID:04d}_{角色名称}_{状态类型}_v{版本号}_{时间戳}.{扩展名}
            # 或者：{玩家ID}_{角色ID:04d}_{角色名称}_{状态类型}_img{索引}_v{版本号}_{时间戳}.{扩展名}（组图）
            # 注意：人物图片现在固定为PNG格式，但兼容旧格式（jpg/jpeg/webp）
            character_id_str = f"{character_id:04d}"
            pattern = re.compile(rf"^[^_]+_{re.escape(character_id_str)}_[^_]+_[^_]+(?:_img\d+)?_v\d+_\d{{8}}_\d{{6}}\.(png|jpg|jpeg|webp)$", re.IGNORECASE)
            
            # 查找匹配的文件
            matching_files = []
            for filename in os.listdir(save_dir):
                if pattern.match(filename):
                    # 构建静态文件URL路径
                    # 相对路径：/static/images/characters/{filename}
                    static_url = f"/static/images/characters/{filename}"
                    matching_files.append(static_url)
            
            # 按文件名排序（最新的在前）
            matching_files.sort(reverse=True)
            
            if matching_files:
                logger.info(f"找到角色 {character_id} 的 {len(matching_files)} 张本地图片")
            else:
                logger.debug(f"未找到角色 {character_id} 的本地图片")
            
            return matching_files
            
        except Exception as e:
            logger.error(f"获取角色本地图片失败: {e}", exc_info=True)
            return []
    
    def generate_character_image_prompt(self, request_data: Dict[str, Any], generate_group: bool = True, group_count: int = 3) -> str:
        """生成角色图片的prompt
        
        Args:
            request_data: 前端发送的角色创建请求数据
            generate_group: 是否生成组图（默认：True）
            group_count: 组图数量（默认：3）
            
        Returns:
            专业的中文图片生成prompt
        """
        return self.image_service.generate_character_image_prompt(request_data, generate_group, group_count)
    
    def generate_character_image(self, request_data: Dict[str, Any], character_id: Optional[int] = None,
                                 user_id: Optional[str] = None, image_type: str = 'portrait',
                                 generate_group: bool = True, group_count: int = 3) -> Optional[List[str]]:
        """生成角色图片（支持组图，供前端三选一）
        
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
        return self.image_service.generate_character_image_by_data(
            request_data, character_id, user_id, image_type, generate_group, group_count
        )
    
    def generate_scene_image(self, scene_data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[str]:
        """生成场景图片
        
        Args:
            scene_data: 场景数据，包含：
                - scene_id: 场景ID（如'school', 'library'等）
                - scene_name: 场景名称（可选）
                - scene_description: 场景描述（可选）
                - atmosphere: 氛围描述（可选）
                - time_of_day: 时间（如'白天', '夜晚'等，可选）
                - weather: 天气（如'晴天', '雨天'等，可选）
            user_id: 玩家ID（可选，用于文件命名）
            
        Returns:
            图片URL，如果失败返回None
        """
        return self.image_service.generate_scene_image(scene_data, None, user_id)

