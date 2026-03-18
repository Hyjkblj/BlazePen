# 玩家ID与角色ID设计说明

## 概述
本文档说明玩家ID（user_id）和角色ID（character_id）的设计、生成方式、使用场景和命名规则。

## 1. 玩家ID (user_id)

### 1.1 基本信息
- **类型**：字符串 (str)
- **格式**：UUID字符串（如：`"f8a4a002-b381-4679-91bb-bca30f136edb"`）
- **默认值**：`"UNKNOWN"`（当未提供时用于文件命名）

### 1.2 生成方式

#### 方式1：前端提供
```typescript
// 前端创建角色时可以提供user_id
const request = {
  name: "角色名",
  user_id: "user-123",  // 可选
  ...
};
```

#### 方式2：后端自动生成（游戏初始化）
```python
# backend/api/services/game_session.py
def create_session(self, user_id: Optional[str], ...):
    if not user_id:
        user_id = str(uuid.uuid4())  # 自动生成UUID
```

#### 方式3：使用默认值（图片文件命名）
```python
# backend/api/services/image_service.py
def _save_image_to_local(self, ..., user_id: Optional[str] = None, ...):
    if not user_id:
        user_id = 'UNKNOWN'  # 用于文件命名
```

### 1.3 使用场景

1. **游戏会话管理**
   - 存储在`GameSession`中
   - 用于标识游戏会话的拥有者

2. **文件命名**
   - 角色图片：`{user_id}_{character_id:04d}_{角色名称}_portrait_v{version}_{timestamp}.png`
   - 场景图片：`{user_id}_SCENE_{scene_id}_{场景名称}_scene_v{version}_{timestamp}.jpg`
   - 合成图片：`{user_id}_{character_id:04d}_SCENE_{scene_id}_composite_v{version}_{timestamp}.jpg`

3. **示例文件名**
   ```
   UNKNOWN_0030_曾照微_portrait_v1_20260122_015639.png
   UNKNOWN_SCENE_playground_操场_scene_v5_20260121_232737.jpg
   UNKNOWN_0030_SCENE_playground_composite_v1_20260122_015639.jpg
   ```

### 1.4 存储位置

- **游戏会话**：`GameSession.user_id`（内存中）
- **API请求**：`GameInitRequest.user_id`（可选）
- **文件系统**：作为文件名的一部分

## 2. 角色ID (character_id)

### 2.1 基本信息
- **类型**：整数 (int)
- **格式**：自增整数（如：`30`, `31`, `32`）
- **范围**：从1开始，无上限

### 2.2 生成方式

#### 数据库自增主键
```python
# backend/models/character.py
class Character(Base):
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 数据库自动生成，从1开始递增
```

#### 创建流程
```python
# backend/database/db_manager.py
def create_character(self, ...) -> int:
    character = Character(...)
    session.add(character)
    session.flush()  # 获取ID
    session.commit()
    return character.id  # 返回角色ID
```

### 2.3 使用场景

1. **数据库关联**
   - 作为`characters`表的主键
   - 关联`character_attributes`表（角色属性）
   - 关联`character_states`表（角色状态）

2. **向量数据库关联**
   - 作为ChromaDB中的metadata key
   - 用于检索特定角色的历史对话和事件

3. **文件命名**
   - 角色图片：`{user_id}_{character_id:04d}_{角色名称}_portrait_v{version}_{timestamp}.png`
   - 合成图片：`{user_id}_{character_id:04d}_SCENE_{scene_id}_composite_v{version}_{timestamp}.jpg`
   - 格式：`{character_id:04d}` 表示4位数字，不足补0（如：`0030`）

4. **游戏会话**
   - 存储在`GameSession.character_id`中
   - 用于标识当前游戏会话使用的角色

### 2.4 存储位置

- **数据库**：`characters.id`（PostgreSQL主键）
- **游戏会话**：`GameSession.character_id`（内存中）
- **API请求**：`GameInitRequest.character_id`（必需）
- **文件系统**：作为文件名的一部分

## 3. 文件命名规则

### 3.1 角色图片
```
格式：{user_id}_{character_id:04d}_{角色名称}_{图片类型}_v{版本号}_{时间戳}.{扩展名}

示例：
- UNKNOWN_0030_曾照微_portrait_v1_20260122_015639.png
- UNKNOWN_0030_曾照微_portrait_img2_v1_20260122_015639.png  # 组图索引
```

### 3.2 场景图片
```
格式：{user_id}_SCENE_{scene_id}_{场景名称}_scene_v{版本号}_{时间戳}.{扩展名}

示例：
- UNKNOWN_SCENE_playground_操场_scene_v5_20260121_232737.jpg
- UNKNOWN_SCENE_school_学校_scene_v1_20260119_094723.jpg
```

### 3.3 合成图片
```
格式：{user_id}_{character_id:04d}_SCENE_{scene_id}_composite_v{版本号}_{时间戳}.jpg

示例：
- UNKNOWN_0030_SCENE_playground_composite_v1_20260122_015639.jpg
```

## 4. 数据流

### 4.1 创建角色流程
```
前端创建角色请求
    ↓
后端接收请求（user_id可选）
    ↓
创建Character记录（数据库自动生成character_id）
    ↓
返回character_id给前端
    ↓
前端保存character_id到sessionStorage
```

### 4.2 初始化游戏流程
```
前端初始化游戏请求
    ↓
传递character_id（必需）和user_id（可选）
    ↓
后端创建游戏会话：
  - 如果user_id未提供，自动生成UUID
  - 使用character_id关联角色
    ↓
返回thread_id和user_id
```

### 4.3 图片生成流程
```
生成图片请求
    ↓
使用user_id和character_id构建文件名
    ↓
如果user_id未提供，使用'UNKNOWN'
    ↓
保存文件：{user_id}_{character_id:04d}_{名称}_{类型}_v{版本}_{时间戳}.{扩展名}
```

## 5. 关键代码位置

### 5.1 玩家ID生成
- **游戏会话创建**：`backend/api/services/game_session.py:create_session` (第45-58行)
- **文件命名默认值**：`backend/api/services/image_service.py:_save_image_to_local` (第973-974行)

### 5.2 角色ID生成
- **数据库模型**：`backend/models/character.py:Character` (第14行)
- **创建角色**：`backend/database/db_manager.py:create_character` (第37-82行)
- **返回角色ID**：`backend/api/services/character_service.py:create_character` (第132-171行)

### 5.3 文件命名
- **角色图片**：`backend/api/services/image_service.py:_save_image_to_local` (第1080行)
- **场景图片**：`backend/api/services/image_service.py:_save_image_to_local` (第1063行)
- **合成图片**：`backend/api/services/image_service.py:composite_scene_with_character` (第1463行)

## 6. 设计特点

### 6.1 玩家ID特点
- ✅ **可选性**：前端可以不提供，后端自动生成
- ✅ **灵活性**：支持自定义user_id或使用UUID
- ✅ **默认值**：文件命名时使用'UNKNOWN'作为默认值
- ✅ **唯一性**：使用UUID确保唯一性

### 6.2 角色ID特点
- ✅ **自增性**：数据库自动递增，确保唯一性
- ✅ **持久性**：存储在数据库中，永久保存
- ✅ **关联性**：作为主键关联多个表
- ✅ **格式化**：文件命名时使用4位数字格式（`0030`）

## 7. 相关文件

- `backend/api/services/game_session.py` - 游戏会话管理（user_id生成）
- `backend/models/character.py` - 角色数据库模型（character_id定义）
- `backend/database/db_manager.py` - 数据库管理（character_id生成）
- `backend/api/services/image_service.py` - 图片服务（文件命名规则）
- `backend/api/schemas.py` - API数据模型（请求/响应格式）

## 8. 注意事项

1. **玩家ID**
   - 如果前端不提供user_id，后端会在创建游戏会话时自动生成
   - 文件命名时如果user_id为None，会使用'UNKNOWN'作为默认值
   - user_id主要用于文件命名，不存储在数据库中

2. **角色ID**
   - character_id是必需的，创建角色时必须提供
   - character_id是数据库主键，一旦创建不能修改
   - character_id用于关联向量数据库中的历史数据

3. **文件命名**
   - 所有文件名都包含user_id和character_id（如果适用）
   - 使用4位数字格式（`{character_id:04d}`）确保文件名对齐
   - 文件名中的特殊字符会被清理和替换
