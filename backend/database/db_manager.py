"""PostgreSQL数据库管理"""
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from contextlib import contextmanager
from models.character import Base, Character, CharacterAttribute, CharacterState
from database.integrity import is_unique_constraint_conflict
from database.session_factory import get_engine, get_session_factory


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        # 统一复用共享 engine 和 sessionmaker，避免各领域重复创建连接池。
        self.engine = get_engine()
        self.SessionLocal = get_session_factory()
        self._training_repository = None
    
    def init_db(self):
        """显式初始化数据库表。

        注意：
        1. 该方法只建议由独立脚本或部署初始化流程调用
        2. 业务应用启动时不应再偷偷调用它来补表
        """
        # 显式补充模型注册，避免只导入角色模型时 `Base.metadata`
        # 里缺少训练表定义，导致老入口只建出一部分表。
        self._register_managed_models()
        Base.metadata.create_all(self.engine)

    def _register_managed_models(self):
        """确保当前项目托管的 ORM 模型都已注册到 `Base.metadata`。"""
        import models.story  # noqa: F401
        import models.training  # noqa: F401

    def check_connection(self):
        """检查数据库连接是否可用，不做任何 schema 变更。"""
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    
    @contextmanager
    def get_session(self):
        """获取数据库会话"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_character(self, name: str, gender: str, appearance: str, 
                        personality: str, attributes: dict, scene_id: str = 'school',
                        character_data: dict = None) -> int:
        """创建角色
        
        Args:
            name: 角色名称
            gender: 性别
            appearance: 外观描述（文本，用于兼容）
            personality: 性格描述（文本，用于兼容）
            attributes: 角色属性字典（用于兼容旧系统）
            scene_id: 场景ID
            character_data: 完整的角色数据字典（新系统，包含所有前端数据）
        
        Returns:
            角色ID（用于与ChromaDB关联）
        """
        with self.get_session() as session:
            # 创建角色
            character = Character(
                name=name,
                gender=gender,
                appearance=appearance,
                personality=personality,
                scene_id=scene_id,
                character_data=character_data  # 存储完整的角色数据字典
            )
            session.add(character)
            session.flush()
            
            # 添加决定因素（保留用于兼容）
            if attributes:
                for attr_type, attr_value in attributes.items():
                    attr = CharacterAttribute(
                        character_id=character.id,
                        attribute_type=attr_type,
                        attribute_value=attr_value
                    )
                    session.add(attr)
            
            # 初始化状态值
            state = CharacterState(character_id=character.id)
            session.add(state)
            
            session.commit()
            return character.id  # 返回角色ID，作为与ChromaDB关联的key
    
    def get_character(self, character_id: int) -> Character:
        """获取角色信息
        
        Returns:
            Character对象，包含character_data字段（完整的角色数据字典）
        """
        with self.get_session() as session:
            character = session.query(Character).filter(Character.id == character_id).first()
            return character
    
    def get_character_data(self, character_id: int) -> dict:
        """获取角色的完整数据字典
        
        Args:
            character_id: 角色ID（与ChromaDB关联的key）
        
        Returns:
            完整的角色数据字典，如果不存在则返回None
        """
        with self.get_session() as session:
            character = session.query(Character).filter(Character.id == character_id).first()
            if character and character.character_data:
                return character.character_data
            return None
    
    def get_character_states(self, character_id: int) -> CharacterState:
        """获取角色状态值"""
        with self.get_session() as session:
            state = session.query(CharacterState).filter(
                CharacterState.character_id == character_id
            ).first()
            if state:
                # 在会话关闭前访问所有属性，确保数据已加载
                _ = state.favorability, state.trust, state.hostility, state.dependence, \
                    state.emotion, state.stress, state.anxiety, state.happiness, \
                    state.sadness, state.confidence, state.initiative, state.caution
            return state
    
    def update_character_states(self, character_id: int, state_changes: dict):
        """更新角色状态值"""
        with self.get_session() as session:
            state = session.query(CharacterState).filter(
                CharacterState.character_id == character_id
            ).first()
            
            if state:
                for key, value in state_changes.items():
                    if hasattr(state, key):
                        current_value = getattr(state, key)
                        new_value = max(0, min(100, current_value + value))  # 限制在0-100范围
                        setattr(state, key, new_value)
            
            session.commit()
    
    def get_character_attributes(self, character_id: int) -> dict:
        """获取角色所有决定因素"""
        with self.get_session() as session:
            attributes = session.query(CharacterAttribute).filter(
                CharacterAttribute.character_id == character_id
            ).all()
            
            return {attr.attribute_type: attr.attribute_value for attr in attributes}

    # ========== 训练系统（P1，无Chroma依赖） ==========
    def _get_training_repository(self):
        """按需创建训练域仓储，避免通用管理器在导入阶段直接耦合训练模块。"""
        if self._training_repository is None:
            from training.training_repository import SqlAlchemyTrainingRepository

            self._training_repository = SqlAlchemyTrainingRepository(
                engine=self.engine,
                session_factory=self.SessionLocal,
            )
        return self._training_repository

    def create_training_session_artifacts(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().create_training_session_artifacts(*args, **kwargs)

    def create_training_session(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().create_training_session(*args, **kwargs)

    def get_training_session(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().get_training_session(*args, **kwargs)

    def update_training_session(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().update_training_session(*args, **kwargs)

    def create_training_round(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().create_training_round(*args, **kwargs)

    def get_training_rounds(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().get_training_rounds(*args, **kwargs)

    def get_training_round_by_session_round(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().get_training_round_by_session_round(*args, **kwargs)

    def create_round_evaluation(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().create_round_evaluation(*args, **kwargs)

    def get_round_evaluation_by_round_id(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().get_round_evaluation_by_round_id(*args, **kwargs)

    def get_round_evaluations_by_session(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().get_round_evaluations_by_session(*args, **kwargs)

    def create_kt_snapshot(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().create_kt_snapshot(*args, **kwargs)

    def create_narrative_snapshot(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().create_narrative_snapshot(*args, **kwargs)

    def save_training_round_artifacts(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().save_training_round_artifacts(*args, **kwargs)

    @staticmethod
    def _is_duplicate_round_conflict(exc: IntegrityError) -> bool:
        """保留旧静态方法入口，内部改用统一完整性识别工具。"""
        return is_unique_constraint_conflict(
            exc,
            constraint_name="uq_training_rounds_session_round",
            fallback_token_groups=(
                ("training_rounds", "round_no", "session_id"),
                ("duplicate key", "training_rounds"),
            ),
        )

    def upsert_ending_result(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().upsert_ending_result(*args, **kwargs)

    def get_ending_result(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().get_ending_result(*args, **kwargs)

    def upsert_scenario_recommendation_log(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().upsert_scenario_recommendation_log(*args, **kwargs)

    def get_scenario_recommendation_logs(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().get_scenario_recommendation_logs(*args, **kwargs)

    def create_training_audit_event(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().create_training_audit_event(*args, **kwargs)

    def get_training_audit_events(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().get_training_audit_events(*args, **kwargs)

    def create_kt_observation(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().create_kt_observation(*args, **kwargs)

    def get_kt_observations(self, *args, **kwargs):
        """兼容旧调用：转发到训练域专用仓储。"""
        return self._get_training_repository().get_kt_observations(*args, **kwargs)

