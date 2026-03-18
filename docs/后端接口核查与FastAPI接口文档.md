# 后端接口核查与 FastAPI 接口文档

更新日期：2026-03-18

## 1. 核查结论

结论：当前后端接口服务是基于 `FastAPI` 构建的，不是 `festapi`。

直接证据：

1. `backend/requirements.txt` 明确声明了 `fastapi>=0.104.0` 与 `uvicorn[standard]>=0.24.0`。
2. `backend/api/app.py` 中直接创建了 `app = FastAPI(...)`。
3. `backend/api/training_app.py` 中也单独创建了 `app = FastAPI(...)`。
4. `backend/run_api.py` 使用 `uvicorn.run("api.app:app", ...)` 启动主 API。
5. `backend/run_training_api.py` 使用 `uvicorn.run("api.training_app:app", ...)` 启动训练专用 API。

补充说明：

- `backend/main.py` 不是 Web API 入口，而是本地命令行游戏入口。
- 主服务和训练专用服务都能自动暴露 Swagger 文档：`/docs`、`/redoc`、`/openapi.json`。

## 2. 服务入口与端口

### 2.1 主服务

- 启动入口：`backend/run_api.py`
- Uvicorn 应用：`api.app:app`
- 默认端口：`8000`
- 路由范围：
  - 角色管理
  - 游戏流程
  - 向量库管理
  - TTS 语音
  - 训练系统

### 2.2 训练专用服务

- 启动入口：`backend/run_training_api.py`
- Uvicorn 应用：`api.training_app:app`
- 默认端口：`8010`
- 路由范围：
  - 仅训练系统接口

说明：训练接口在两套服务中都存在，路径相同，通常只是监听端口不同。

## 3. 统一响应格式

大部分业务接口都走统一响应壳：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

错误响应通常为：

```json
{
  "code": 400,
  "message": "错误信息",
  "data": null,
  "error": {
    "details": {}
  }
}
```

例外：

- `GET /`
- `GET /health`

这两个接口直接返回简单 JSON，不走统一业务壳。

## 4. 公共接口

### 4.1 文档与健康检查

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 服务根路由，返回服务名、版本、文档地址 |
| GET | `/health` | 健康检查 |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |
| GET | `/openapi.json` | OpenAPI JSON |

### 4.2 静态资源挂载

| 路径前缀 | 用途 |
| --- | --- |
| `/static/images/characters` | 角色图片 |
| `/static/images/scenes` | 大场景图片 |
| `/static/images/smallscenes` | 小场景图片 |
| `/static/images/composite` | 合成图片 |
| `/static/audio/cache` | TTS 音频缓存 |
| `/admin` | 管理页面静态资源 |

## 5. 角色管理接口

路由前缀：`/api/v1/characters`

### 5.1 创建角色

- 方法：`POST`
- 路径：`/api/v1/characters/create`
- 说明：创建角色，并尝试生成角色组图。

请求体：

```json
{
  "name": "角色名称",
  "appearance": {},
  "personality": {},
  "background": {},
  "gender": "female",
  "age": 20,
  "identity": "记者",
  "initial_scene": "school",
  "initial_scene_prompt": "可选场景提示",
  "user_id": "user-001",
  "image_type": "portrait"
}
```

字段说明：

- `name`：必填，角色名称
- `appearance`：必填，外观设定对象
- `personality`：必填，性格设定对象
- `background`：必填，背景设定对象
- `gender`：可选，性别
- `age`：可选，年龄
- `identity`：可选，身份
- `initial_scene`：可选，初始场景
- `initial_scene_prompt`：可选，场景提示
- `user_id`：可选，玩家 ID
- `image_type`：可选，默认 `portrait`

返回重点：

- `data.character_id`
- `data.name`
- `data.image_urls`
- `data.appearance / personality / background`

### 5.2 获取大场景列表

- 方法：`GET`
- 路径：`/api/v1/characters/scenes`
- 说明：返回可选的大场景列表及其图片地址。

返回重点：

- `data.scenes[].id`
- `data.scenes[].name`
- `data.scenes[].description`
- `data.scenes[].imageUrl`
- `data.scenes[].openingEventsCount`

### 5.3 获取指定大场景下的初遇事件列表

- 方法：`GET`
- 路径：`/api/v1/characters/scenes/{major_scene_id}/opening-events`
- 路径参数：
  - `major_scene_id`：大场景 ID

返回重点：

- `data.major_scene_id`
- `data.major_scene_name`
- `data.events[].id`
- `data.events[].title`
- `data.events[].description`
- `data.events[].sub_scene`

### 5.4 获取角色详情

- 方法：`GET`
- 路径：`/api/v1/characters/{character_id}`
- 路径参数：
  - `character_id`：角色 ID，字符串形式传入，内部再转整数

返回重点：

- `data.character_id`
- `data.name`
- `data.appearance`
- `data.personality`
- `data.background`

### 5.5 获取角色图片列表

- 方法：`GET`
- 路径：`/api/v1/characters/{character_id}/images`
- 路径参数：
  - `character_id`

返回重点：

- `data.images`：图片 URL 数组

### 5.6 角色图片去背

- 方法：`POST`
- 路径：`/api/v1/characters/{character_id}/remove-background`

请求体：

```json
{
  "image_url": "/static/images/characters/xxx.png",
  "image_urls": [
    "/static/images/characters/a.png",
    "/static/images/characters/b.png",
    "/static/images/characters/c.png"
  ],
  "selected_index": 1
}
```

字段说明：

- `image_url`：可选，当前选中的图片
- `image_urls`：可选，所有候选图片
- `selected_index`：可选，选中的下标

返回重点：

- `data.selected_image_url`
- `data.transparent_url`
- `data.local_path`
- `data.deleted_count`

### 5.7 初始化故事

- 方法：`POST`
- 路径：`/api/v1/characters/initialize-story`
- 说明：把角色与会话绑定到某个大场景/初遇事件，生成故事开局。

请求体：

```json
{
  "thread_id": "thread-001",
  "character_id": "1",
  "scene_id": "school",
  "opening_event_id": "event-001",
  "character_image_url": "/static/images/characters/hero.png"
}
```

字段说明：

- `thread_id`：必填，会话线程 ID
- `character_id`：必填，角色 ID
- `scene_id`：可选，默认 `school`
- `opening_event_id`：可选，不传则随机挑选
- `character_image_url`：可选，指定角色图片

## 6. 游戏管理接口

路由前缀：`/api/v1/game`

### 6.1 初始化游戏会话

- 方法：`POST`
- 路径：`/api/v1/game/init`

请求体：

```json
{
  "user_id": "user-001",
  "game_mode": "solo",
  "character_id": "1"
}
```

字段说明：

- `game_mode`：必填，代码注释显示支持 `solo | story`
- `user_id`：可选
- `character_id`：建议传入，接口内部要求其存在

返回重点：

- `data.thread_id`
- `data.user_id`
- `data.game_mode`

### 6.2 提交玩家输入

- 方法：`POST`
- 路径：`/api/v1/game/input`

请求体：

```json
{
  "thread_id": "thread-001",
  "user_input": "option:1",
  "user_id": "user-001",
  "character_id": "1"
}
```

字段说明：

- `thread_id`：必填
- `user_input`：必填
- `user_id`：可选
- `character_id`：可选，但用于会话恢复时很重要

特殊规则：

- 如果 `user_input` 满足 `option:<number>`，接口会把它解析为选项提交。
- 如果会话失效且带了 `character_id`，接口会尝试自动恢复会话。

返回重点：

- `data.character_dialogue`
- `data.player_options`
- `data.story_background`
- `data.event_title`
- `data.scene`
- `data.is_event_finished`
- `data.is_game_finished`
- 可能附带 `data.thread_id`、`data.session_restored`

### 6.3 检查是否满足结局条件

- 方法：`GET`
- 路径：`/api/v1/game/check-ending/{thread_id}`

路径参数：

- `thread_id`

返回重点：

- `data.has_ending`
- `data.ending`

### 6.4 强制触发结局

- 方法：`POST`
- 路径：`/api/v1/game/trigger-ending`

请求体：

```json
{
  "thread_id": "thread-001"
}
```

## 7. TTS 语音接口

路由前缀：`/api/v1/tts`

### 7.1 生成语音

- 方法：`POST`
- 路径：`/api/v1/tts/generate`

请求体：

```json
{
  "text": "你好，这是测试语音。",
  "character_id": 1,
  "emotion_params": {},
  "use_cache": true
}
```

返回重点：

- `data.audio_url`
- `data.audio_path`
- `data.duration`
- `data.cached`

### 7.2 创建 Voice Design 音色

- 方法：`POST`
- 路径：`/api/v1/tts/voice-design/create`

请求体：

```json
{
  "description": "温柔、坚定、年轻女性音色",
  "character_id": 1
}
```

返回重点：

- `data.voice_id`
- `data.message`

### 7.3 保存角色音色配置

- 方法：`POST`
- 路径：`/api/v1/tts/voice/config`

请求体：

```json
{
  "character_id": 1,
  "voice_type": "preset",
  "preset_voice_id": "female_001",
  "voice_design_description": null,
  "voice_params": {}
}
```

字段说明：

- `character_id`：必填
- `voice_type`：必填，常见值为 `preset`、`custom`、`voice_design`
- `preset_voice_id`：可选
- `voice_design_description`：可选
- `voice_params`：可选对象

### 7.4 获取角色音色配置

- 方法：`GET`
- 路径：`/api/v1/tts/voice/config/{character_id}`

### 7.5 获取 TTS 服务状态

- 方法：`GET`
- 路径：`/api/v1/tts/status`

返回重点：

- `data.enabled`
- `data.provider`
- `data.model`
- `data.voice_design_enabled`

### 7.6 获取预置音色列表

- 方法：`GET`
- 路径：`/api/v1/tts/presets`
- 查询参数：
  - `gender`：可选

### 7.7 试听预置音色

- 方法：`POST`
- 路径：`/api/v1/tts/preview`

请求体：

```json
{
  "preset_voice_id": "female_001",
  "text": "可选试听文本"
}
```

### 7.8 获取单个预置音色预览信息

- 方法：`GET`
- 路径：`/api/v1/tts/presets/{voice_id}/preview`

### 7.9 查询已创建的 Voice Design 音色列表

- 方法：`GET`
- 路径：`/api/v1/tts/voice-design/list`
- 查询参数：
  - `page_index`：默认 `0`
  - `page_size`：默认 `10`

## 8. 向量数据库管理接口

路由前缀：`/api/v1/admin/vector-db`

说明：这一组接口带有明显的管理性质，但当前仍直接挂载在主 API 中。

### 8.1 查询向量库数据

- 方法：`GET`
- 路径：`/api/v1/admin/vector-db/list`
- 查询参数：
  - `character_id`：可选

返回重点：

- `data.total`
- `data.character_stats`
- `data.items`

### 8.2 添加事件向量

- 方法：`POST`
- 路径：`/api/v1/admin/vector-db/add-event`

请求体：

```json
{
  "character_id": 1,
  "event_id": "event-001",
  "story_text": "事件故事文本",
  "dialogue_text": "事件对话文本",
  "metadata": {}
}
```

### 8.3 添加对话轮次向量

- 方法：`POST`
- 路径：`/api/v1/admin/vector-db/add-dialogue`

请求体：

```json
{
  "character_id": 1,
  "event_id": "event-001",
  "story_background": "背景文本",
  "dialogue_round": 1,
  "character_dialogue": "角色发言",
  "player_choice": "玩家选择",
  "metadata": {}
}
```

### 8.4 删除指定文档

- 方法：`POST`
- 路径：`/api/v1/admin/vector-db/delete`

请求体：

```json
{
  "doc_ids": [
    "doc-1",
    "doc-2"
  ]
}
```

### 8.5 删除指定角色的全部向量数据

- 方法：`DELETE`
- 路径：`/api/v1/admin/vector-db/delete-by-character/{character_id}`

### 8.6 重置向量数据库

- 方法：`POST`
- 路径：`/api/v1/admin/vector-db/reset`
- 说明：危险操作

### 8.7 获取向量数据库统计信息

- 方法：`GET`
- 路径：`/api/v1/admin/vector-db/stats`

## 9. 训练系统接口

路由前缀：`/api/v1/training`

说明：

- 这组接口既被主服务加载，也被训练专用服务加载。
- 训练接口的 `response_model` 相对最完整，OpenAPI 结构也最规范。

### 9.1 初始化训练会话

- 方法：`POST`
- 路径：`/api/v1/training/init`

请求体：

```json
{
  "user_id": "user-001",
  "character_id": 1,
  "training_mode": "guided"
}
```

字段说明：

- `user_id`：必填
- `character_id`：可选
- `training_mode`：可选，默认 `guided`

返回重点：

- `data.session_id`
- `data.status`
- `data.round_no`
- `data.k_state`
- `data.s_state`
- `data.next_scenario`
- `data.scenario_candidates`

### 9.2 获取下一训练场景

- 方法：`POST`
- 路径：`/api/v1/training/scenario/next`

请求体：

```json
{
  "session_id": "session-001"
}
```

返回重点：

- `data.session_id`
- `data.status`
- `data.round_no`
- `data.scenario`
- `data.scenario_candidates`
- `data.k_state`
- `data.s_state`
- `data.ending`

### 9.3 提交训练回合

- 方法：`POST`
- 路径：`/api/v1/training/round/submit`

请求体：

```json
{
  "session_id": "session-001",
  "scenario_id": "scenario-001",
  "user_input": "我的应对策略是……",
  "selected_option": "A"
}
```

返回重点：

- `data.session_id`
- `data.round_no`
- `data.evaluation`
- `data.k_state`
- `data.s_state`
- `data.is_completed`
- `data.ending`
- `data.decision_context`

### 9.4 获取训练进度

- 方法：`GET`
- 路径：`/api/v1/training/progress/{session_id}`

返回重点：

- `data.session_id`
- `data.status`
- `data.round_no`
- `data.total_rounds`
- `data.k_state`
- `data.s_state`

### 9.5 获取训练报告

- 方法：`GET`
- 路径：`/api/v1/training/report/{session_id}`

返回重点：

- `data.session_id`
- `data.status`
- `data.rounds`
- `data.k_state_final`
- `data.s_state_final`
- `data.improvement`
- `data.summary`
- `data.ability_radar`
- `data.state_radar`
- `data.growth_curve`
- `data.history`

### 9.6 获取训练诊断数据

- 方法：`GET`
- 路径：`/api/v1/training/diagnostics/{session_id}`

返回重点：

- `data.session_id`
- `data.status`
- `data.round_no`
- `data.summary`
- `data.recommendation_logs`
- `data.audit_events`
- `data.kt_observations`

## 10. 接口设计观察

从当前代码结构看，接口设计已经具备比较清晰的 FastAPI 分层特征：

- 使用 `APIRouter` 按领域拆分模块
- 使用统一前缀 `/api/v1/...`
- 使用 Pydantic Schema 描述训练模块和部分业务模块
- 自动提供 OpenAPI 文档
- 主服务与训练专用服务边界基本清晰

但也存在几个值得关注的点：

### 10.1 优点

1. 路由分组比较清楚，角色、游戏、训练、TTS、管理接口都有独立 router。
2. 版本号前缀 `v1` 已经建立，后续演进空间较好。
3. 响应壳基本统一，前端接入成本低。
4. 训练模块的模型定义比较完整，接口契约最好。

### 10.2 风险与改进建议

1. 一部分接口的 `response_model` 仍然是 `dict` 或未声明，导致 OpenAPI 精度不够。
2. `initialize-story` 当前挂在 `characters` 路由下，从语义上更像 `game` 或 `story` 域。
3. `vector-db` 管理接口直接暴露在主应用下，且代码中未看到鉴权保护，生产环境风险较高。
4. 训练接口被主服务和训练专用服务同时暴露，虽然方便部署，但要注意文档、鉴权、限流和版本同步。
5. 根接口与健康检查未统一走响应壳，这本身不算错误，但风格上与业务接口不同。

## 11. 建议的后续优化方向

如果要继续完善这套接口，建议按优先级做：

1. 给 `characters`、`game`、`tts`、`vector-db` 全量补齐明确的 `response_model`。
2. 给管理类接口增加鉴权与环境隔离。
3. 把 `initialize-story` 从角色域迁移到游戏域，或者新增 `story` 域。
4. 为主服务版和训练专用版文档分别输出一份 Swagger 使用说明。
5. 为关键接口增加请求示例与错误码字典。

