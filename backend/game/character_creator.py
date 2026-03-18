"""角色创建系统"""
import random
from database.db_manager import DatabaseManager
from data.character_attributes import CHARACTER_ATTRIBUTES


class CharacterCreator:
    """角色创建器"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_character(self, name: str, gender: str, appearance: str, 
                        personality: str, scene_id: str = 'school',
                        character_data: dict = None) -> int:
        """创建角色（重构版：支持存储完整的角色数据字典）
        
        Args:
            name: 角色名称
            gender: 性别（玩家选择）
            appearance: 外观描述（玩家选择，用于兼容）
            personality: 性格描述（玩家选择，用于兼容）
            scene_id: 场景ID
            character_data: 完整的角色数据字典（新系统，包含所有前端数据）
        
        Returns:
            角色ID（用于与ChromaDB关联的key）
        """
        # 随机抽取决定因素（保留用于兼容）
        random_attributes = {}
        for attr_type, options in CHARACTER_ATTRIBUTES.items():
            random_attributes[attr_type] = random.choice(options)
        
        # 创建角色（传递完整的字典数据）
        character_id = self.db_manager.create_character(
            name=name,
            gender=gender,
            appearance=appearance,
            personality=personality,
            attributes=random_attributes,
            scene_id=scene_id,
            character_data=character_data  # 传递完整的字典数据
        )
        
        return character_id  # 返回角色ID，作为与ChromaDB关联的key
    
    def get_character_info(self, character_id: int) -> dict:
        """获取角色完整信息（重构版：优先返回character_data字典）
        
        Args:
            character_id: 角色ID（与ChromaDB关联的key）
        
        Returns:
            角色信息字典，优先使用character_data字段
        """
        character = self.db_manager.get_character(character_id)
        if not character:
            raise ValueError(f"角色 ID {character_id} 不存在")
        
        # 优先使用character_data字段（新系统）
        if character.character_data:
            character_data = character.character_data.copy()
            character_data['id'] = character.id
            character_data['character_id'] = character.id  # 添加character_id字段，用于与ChromaDB关联
        else:
            # 兼容旧系统：从各个字段构建
            attributes = self.db_manager.get_character_attributes(character_id)
            character_data = {
                'id': character.id,
                'character_id': character.id,  # 添加character_id字段，用于与ChromaDB关联
                'name': character.name,
                'gender': character.gender,
                'appearance': character.appearance,
                'personality': character.personality,
                'scene_id': character.scene_id,
                'attributes': attributes,
            }
        
        # 获取状态值
        states = self.db_manager.get_character_states(character_id)
        if states:
            character_data['states'] = {
                'favorability': states.favorability,
                'trust': states.trust,
                'hostility': states.hostility,
                'dependence': states.dependence,
                'emotion': states.emotion,
                'stress': states.stress,
                'anxiety': states.anxiety,
                'happiness': states.happiness,
                'sadness': states.sadness,
                'confidence': states.confidence,
                'initiative': states.initiative,
                'caution': states.caution
            }
        else:
            character_data['states'] = {}
        
        return character_data

