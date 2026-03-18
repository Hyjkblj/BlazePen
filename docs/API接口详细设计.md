# No End Story - API 接口详细设计文档

## 一、API 设计原则

- **RESTful 风格**：使用标准的 HTTP 方法
- **JSON 格式**：所有请求和响应使用 JSON
- **错误处理**：统一的错误响应格式
- **版本控制**：API 路径包含版本号 `/api/v1/`
- **认证机制**：使用 JWT Token 或 Session

---

## 二、认证与授权

### 2.1 认证方式

**JWT Token 认证**（推荐）

```
Header: Authorization: Bearer <token>
```

**Session 认证**（备选）

```
Cookie: session_id=<session_id>
```

### 2.2 Token 获取

```
POST /api/v1/auth/login
POST /api/v1/auth/register
```

---

## 三、核心 API 接口

### 3.1 游戏会话管理

#### 3.1.1 初始化游戏

**接口**：`POST /api/v1/game/init`

**描述**：为玩家创建新的游戏会话和 Thread

**请求**：
```json
{
    "user_id": "uuid",
    "game_mode": "solo",  // solo / story
    "character_id": "uuid"  // 可选，选择角色
}
```

**响应**：
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "session_id": "uuid",
        "thread_id": "uuid",
        "initial_state": {
            "scene": "scene_1",
            "background": "background_url",
            "character": {
                "id": "uuid",
                "name": "Alice",
                "avatar": "avatar_url"
            }
        }
    }
}
```

**错误响应**：
```json
{
    "code": 400,
    "message": "Invalid user_id",
    "data": null
}
```

---

#### 3.1.2 玩家输入处理

**接口**：`POST /api/v1/game/input`

**描述**：处理玩家的输入，生成剧情响应

**请求**：
```json
{
    "thread_id": "uuid",
    "session_id": "uuid",
    "input": {
        "type": "text",  // text | choice
        "content": "我想去海边看看",
        "choice_id": null  // 如果 type 是 choice，这里是对应的选项 ID
    }
}
```

**响应**（同步）：
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "story_content": {
            "text": "你走向海边，阳光洒在海面上...",
            "dialogue": [
                {
                    "speaker": "Alice",
                    "content": "这里真美啊！",
                    "emotion": "happy"
                }
            ],
            "description": "海风轻拂，远处有海鸟..."
        },
        "image": {
            "url": "https://...",
            "prompt": "..."
        },
        "choices": [
            {
                "id": "choice_1",
                "text": "继续沿着海岸走"
            },
            {
                "id": "choice_2",
                "text": "坐下来休息"
            }
        ],
        "state": {
            "scene": "beach",
            "emotion_values": {
                "happiness": 0.8,
                "calm": 0.6
            },
            "flags": ["visited_beach"]
        },
        "metadata": {
            "generation_time": 1.2,
            "tokens_used": 150
        }
    }
}
```

**响应**（流式，使用 Server-Sent Events）：
```
Content-Type: text/event-stream

event: story_start
data: {"type": "story_start"}

event: story_chunk
data: {"type": "text", "content": "你走向海边"}

event: story_chunk
data: {"type": "text", "content": "，阳光洒在海面上..."}

event: image_generating
data: {"type": "image", "status": "generating"}

event: image_ready
data: {"type": "image", "url": "https://..."}

event: choices_ready
data: {"type": "choices", "choices": [...]}

event: story_complete
data: {"type": "complete", "state": {...}}
```

---

#### 3.1.3 获取游戏历史

**接口**：`GET /api/v1/game/history/{thread_id}`

**描述**：获取指定 Thread 的对话历史

**查询参数**：
- `limit`: 返回记录数（默认 50）
- `offset`: 偏移量（默认 0）
- `include_images`: 是否包含图像（默认 true）

**响应**：
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "thread_id": "uuid",
        "conversations": [
            {
                "id": "msg_1",
                "role": "user",
                "content": "我想去海边",
                "timestamp": "2024-01-01T10:00:00Z"
            },
            {
                "id": "msg_2",
                "role": "assistant",
                "content": {
                    "text": "你走向海边...",
                    "image_url": "https://...",
                    "choices": [...]
                },
                "timestamp": "2024-01-01T10:00:05Z"
            }
        ],
        "current_state": {
            "scene": "beach",
            "emotion_values": {...},
            "flags": [...]
        },
        "pagination": {
            "total": 100,
            "limit": 50,
            "offset": 0
        }
    }
}
```

---

#### 3.1.4 获取当前状态

**接口**：`GET /api/v1/game/state/{thread_id}`

**描述**：获取当前游戏状态

**响应**：
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "thread_id": "uuid",
        "current_scene": "beach",
        "character_relations": {
            "Alice": {
                "relationship_level": 5,
                "emotion": "friendly"
            }
        },
        "emotion_values": {
            "happiness": 0.8,
            "calm": 0.6,
            "excitement": 0.4
        },
        "story_flags": [
            "visited_beach",
            "met_alice"
        ],
        "progress": {
            "total_scenes": 10,
            "completed_scenes": 3,
            "completion_rate": 0.3
        }
    }
}
```

---

#### 3.1.5 重置游戏

**接口**：`POST /api/v1/game/reset/{thread_id}`

**描述**：重置游戏到初始状态（保留 Thread，清空历史）

**请求**：
```json
{
    "confirm": true
}
```

**响应**：
```json
{
    "code": 200,
    "message": "Game reset successfully",
    "data": {
        "thread_id": "uuid",
        "new_session_id": "uuid"
    }
}
```

---

### 3.2 角色管理

#### 3.2.1 获取可选角色列表

**接口**：`GET /api/v1/characters`

**响应**：
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "characters": [
            {
                "id": "uuid",
                "name": "Alice",
                "description": "冷静理性的女主角",
                "avatar": "https://...",
                "personality": {
                    "traits": ["冷静", "理性", "独立"],
                    "background": "..."
                }
            }
        ]
    }
}
```

---

#### 3.2.2 获取角色详情

**接口**：`GET /api/v1/characters/{character_id}`

**响应**：
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "id": "uuid",
        "name": "Alice",
        "description": "...",
        "avatar": "https://...",
        "personality": {...},
        "relationship": {
            "current_level": 5,
            "history": [...]
        }
    }
}
```

---

### 3.3 图像管理

#### 3.3.1 重新生成图像

**接口**：`POST /api/v1/images/regenerate`

**描述**：为当前场景重新生成图像

**请求**：
```json
{
    "thread_id": "uuid",
    "scene_id": "scene_1",
    "style_override": null  // 可选，覆盖风格
}
```

**响应**：
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "image_url": "https://...",
        "prompt": "...",
        "generation_time": 3.5
    }
}
```

---

### 3.4 配置与管理

#### 3.4.1 获取游戏配置

**接口**：`GET /api/v1/config`

**响应**：
```json
{
    "code": 200,
    "message": "success",
    "data": {
        "game_modes": ["solo", "story"],
        "characters": [...],
        "settings": {
            "max_history_length": 100,
            "image_generation_enabled": true,
            "streaming_enabled": true
        }
    }
}
```

---

#### 3.4.2 更新用户设置

**接口**：`PUT /api/v1/user/settings`

**请求**：
```json
{
    "preferences": {
        "language": "zh-CN",
        "image_quality": "standard",  // standard | hd
        "streaming": true
    }
}
```

**响应**：
```json
{
    "code": 200,
    "message": "Settings updated",
    "data": {
        "user_id": "uuid",
        "settings": {...}
    }
}
```

---

## 四、WebSocket API（可选）

### 4.1 连接建立

**端点**：`WS /ws/game/{thread_id}`

**认证**：通过 Query 参数传递 Token
```
WS /ws/game/{thread_id}?token=<jwt_token>
```

### 4.2 消息格式

#### 客户端发送

```json
{
    "type": "user_input",
    "data": {
        "input": "我想去海边",
        "input_type": "text"
    }
}
```

```json
{
    "type": "ping",
    "data": {}
}
```

#### 服务器发送

```json
{
    "type": "story_chunk",
    "data": {
        "content": "你走向海边",
        "is_complete": false
    }
}
```

```json
{
    "type": "image_ready",
    "data": {
        "url": "https://..."
    }
}
```

```json
{
    "type": "error",
    "data": {
        "code": "GENERATION_FAILED",
        "message": "Image generation failed"
    }
}
```

---

## 五、错误码定义

| 错误码 | HTTP 状态码 | 说明 |
|--------|------------|------|
| 200 | 200 | 成功 |
| 400 | 400 | 请求参数错误 |
| 401 | 401 | 未认证 |
| 403 | 403 | 无权限 |
| 404 | 404 | 资源不存在 |
| 429 | 429 | 请求频率过高 |
| 500 | 500 | 服务器内部错误 |
| 502 | 502 | OpenAI API 错误 |
| 503 | 503 | 服务暂时不可用 |

### 错误响应格式

```json
{
    "code": 400,
    "message": "Invalid thread_id",
    "data": null,
    "error": {
        "type": "ValidationError",
        "details": {
            "field": "thread_id",
            "reason": "Thread not found"
        }
    }
}
```

---

## 六、Rate Limiting

### 限制规则

- **普通用户**：60 请求/分钟
- **VIP 用户**：300 请求/分钟
- **图像生成**：10 请求/分钟

### 响应头

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 59
X-RateLimit-Reset: 1609459200
```

---

## 七、数据模型

### 7.1 StoryContent

```typescript
interface StoryContent {
    text: string;              // 主要故事文本
    dialogue?: Dialogue[];     // 对话列表
    description?: string;      // 场景描述
    choices?: Choice[];        // 玩家选项
}

interface Dialogue {
    speaker: string;           // 说话者
    content: string;           // 对话内容
    emotion?: string;          // 情绪
    timestamp?: string;        // 时间戳
}

interface Choice {
    id: string;                // 选项 ID
    text: string;              // 选项文本
    consequence_hint?: string; // 后果提示（可选）
}
```

### 7.2 GameState

```typescript
interface GameState {
    thread_id: string;
    current_scene: string;
    character_relations: Record<string, Relation>;
    emotion_values: Record<string, number>;
    story_flags: string[];
    progress?: Progress;
}

interface Relation {
    relationship_level: number;
    emotion: string;
    history?: string[];
}

interface Progress {
    total_scenes: number;
    completed_scenes: number;
    completion_rate: number;
}
```

---

## 八、示例请求

### 8.1 完整游戏流程示例

```bash
# 1. 初始化游戏
curl -X POST https://api.example.com/api/v1/game/init \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "game_mode": "solo",
    "character_id": "char_alice"
  }'

# 2. 玩家输入
curl -X POST https://api.example.com/api/v1/game/input \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread_456",
    "session_id": "session_789",
    "input": {
      "type": "text",
      "content": "我想去海边看看"
    }
  }'

# 3. 选择选项
curl -X POST https://api.example.com/api/v1/game/input \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread_456",
    "session_id": "session_789",
    "input": {
      "type": "choice",
      "choice_id": "choice_1"
    }
  }'
```

---

*本文档将随着开发进程持续更新*
