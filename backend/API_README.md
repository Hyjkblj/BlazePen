# FastAPI 后端接口说明

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动API服务器

```bash
python run_api.py
```

或者：

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 访问API文档

启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API接口列表

### 健康检查

- **GET** `/health` - 检查服务器健康状态

### 角色管理

- **POST** `/api/v1/characters/create` - 创建角色
- **GET** `/api/v1/characters/{character_id}` - 获取角色信息
- **GET** `/api/v1/characters/{character_id}/images` - 获取角色图片列表
- **POST** `/api/v1/characters/initialize-story` - 初始化故事（触发初遇场景）

### 游戏管理

- **POST** `/api/v1/game/init` - 初始化游戏
- **POST** `/api/v1/game/input` - 处理玩家输入
- **GET** `/api/v1/game/check-ending/{thread_id}` - 检查是否满足结局条件
- **POST** `/api/v1/game/trigger-ending` - 触发结局

## 使用流程

### 1. 创建角色

```bash
POST /api/v1/characters/create
{
  "name": "Alice",
  "appearance": {"description": "高挑清秀，气质优雅"},
  "personality": {"traits": ["温柔善良", "善解人意"]},
  "background": {"origin": "城市"},
  "gender": "女"
}
```

### 2. 初始化游戏

```bash
POST /api/v1/game/init
{
  "character_id": "1",
  "game_mode": "solo"
}
```

返回 `thread_id` 和 `user_id`。

### 3. 初始化故事

```bash
POST /api/v1/characters/initialize-story
{
  "thread_id": "uuid",
  "character_id": "1"
}
```

返回初始场景和第一轮对话。

### 4. 处理玩家输入

```bash
POST /api/v1/game/input
{
  "thread_id": "uuid",
  "user_input": "option:1"  # 或自由输入文本
}
```

支持两种方式：
- 选项ID：`"option:1"`, `"option:2"`, `"option:3"`（对应3个选项）
- 自由输入：直接输入文本

### 5. 检查结局

```bash
GET /api/v1/game/check-ending/{thread_id}
```

### 6. 触发结局

```bash
POST /api/v1/game/trigger-ending
{
  "thread_id": "uuid"
}
```

## 响应格式

所有API响应都遵循统一格式：

```json
{
  "code": 200,
  "message": "success",
  "data": {
    // 具体数据
  }
}
```

## 错误处理

- `400`: 参数错误
- `401`: 未授权
- `403`: 权限不足
- `404`: 资源不存在
- `500`: 服务器错误

## 注意事项

1. **thread_id**: 每个游戏会话都有唯一的 `thread_id`，需要保存并在后续请求中使用
2. **character_id**: 角色ID是整数，但在API中作为字符串传递
3. **游戏状态**: 游戏状态保存在内存中，服务器重启后会丢失
4. **CORS**: 当前配置允许所有来源，生产环境应该限制

## 项目结构

```
api/
├── app.py              # FastAPI主应用
├── schemas.py          # Pydantic数据模型
├── response.py         # 响应工具
├── routers/            # API路由
│   ├── characters.py  # 角色管理路由
│   └── game.py        # 游戏管理路由
└── services/          # 服务层
    ├── character_service.py  # 角色服务
    ├── game_service.py        # 游戏服务
    └── game_session.py        # 游戏会话管理
```

## 开发说明

- 使用 FastAPI 框架
- 使用 Pydantic 进行数据验证
- 使用 Uvicorn 作为ASGI服务器
- 支持自动API文档生成（Swagger/ReDoc）

