# 前端 API 接口文档

本文档描述了前端应用中使用的所有 API 接口，包括接口定义、请求参数、响应格式和使用示例。

## 目录

- [API 配置](#api-配置)
- [类型定义](#类型定义)
- [API 接口](#api-接口)
  - [健康检查](#健康检查)
  - [角色管理](#角色管理)
  - [游戏管理](#游戏管理)
- [错误处理](#错误处理)
- [使用示例](#使用示例)

---

## API 配置

### 基础配置

API 服务使用 Axios 进行 HTTP 请求，基础配置如下：

```typescript
baseURL: '/api'
timeout: 30000ms
Content-Type: application/json
```

### 认证机制

API 请求会自动在请求头中添加认证信息：

```typescript
Authorization: Bearer <token>
```

Token 从 `localStorage.getItem('token')` 获取，如果存在则自动添加到请求头中。

### 请求拦截器

所有请求都会经过请求拦截器，自动添加认证 Token：

```typescript
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### 响应拦截器

响应拦截器会自动处理响应数据，并统一处理错误：

```typescript
api.interceptors.response.use(
  (response) => response.data,  // 直接返回 data 字段
  (error) => {
    // 统一错误处理
    // 401: 清除 token 并跳转登录页
    // 403: 权限不足
    // 404: 资源不存在
    // 500: 服务器错误
  }
);
```

---

## 类型定义

### ApiResponse

通用 API 响应格式：

```typescript
interface ApiResponse<T = any> {
  code: number;      // 状态码，200 表示成功
  message: string;   // 响应消息
  data: T;          // 响应数据
}
```

### User

用户信息类型：

```typescript
interface User {
  id: string;
  username: string;
  email?: string;
  createdAt: string;
}
```

### Thread

故事线程类型：

```typescript
interface Thread {
  id: string;
  userId: string;
  title: string;
  createdAt: string;
  updatedAt: string;
}
```

### Message

对话消息类型：

```typescript
interface Message {
  id: string;
  threadId: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: string;
}
```

### StoryState

故事状态类型：

```typescript
interface StoryState {
  id: string;
  threadId: string;
  currentScene: string;
  characters: Record<string, any>;
  emotions: Record<string, number>;
  metadata: Record<string, any>;
}
```

### CreateCharacterRequest

创建角色请求类型：

```typescript
interface CreateCharacterRequest {
  name: string;                    // 角色名称
  appearance: Record<string, any>; // 外观设定
  personality: Record<string, any>; // 性格设定
  background: Record<string, any>;  // 背景设定
  gender?: string;                  // 性别（可选）
  age?: number;                     // 年龄（可选）
  identity?: string;                // 身份（可选）
  initial_scene?: string;           // 初始场景（可选）
  initial_scene_prompt?: string;    // 初始场景提示（可选）
}
```

---

## API 接口

### 健康检查

#### checkServerHealth

检查后端服务健康状态。

**接口路径**: `GET /health`

**请求参数**: 无

**响应类型**: `Promise<boolean>`

**使用示例**:

```typescript
import { checkServerHealth } from '@/services/api';

const isHealthy = await checkServerHealth();
if (isHealthy) {
  console.log('后端服务正常');
} else {
  console.log('后端服务不可用');
}
```

**说明**:
- 超时时间：5 秒
- 返回 `true` 表示服务正常，`false` 表示服务不可用

---

### 角色管理

#### createCharacter

创建新角色。

**接口路径**: `POST /api/v1/characters/create`

**请求参数**:

```typescript
const data: CreateCharacterRequest = {
  name: "Alice",
  appearance: {
    hair: "黑色长发",
    eyes: "棕色",
    height: "165cm"
  },
  personality: {
    traits: ["冷静", "理性", "独立"],
    background: "..."
  },
  background: {
    origin: "城市",
    education: "大学"
  },
  gender: "female",
  age: 22,
  identity: "学生",
  initial_scene: "校园",
  initial_scene_prompt: "在校园里初次相遇"
};
```

**响应格式**:

```typescript
{
  code: 200,
  message: "success",
  data: {
    character_id: "uuid",
    name: "Alice",
    appearance: {...},
    personality: {...},
    background: {...}
  }
}
```

**使用示例**:

```typescript
import { createCharacter } from '@/services/api';

try {
  const response = await createCharacter({
    name: "Alice",
    appearance: { /* ... */ },
    personality: { /* ... */ },
    background: { /* ... */ }
  });
  
  console.log('角色创建成功:', response.data.character_id);
} catch (error) {
  console.error('创建角色失败:', error);
}
```

#### getCharacterImages

获取角色图片列表。

**接口路径**: `GET /api/v1/characters/{characterId}/images`

**请求参数**:
- `characterId` (string): 角色 ID

**响应格式**:

```typescript
{
  data: {
    images: string[]  // 图片 URL 数组
  }
}
```

**使用示例**:

```typescript
import { getCharacterImages } from '@/services/api';

try {
  const response = await getCharacterImages('character-id-123');
  console.log('角色图片:', response.data.images);
} catch (error) {
  console.error('获取角色图片失败:', error);
}
```

**说明**:
- 当前实现返回空数组，实际应该从后端获取
- 接口路径为占位符，需要根据实际后端实现调整

---

### 游戏管理

#### 初始化游戏

**接口路径**: `POST /api/v1/game/init`

**请求参数**:

```typescript
{
  user_id?: string;        // 用户 ID（可选，不提供则自动生成）
  game_mode: string;       // 游戏模式：'solo' | 'story'
  character_id?: string;   // 角色 ID（可选）
}
```

**响应格式**:

```typescript
{
  code: 200,
  message: "success",
  data: {
    thread_id: "uuid",
    user_id: "uuid",
    game_mode: "solo"
  }
}
```

**使用示例**:

```typescript
import api from '@/services/api';

try {
  const response = await api.post('/v1/game/init', {
    game_mode: 'solo',
    character_id: 'character-id-123'
  });
  
  const { thread_id, user_id } = response.data;
  console.log('游戏初始化成功:', thread_id);
} catch (error) {
  console.error('初始化游戏失败:', error);
}
```

#### 处理玩家输入

**接口路径**: `POST /api/v1/game/input`

**请求参数**:

```typescript
{
  thread_id: string;      // 线程 ID
  user_input: string;     // 玩家输入内容
  user_id?: string;       // 用户 ID（可选）
}
```

**响应格式**:

```typescript
{
  code: 200,
  message: "success",
  data: {
    // 故事引擎返回的结果
    // 具体格式取决于 StoryEngine 的实现
  }
}
```

**使用示例**:

```typescript
import api from '@/services/api';

try {
  const response = await api.post('/v1/game/input', {
    thread_id: 'thread-id-123',
    user_input: '我想去海边看看'
  });
  
  console.log('故事响应:', response.data);
} catch (error) {
  console.error('处理输入失败:', error);
}
```

#### 检查结局

**接口路径**: `GET /api/v1/game/check-ending/{thread_id}`

**请求参数**:
- `thread_id` (路径参数): 线程 ID

**响应格式**:

```typescript
{
  code: 200,
  message: "success",
  data: {
    has_ending: boolean;  // 是否满足结局条件
    ending: Ending | null; // 结局信息（如果满足条件）
  }
}
```

**使用示例**:

```typescript
import api from '@/services/api';

try {
  const response = await api.get(`/v1/game/check-ending/${threadId}`);
  
  if (response.data.has_ending) {
    console.log('触发结局:', response.data.ending);
  } else {
    console.log('未满足结局条件');
  }
} catch (error) {
  console.error('检查结局失败:', error);
}
```

#### 触发结局

**接口路径**: `POST /api/v1/game/trigger-ending`

**请求参数**:

```typescript
{
  thread_id: string;  // 线程 ID
}
```

**响应格式**:

```typescript
{
  code: 200,
  message: "success",
  data: {
    // 结局触发结果
  }
}
```

**使用示例**:

```typescript
import api from '@/services/api';

try {
  // 先检查结局
  const checkResponse = await api.get(`/v1/game/check-ending/${threadId}`);
  
  if (checkResponse.data.has_ending) {
    // 触发结局
    const response = await api.post('/v1/game/trigger-ending', {
      thread_id: threadId
    });
    
    console.log('结局已触发:', response.data);
  }
} catch (error) {
  console.error('触发结局失败:', error);
}
```

#### 获取角色信息

**接口路径**: `GET /api/v1/characters/{character_id}`

**请求参数**:
- `character_id` (路径参数): 角色 ID

**响应格式**:

```typescript
{
  code: 200,
  message: "success",
  data: {
    character_id: "uuid",
    name: "Alice",
    appearance: {...},
    personality: {...},
    background: {...},
    identity: string,
    initial_scene: string
  }
}
```

**使用示例**:

```typescript
import api from '@/services/api';

try {
  const response = await api.get(`/v1/characters/${characterId}`);
  console.log('角色信息:', response.data);
} catch (error) {
  if (error.response?.status === 404) {
    console.error('角色不存在');
  } else {
    console.error('获取角色失败:', error);
  }
}
```

#### 初始化故事

**接口路径**: `POST /api/v1/characters/initialize-story`

**请求参数**:

```typescript
{
  thread_id: string;    // 线程 ID
  character_id: string;  // 角色 ID
}
```

**响应格式**:

```typescript
{
  code: 200,
  message: "success",
  data: {
    // 初始场景触发结果
  }
}
```

**使用示例**:

```typescript
import api from '@/services/api';

try {
  const response = await api.post('/v1/characters/initialize-story', {
    thread_id: threadId,
    character_id: characterId
  });
  
  console.log('故事初始化成功:', response.data);
} catch (error) {
  console.error('初始化故事失败:', error);
}
```

---

## 错误处理

### HTTP 状态码处理

API 拦截器会自动处理以下 HTTP 状态码：

| 状态码 | 处理方式 |
|--------|---------|
| 401 | 清除 localStorage 中的 token，并跳转到 `/login` |
| 403 | 输出错误日志："没有权限访问" |
| 404 | 输出错误日志："请求的资源不存在" |
| 500 | 输出错误日志："服务器错误" |
| 其他 | 输出错误日志：`error.response.data?.message || error.message` |

### 网络错误处理

如果请求无法到达服务器（网络错误），会输出错误日志：`网络错误: ${error.message}`

### 错误响应格式

后端返回的错误响应格式：

```typescript
{
  code: number;        // 错误码
  message: string;     // 错误消息
  data: null;
  error?: {            // 可选的详细错误信息
    type: string;
    details: {
      field?: string;
      reason?: string;
    };
  };
}
```

### 错误处理示例

```typescript
import api from '@/services/api';

try {
  const response = await api.post('/v1/game/init', {
    game_mode: 'solo'
  });
  // 处理成功响应
} catch (error: any) {
  if (error.response) {
    // 服务器返回了错误响应
    const { code, message } = error.response.data;
    console.error(`错误 ${code}: ${message}`);
    
    // 根据错误码进行不同处理
    switch (code) {
      case 400:
        // 处理参数错误
        break;
      case 401:
        // 已由拦截器处理，跳转登录页
        break;
      case 404:
        // 处理资源不存在
        break;
      default:
        // 处理其他错误
    }
  } else {
    // 网络错误或其他错误
    console.error('请求失败:', error.message);
  }
}
```

---

## 使用示例

### 完整游戏流程示例

```typescript
import api, { createCharacter } from '@/services/api';

// 1. 创建角色
async function startGame() {
  try {
    // 创建角色
    const characterResponse = await createCharacter({
      name: "Alice",
      appearance: {
        hair: "黑色长发",
        eyes: "棕色"
      },
      personality: {
        traits: ["冷静", "理性"]
      },
      background: {
        origin: "城市"
      }
    });
    
    const characterId = characterResponse.data.character_id;
    
    // 2. 初始化游戏
    const initResponse = await api.post('/v1/game/init', {
      game_mode: 'solo',
      character_id: characterId
    });
    
    const threadId = initResponse.data.thread_id;
    
    // 3. 初始化故事（触发初遇场景）
    const storyResponse = await api.post('/v1/characters/initialize-story', {
      thread_id: threadId,
      character_id: characterId
    });
    
    console.log('游戏开始:', {
      threadId,
      characterId,
      initialScene: storyResponse.data
    });
    
    return { threadId, characterId };
  } catch (error) {
    console.error('启动游戏失败:', error);
    throw error;
  }
}

// 4. 处理玩家输入
async function sendMessage(threadId: string, userInput: string) {
  try {
    const response = await api.post('/v1/game/input', {
      thread_id: threadId,
      user_input: userInput
    });
    
    return response.data;
  } catch (error) {
    console.error('发送消息失败:', error);
    throw error;
  }
}

// 5. 检查结局
async function checkEnding(threadId: string) {
  try {
    const response = await api.get(`/v1/game/check-ending/${threadId}`);
    
    if (response.data.has_ending) {
      // 触发结局
      const endingResponse = await api.post('/v1/game/trigger-ending', {
        thread_id: threadId
      });
      
      return endingResponse.data;
    }
    
    return null;
  } catch (error) {
    console.error('检查结局失败:', error);
    throw error;
  }
}
```

### React 组件中使用示例

```typescript
import { useState, useEffect } from 'react';
import api, { createCharacter } from '@/services/api';
import { Message } from '@/types';

function GameComponent() {
  const [threadId, setThreadId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  
  // 初始化游戏
  useEffect(() => {
    async function init() {
      try {
        setLoading(true);
        
        // 创建角色
        const charResponse = await createCharacter({
          name: "Alice",
          appearance: {},
          personality: {},
          background: {}
        });
        
        // 初始化游戏
        const gameResponse = await api.post('/v1/game/init', {
          game_mode: 'solo',
          character_id: charResponse.data.character_id
        });
        
        setThreadId(gameResponse.data.thread_id);
      } catch (error) {
        console.error('初始化失败:', error);
      } finally {
        setLoading(false);
      }
    }
    
    init();
  }, []);
  
  // 发送消息
  const handleSendMessage = async (input: string) => {
    if (!threadId) return;
    
    try {
      setLoading(true);
      
      // 添加用户消息
      const userMessage: Message = {
        id: Date.now().toString(),
        threadId,
        role: 'user',
        content: input,
        createdAt: new Date().toISOString()
      };
      setMessages(prev => [...prev, userMessage]);
      
      // 发送到后端
      const response = await api.post('/v1/game/input', {
        thread_id: threadId,
        user_input: input
      });
      
      // 添加助手回复
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        threadId,
        role: 'assistant',
        content: JSON.stringify(response.data),
        createdAt: new Date().toISOString()
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('发送消息失败:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      {/* 游戏界面 */}
    </div>
  );
}
```

---

## 注意事项

1. **Token 管理**: Token 存储在 `localStorage` 中，键名为 `'token'`。确保在登录后正确设置 token。

2. **错误处理**: 所有 API 调用都应该使用 try-catch 进行错误处理，特别是网络请求可能失败的情况。

3. **超时设置**: 默认超时时间为 30 秒，健康检查为 5 秒。对于长时间运行的请求，可能需要调整超时时间。

4. **路径前缀**: 所有 API 请求会自动添加 `/api` 前缀，实际请求路径为 `/api/v1/...`。

5. **响应数据**: 响应拦截器会自动提取 `response.data`，所以直接使用返回的数据即可，无需再访问 `.data` 属性。

6. **类型安全**: 建议使用 TypeScript 类型定义，确保类型安全。

---

## 更新日志

- **2024-01-XX**: 初始版本，包含基础 API 接口文档

---

*本文档会随着 API 的更新而持续维护*
