"""角色相关数据库模型"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Character(Base):
    """角色主表"""
    __tablename__ = 'characters'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    gender = Column(String(20), nullable=False)  # 性别
    appearance = Column(Text, nullable=False)  # 外观描述（保留用于兼容）
    personality = Column(Text, nullable=False)  # 性格描述（保留用于兼容）
    scene_id = Column(String(50), default='school')  # 场景ID
    # 新增：存储完整的角色数据字典（JSON格式）
    character_data = Column(JSON, nullable=True, comment='完整的角色数据字典，包含外观、性格、年龄、体重等所有前端数据')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    attributes = relationship('CharacterAttribute', back_populates='character', cascade='all, delete-orphan')
    states = relationship('CharacterState', back_populates='character', cascade='all, delete-orphan')


class CharacterAttribute(Base):
    """角色决定因素表"""
    __tablename__ = 'character_attributes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    attribute_type = Column(String(50), nullable=False)  # 属性类型
    attribute_value = Column(Text, nullable=False)  # 属性值
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联关系
    character = relationship('Character', back_populates='attributes')


class CharacterState(Base):
    """角色状态值表"""
    __tablename__ = 'character_states'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    character_id = Column(Integer, ForeignKey('characters.id'), nullable=False)
    
    # 状态值
    favorability = Column(Float, default=0.0)  # 好感度
    trust = Column(Float, default=0.0)  # 信任度
    hostility = Column(Float, default=0.0)  # 敌意
    dependence = Column(Float, default=0.0)  # 依赖度
    emotion = Column(Float, default=50.0)  # 情绪（0-100）
    stress = Column(Float, default=0.0)  # 压力
    anxiety = Column(Float, default=0.0)  # 焦虑
    happiness = Column(Float, default=50.0)  # 快乐
    sadness = Column(Float, default=0.0)  # 悲伤
    confidence = Column(Float, default=50.0)  # 自信度
    initiative = Column(Float, default=50.0)  # 主动度
    caution = Column(Float, default=50.0)  # 谨慎度
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联关系
    character = relationship('Character', back_populates='states')

