# No End Story - 基于 OpenAI 的无限剧情流游戏

## 项目简介

No End Story 是一款基于 **OpenAI 原生框架**开发的无限剧情流游戏，通过 AI 实时生成剧情和图像，为玩家提供独一无二的故事体验。

### 核心特性

- 🎭 **动态剧情生成**：使用 OpenAI GPT-4o 实时生成个性化剧情
- 🎨 **AI 图像生成**：集成 DALL·E 3 生成场景和角色图像
- 🧠 **智能 Agent 系统**：基于 OpenAI Assistants API 构建剧情 Director 和 Writer
- 💾 **记忆系统**：通过向量数据库和 RAG 技术保持剧情一致性
- 🚀 **高性能架构**：基于 FastAPI 的异步架构，支持高并发

---

## 技术栈

### 后端
- **框架**：FastAPI
- **AI 模型**：OpenAI GPT-4o, DALL·E 3
- **AI 框架**：OpenAI Assistants API, Function Calling
- **数据库**：PostgreSQL
- **缓存**：Redis
- **向量数据库**：Pinecone / Weaviate
- **语言**：Python 3.10+

### 前端（可选）
- React / Next.js
- 或 Unity（游戏引擎）

---

## 快速开始

### 前置要求

- Python 3.10+
- PostgreSQL
- Redis
- OpenAI API Key

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd no-end-story
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **安装依赖**
```bash
pip install -r backend/requirements.txt
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

5. **初始化数据库**
```bash
cd backend
alembic upgrade head
```

6. **初始化 OpenAI Assistants**
```bash
python scripts/init_assistants.py
```

7. **启动服务**
```bash
uvicorn app.main:app --reload
```

服务将在 `http://localhost:8000` 启动

---

## 项目结构

```
no-end-story/
├── backend/          # 后端服务
├── frontend/         # 前端（可选）
├── docs/            # 文档
└── scripts/         # 工具脚本
```

详细结构请参考 [项目结构设计文档](docs/项目结构设计.md)

---

## 文档

- [基于 OpenAI 的技术架构设计](docs/基于OpenAI的技术架构设计.md)
- [API 接口详细设计](docs/API接口详细设计.md)
- [项目结构设计](docs/项目结构设计.md)

---

## API 使用示例

### 初始化游戏

```bash
curl -X POST http://localhost:8000/api/v1/game/init \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_123",
    "game_mode": "solo"
  }'
```

### 玩家输入

```bash
curl -X POST http://localhost:8000/api/v1/game/input \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread_456",
    "input": {
      "type": "text",
      "content": "我想去海边看看"
    }
  }'
```

---

## 开发路线图

### Phase 1: 基础框架（已完成）
- ✅ 项目架构设计
- ✅ API 设计
- ✅ 数据库设计

### Phase 2: 核心功能开发（进行中）
- [ ] OpenAI 集成
- [ ] Agent 实现
- [ ] 基础 API 实现

### Phase 3: 功能完善
- [ ] 图像生成集成
- [ ] 记忆系统实现
- [ ] 前端开发

### Phase 4: 优化与测试
- [ ] 性能优化
- [ ] 一致性优化
- [ ] 测试与部署

---

## 贡献

欢迎提交 Issue 和 Pull Request！

---

## 许可证

[MIT License](LICENSE)

---

## 联系方式

如有问题，请提交 Issue 或联系项目维护者。
