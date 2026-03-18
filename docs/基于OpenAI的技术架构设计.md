# No End Story - 基于 OpenAI 原生框架的技术架构设计

## 一、架构设计原则

### 1.1 技术选型核心
- **AI 模型层**：OpenAI GPT-4 / GPT-4o（文本生成）+ DALL·E 3（图像生成）
- **Agent 框架**：OpenAI Assistants API + Function Calling
- **向量存储**：OpenAI Embeddings + 向量数据库（或使用 OpenAI 的向量存储）
- **后端框架**：Python FastAPI（与 OpenAI SDK 完美集成）
- **前端**：React / Next.js（可选 Unity）

### 1.2 OpenAI 原生框架优势
✅ **统一的 API 接口**：文本生成、图像生成、向量嵌入均通过 OpenAI API  
✅ **Assistants API**：内置 Agent 管理、线程管理、文件管理  
✅ **Function Calling**：结构化输出，可控性强  
✅ **成本透明**：按 token 计费，易于成本控制  
✅ **官方 SDK 支持完善**：Python/Node.js SDK 成熟稳定

---

## 二、整体架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                        前端层 (Frontend)                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ React / Next.js / Unity                               │  │
│  │ • 玩家交互界面                                         │  │
│  │ • 文本/选择输入                                        │  │
│  │ • 图像展示                                            │  │
│  │ • WebSocket / HTTP 通信                               │  │
│  └───────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                   HTTP/WebSocket
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                   后端 API 层 (FastAPI)                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ API Gateway & 路由层                                   │  │
│  │ • 请求路由 / 鉴权                                      │  │
│  │ • Session 管理                                        │  │
│  └───────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│              剧情核心服务层 (Story Service Layer)            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ 剧情 Agent   │  │ AIGC 调度    │  │ 验证与过滤   │      │
│  │ Orchestrator │  │ Orchestrator │  │ Validator    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│            OpenAI 原生框架层 (OpenAI Framework)              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ OpenAI Assistants API                                  │  │
│  │ • Assistant 管理（剧情 Director + Writer）             │  │
│  │ • Thread 管理（玩家会话）                              │  │
│  │ • Function Calling（结构化输出控制）                   │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ OpenAI Chat Completions API                            │  │
│  │ • GPT-4o 文本生成                                      │  │
│  │ • 对话上下文管理                                       │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ OpenAI Images API                                      │  │
│  │ • DALL·E 3 图像生成                                    │  │
│  │ • 图像编辑（可选）                                     │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ OpenAI Embeddings API                                  │  │
│  │ • 文本向量化                                           │  │
│  │ • 语义检索支持                                         │  │
│  └───────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                  数据存储层 (Storage Layer)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PostgreSQL   │  │ Redis        │  │ Vector DB    │      │
│  │ • 玩家状态   │  │ • Session    │  │ • 剧情记忆   │      │
│  │ • 关系数据   │  │ • 缓存       │  │ • 语义检索   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块详细设计

### 3.1 OpenAI Assistants API - 剧情 Agent 引擎

#### 3.1.1 Director Assistant（剧情导演 Agent）

**职责**：规划剧情走向、判断触发条件、控制故事结构

**实现方式**：使用 OpenAI Assistants API 创建专用 Assistant

```python
# 伪代码示例
director_assistant = client.beta.assistants.create(
    name="Story Director",
    instructions="""
    你是一个剧情导演 Agent，负责：
    1. 分析玩家行为对剧情的影响
    2. 决定下一步剧情节点
    3. 判断是否触发关键事件
    4. 输出结构化的剧情规划（JSON格式）
    """,
    model="gpt-4o",
    tools=[
        {"type": "function", "function": {
            "name": "get_story_state",
            "description": "获取当前剧情状态",
            "parameters": {...}
        }},
        {"type": "function", "function": {
            "name": "check_trigger_conditions",
            "description": "检查剧情触发条件",
            "parameters": {...}
        }}
    ]
)
```

**Function Calling 设计**：
- `get_story_state()`：获取当前世界状态、角色关系、情绪值
- `check_trigger_conditions()`：检查事件触发条件
- `update_story_state()`：更新剧情状态
- `plan_next_scene()`：规划下一场景

#### 3.1.2 Writer Assistant（内容生成 Agent）

**职责**：根据 Director 的规划生成具体剧情文本

**实现方式**：使用 OpenAI Assistants API 创建 Writer Assistant

```python
writer_assistant = client.beta.assistants.create(
    name="Story Writer",
    instructions="""
    你是一个故事作家 Agent，负责：
    1. 根据剧情规划生成对话和描述
    2. 保持角色性格一致性
    3. 生成玩家选择选项
    4. 输出结构化故事内容
    """,
    model="gpt-4o",
    tools=[...]
)
```

**Function Calling 设计**：
- `generate_dialogue()`：生成角色对话
- `generate_description()`：生成场景描述
- `generate_choices()`：生成玩家选项

### 3.2 OpenAI Chat Completions API - 灵活生成层

**用途**：用于需要更灵活控制的场景，或作为 Assistants API 的补充

**应用场景**：
- 快速对话生成
- Prompt 模板化生成
- 批量内容生成

```python
# 使用 Chat Completions API
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "你是剧情生成助手..."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.7,
    max_tokens=1000
)
```

### 3.3 OpenAI Images API - AIGC 图像生成

**用途**：生成场景图像、角色立绘

**实现方式**：使用 DALL·E 3 API

```python
# 图像生成
image_response = client.images.generate(
    model="dall-e-3",
    prompt=scene_prompt,
    size="1024x1024",
    quality="standard",
    n=1
)
```

**Prompt 模板设计**：
- 角色一致性模板
- 场景风格模板
- 情绪氛围模板

### 3.4 OpenAI Embeddings API - 记忆检索系统

**用途**：将剧情历史向量化，实现 RAG（检索增强生成）

**实现流程**：
1. 使用 Embeddings API 将剧情片段向量化
2. 存储到向量数据库（如 Pinecone、Weaviate、或 PostgreSQL + pgvector）
3. 检索相关历史注入到 Assistant 的上下文

```python
# 向量化
embedding = client.embeddings.create(
    model="text-embedding-3-large",
    input=story_segment
)

# 存储到向量数据库
vector_db.upsert(
    vectors=[embedding.data[0].embedding],
    metadata={"story_id": ..., "content": ...}
)

# 检索
similar_stories = vector_db.query(
    query_vector=query_embedding,
    top_k=5
)
```

---

## 四、数据流设计

### 4.1 玩家交互到剧情生成的完整流程

```
[玩家输入]
    ↓
[API Gateway - 接收请求]
    ↓
[Session 管理 - 获取/创建 Thread]
    ↓
[剧情 Agent Orchestrator]
    ├─→ [Director Assistant] 
    │     ├─ Function: get_story_state
    │     ├─ Function: check_trigger_conditions
    │     └─ 输出：剧情规划（JSON）
    │
    └─→ [Writer Assistant]
          ├─ 接收：剧情规划 + 历史上下文（RAG检索）
          ├─ Function: generate_dialogue
          ├─ Function: generate_description
          └─ 输出：故事文本（JSON）
    ↓
[验证层 Validator]
    ├─ 内容安全检查
    ├─ 逻辑一致性检查
    └─ 风格一致性检查
    ↓
[图像生成调度]
    └─→ [DALL·E 3 API]
          └─ 生成场景图像
    ↓
[记忆存储]
    ├─ 更新 PostgreSQL（结构化数据）
    ├─ 更新 Redis（缓存）
    └─ 更新 Vector DB（向量记忆）
    ↓
[返回前端]
    └─ JSON: {text, image, choices, state}
```

### 4.2 Thread 管理策略

**OpenAI Assistants API 的核心概念**：
- **Assistant**：Agent 定义（Director、Writer）
- **Thread**：对话线程（每个玩家一个 Thread）
- **Run**：执行一次对话

**Thread 管理设计**：

```python
class ThreadManager:
    def get_or_create_thread(self, user_id: str):
        # 从 Redis 获取 thread_id
        thread_id = redis.get(f"user:{user_id}:thread_id")
        
        if not thread_id:
            # 创建新的 Thread
            thread = client.beta.threads.create()
            thread_id = thread.id
            redis.set(f"user:{user_id}:thread_id", thread_id)
        
        return thread_id
    
    def add_message_to_thread(self, thread_id: str, content: str):
        # 添加用户消息到 Thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content
        )
    
    def run_assistant(self, thread_id: str, assistant_id: str):
        # 运行 Assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
        return run
```

---

## 五、关键技术实现方案

### 5.1 剧情一致性保证机制

#### 方案 1：RAG + 向量检索

1. **历史剧情摘要生成**：定期将剧情历史总结成摘要
2. **向量化存储**：使用 Embeddings API 将摘要向量化
3. **检索注入**：在生成前检索相关历史，注入到 Assistant 的上下文

```python
def get_relevant_context(thread_id: str, query: str, top_k: int = 5):
    # 获取查询向量
    query_embedding = client.embeddings.create(
        model="text-embedding-3-large",
        input=query
    ).data[0].embedding
    
    # 从向量数据库检索
    results = vector_db.query(
        query_vector=query_embedding,
        top_k=top_k,
        filter={"thread_id": thread_id}
    )
    
    # 构建上下文
    context = "\n".join([r.metadata["content"] for r in results])
    return context
```

#### 方案 2：Function Calling + 状态数据库

通过 Function Calling 让 Assistant 主动查询和更新状态数据库

```python
# Function: get_story_state
def get_story_state(thread_id: str):
    state = db.query(
        "SELECT * FROM story_states WHERE thread_id = ?",
        thread_id
    )
    return {
        "current_scene": state.scene,
        "character_relations": state.relations,
        "emotion_values": state.emotions,
        "story_flags": state.flags
    }
```

### 5.2 图像一致性解决方案

#### 方案：角色 Profile + Prompt 模板

```python
class CharacterProfile:
    def __init__(self, character_id: str):
        self.character_id = character_id
        self.name = "Alice"
        self.appearance = {
            "hair": "silver hair",
            "eyes": "light green eyes",
            "clothing": "black coat",
            "style": "anime style"
        }
    
    def build_image_prompt(self, scene_description: str):
        base_prompt = f"{self.name}, {self.appearance['hair']}, {self.appearance['eyes']}, {self.appearance['clothing']}, {self.appearance['style']}"
        return f"{base_prompt}, {scene_description}, consistent character design"
```

### 5.3 成本控制策略

1. **缓存机制**：
   - 相同场景图像缓存（Redis + 对象存储）
   - 常用对话模板缓存

2. **模型选择**：
   - 简单场景使用 GPT-4o-mini（成本更低）
   - 复杂场景使用 GPT-4o

3. **Token 优化**：
   - 使用摘要而非完整历史
   - 压缩 Prompt 长度
   - 使用 Function Calling 减少重复描述

4. **请求频率控制**：
   - 限制并发请求数
   - 实现请求队列
   - 延迟非关键请求

---

## 六、数据库设计

### 6.1 PostgreSQL 表结构

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 线程表（对应 OpenAI Thread）
CREATE TABLE threads (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    openai_thread_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 剧情状态表
CREATE TABLE story_states (
    id UUID PRIMARY KEY,
    thread_id UUID REFERENCES threads(id),
    current_scene VARCHAR(255),
    story_flags JSONB,
    character_relations JSONB,
    emotion_values JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 对话历史表
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    thread_id UUID REFERENCES threads(id),
    role VARCHAR(50), -- user / assistant
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 生成图像缓存表
CREATE TABLE image_cache (
    id UUID PRIMARY KEY,
    prompt_hash VARCHAR(64) UNIQUE,
    image_url TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 6.2 Redis 数据结构

```
# Session 管理
user:{user_id}:thread_id -> thread_id
thread:{thread_id}:last_activity -> timestamp

# 缓存
image:prompt:{prompt_hash} -> image_url
story:scene:{scene_id} -> story_data

# 临时状态
thread:{thread_id}:generating -> true/false
```

### 6.3 向量数据库结构

**使用 Pinecone 或 Weaviate 示例**：

```python
# 向量数据结构
{
    "id": "story_segment_123",
    "values": [0.1, 0.2, ...],  # embedding vector
    "metadata": {
        "thread_id": "...",
        "content": "剧情内容...",
        "scene": "scene_1",
        "timestamp": "...",
        "importance": 0.8  # 重要性评分
    }
}
```

---

## 七、API 接口设计

### 7.1 REST API 端点

```python
# FastAPI 路由示例

# 初始化游戏
POST /api/game/init
Request: {user_id: str}
Response: {thread_id: str, session_id: str}

# 玩家输入
POST /api/game/input
Request: {
    thread_id: str,
    input: str,  # 玩家输入文本
    input_type: str  # "text" | "choice"
}
Response: {
    story_text: str,
    image_url: str,
    choices: List[str],
    state: dict
}

# 获取历史
GET /api/game/history/{thread_id}
Response: {
    conversations: List[dict],
    current_state: dict
}

# 重置游戏
POST /api/game/reset/{thread_id}
Response: {success: bool}
```

### 7.2 WebSocket 接口（可选）

用于实时流式输出

```python
# WebSocket 端点
WS /ws/game/{thread_id}

# 消息格式
{
    "type": "user_input",
    "content": "..."
}

{
    "type": "story_update",
    "content": "...",
    "streaming": true
}
```

---

## 八、开发路线图

### Phase 1: 基础框架搭建（2-3周）

**目标**：建立基本架构和 OpenAI 集成

- [ ] 搭建 FastAPI 后端框架
- [ ] 集成 OpenAI SDK
- [ ] 创建 Director 和 Writer Assistant
- [ ] 实现基础的 Thread 管理
- [ ] 实现简单的文本生成流程
- [ ] 数据库表结构创建

### Phase 2: 核心功能开发（3-4周）

**目标**：实现核心剧情生成功能

- [ ] 完善 Function Calling 设计
- [ ] 实现 RAG 记忆检索系统
- [ ] 集成 DALL·E 3 图像生成
- [ ] 实现验证和过滤层
- [ ] 前端基础 UI 开发
- [ ] API 接口完善

### Phase 3: 一致性优化（2-3周）

**目标**：解决一致性和连贯性问题

- [ ] 图像一致性优化
- [ ] 剧情一致性优化
- [ ] 角色关系图实现
- [ ] 缓存机制优化
- [ ] 性能优化

### Phase 4: 体验优化与测试（2-3周）

**目标**：提升用户体验，进行测试

- [ ] 前端 UI/UX 优化
- [ ] 流式输出实现
- [ ] 成本优化
- [ ] 单元测试和集成测试
- [ ] 性能测试和优化

---

## 九、技术栈总结

| 层级 | 技术/工具 | 用途 |
|------|----------|------|
| **AI 模型** | OpenAI GPT-4o | 文本生成 |
| **AI 模型** | OpenAI DALL·E 3 | 图像生成 |
| **AI 框架** | OpenAI Assistants API | Agent 管理 |
| **AI 工具** | OpenAI Embeddings API | 向量化 |
| **后端框架** | Python FastAPI | API 服务 |
| **AI SDK** | openai-python | OpenAI 官方 SDK |
| **数据库** | PostgreSQL | 结构化数据 |
| **缓存** | Redis | 缓存和 Session |
| **向量数据库** | Pinecone / Weaviate | 向量存储 |
| **前端** | React / Next.js | 用户界面 |
| **通信** | WebSocket / HTTP | 前后端通信 |

---

## 十、关键注意事项

### 10.1 OpenAI API 使用最佳实践

1. **API Key 管理**：使用环境变量，不要硬编码
2. **错误处理**：实现重试机制和 fallback
3. **Rate Limiting**：遵守 OpenAI 的速率限制
4. **成本监控**：记录每次调用的 token 使用量
5. **版本管理**：指定模型版本，避免自动升级导致的问题

### 10.2 安全性

1. **API Key 保护**：后端存储，前端不可见
2. **输入验证**：防止 Prompt 注入攻击
3. **内容过滤**：实现多层内容安全检查
4. **用户数据隔离**：确保 Thread 和数据的正确隔离

### 10.3 性能优化

1. **异步处理**：图像生成等耗时操作异步处理
2. **并发控制**：限制并发请求数量
3. **缓存策略**：合理使用缓存减少 API 调用
4. **流式输出**：使用 Streaming API 提升响应速度

---

## 十一、下一步行动

1. **环境准备**：
   - 申请 OpenAI API Key
   - 设置开发环境
   - 创建项目结构

2. **快速原型**：
   - 实现一个简单的对话流程
   - 验证 OpenAI API 集成
   - 测试基本功能

3. **迭代开发**：
   - 按照开发路线图逐步实现
   - 持续测试和优化
   - 收集用户反馈

---

*本文档将随着开发进程持续更新和完善*
