# No End Story - PostgreSQL 使用方案分析

## 一、PostgreSQL 在项目中的角色

### 1.1 核心职责

PostgreSQL 在 No End Story 项目中承担**结构化数据存储**的角色：

1. **用户数据**：用户信息、账户数据
2. **会话数据**：Thread 管理、Session 信息
3. **剧情状态**：当前场景、角色关系、情绪值、故事标志
4. **对话历史**：用户输入、AI 响应的完整记录
5. **图像缓存**：生成图像的元数据和 URL
6. **配置数据**：游戏配置、角色配置等

### 1.2 数据特点

- **结构化数据**：关系型数据，适合 SQL 查询
- **事务需求**：需要 ACID 保证
- **查询模式**：主要是精确查询和范围查询
- **数据规模**：中等规模（百万级记录）

---

## 二、PostgreSQL + pgvector 作为向量数据库？

### 2.1 方案分析：PostgreSQL + pgvector vs Chroma

#### 方案对比

| 维度 | PostgreSQL + pgvector | Chroma | 推荐 |
|------|----------------------|--------|------|
| **统一架构** | ⭐⭐⭐⭐⭐ 所有数据在同一数据库 | ⭐⭐⭐ 需要两个数据库 | PostgreSQL 更统一 |
| **事务支持** | ⭐⭐⭐⭐⭐ ACID 保证 | ⭐⭐ 无事务 | PostgreSQL 更可靠 |
| **开发速度** | ⭐⭐⭐ 需要 SQL 和扩展 | ⭐⭐⭐⭐⭐ API 简单 | Chroma 更快 |
| **性能** | ⭐⭐⭐ 中等规模性能良好 | ⭐⭐⭐⭐ 性能更优 | Chroma 稍好 |
| **维护成本** | ⭐⭐⭐⭐ 只需一个数据库 | ⭐⭐⭐ 需要两个系统 | PostgreSQL 更简单 |
| **学习曲线** | ⭐⭐⭐ SQL + pgvector | ⭐⭐⭐⭐⭐ API 简洁 | Chroma 更简单 |
| **适合规模** | ⭐⭐⭐⭐ 中小规模 | ⭐⭐⭐⭐ 中小规模 | 都适合 |

---

### 2.2 PostgreSQL + pgvector 方案

#### ✅ 优势

1. **架构统一**
   - 所有数据（结构化 + 向量）在同一数据库
   - 简化部署和运维
   - **只需维护一个数据库系统**

2. **事务支持**
   - 向量数据和结构化数据可以在同一事务中
   - 数据一致性保证更强
   - **适合需要强一致性的场景**

3. **查询灵活**
   - 可以使用 SQL JOIN 关联向量数据和结构化数据
   - 复杂的过滤和聚合查询
   - **适合复杂的查询需求**

4. **成熟稳定**
   - PostgreSQL 久经考验
   - pgvector 扩展成熟
   - **生产环境稳定**

5. **成本优势**
   - 无需额外的向量数据库服务
   - 统一维护，降低运维成本
   - **适合中小团队**

#### ❌ 劣势

1. **性能限制**
   - 大规模数据（千万级）性能不如专用向量数据库
   - 检索速度相对较慢（但中小规模足够）

2. **开发复杂度**
   - 需要学习 pgvector 扩展
   - SQL 查询相对复杂
   - **比 Chroma API 复杂一些**

3. **功能相对简单**
   - 相比 Chroma，API 不够简洁
   - 需要自己管理索引和优化

---

### 2.3 Chroma 方案（当前推荐）

#### ✅ 优势

1. **开发速度快**
   - API 简洁直观
   - 开箱即用
   - **适合快速 MVP**

2. **性能优秀**
   - 专门优化的向量数据库
   - 性能比 pgvector 稍好

3. **学习曲线平缓**
   - 不需要学习 SQL 扩展
   - Python API 更直观

#### ❌ 劣势

1. **架构复杂**
   - 需要维护两个数据库系统
   - 部署和运维成本稍高

2. **无事务支持**
   - 向量数据和结构化数据无法在同一事务中
   - 数据一致性需要自己保证

---

## 三、推荐方案分析

### 3.1 对于 No End Story 项目

#### 选项 A：PostgreSQL + pgvector（推荐 ✅）

**推荐理由**：

1. ✅ **架构统一**
   - 项目已经有 PostgreSQL（结构化数据）
   - 使用 pgvector 可以统一架构
   - **只需维护一个数据库**

2. ✅ **适合团队**
   - 2 人后端团队
   - 统一的技术栈（SQL）
   - 降低运维复杂度

3. ✅ **数据一致性**
   - 向量数据和结构化数据可以在同一事务中
   - 适合需要强一致性的场景

4. ✅ **性能足够**
   - 项目规模：10万-100万向量
   - pgvector 性能完全足够
   - 中小规模性能差异不明显

5. ✅ **成本优势**
   - 无需额外的向量数据库
   - 统一维护，降低成本

#### 选项 B：PostgreSQL（结构化） + Chroma（向量）

**适用场景**：
- 需要最快的开发速度
- 不关心架构统一
- 团队对 SQL 不熟悉

---

## 四、PostgreSQL + pgvector 实施方案

### 4.1 安装和配置

#### 安装 pgvector 扩展

```bash
# 在 PostgreSQL 中安装 pgvector 扩展
# 方法 1：使用包管理器（推荐）
# Ubuntu/Debian
sudo apt-get install postgresql-14-pgvector  # 根据 PostgreSQL 版本调整

# macOS
brew install pgvector

# 方法 2：从源码编译
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install
```

#### 在数据库中启用扩展

```sql
-- 连接到数据库
psql -d noendstory

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4.2 数据库设计

#### 结构化数据表（原有）

```sql
-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 线程表
CREATE TABLE threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    openai_thread_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 剧情状态表
CREATE TABLE story_states (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE UNIQUE,
    current_scene VARCHAR(255),
    story_flags JSONB DEFAULT '{}',
    character_relations JSONB DEFAULT '{}',
    emotion_values JSONB DEFAULT '{}',
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 对话历史表
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- user / assistant
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 图像缓存表
CREATE TABLE image_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prompt_hash VARCHAR(64) UNIQUE NOT NULL,
    image_url TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 向量存储表（新增）

```sql
-- 剧情记忆向量表
CREATE TABLE story_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id UUID REFERENCES threads(id) ON DELETE CASCADE NOT NULL,
    content TEXT NOT NULL,  -- 原始文本
    embedding vector(1536) NOT NULL,  -- OpenAI embedding 维度
    scene VARCHAR(255),
    importance FLOAT DEFAULT 0.5,  -- 重要性评分 0-1
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引（HNSW 索引，性能更好）
CREATE INDEX ON story_memories 
USING hnsw (embedding vector_cosine_ops);

-- 创建 thread_id 索引（用于过滤）
CREATE INDEX idx_story_memories_thread_id ON story_memories(thread_id);

-- 创建复合索引（用于常见查询）
CREATE INDEX idx_story_memories_thread_scene 
ON story_memories(thread_id, scene);
```

### 4.3 Python 集成

#### 安装依赖

```bash
pip install psycopg2-binary pgvector sqlalchemy
# 或使用 async 版本
pip install asyncpg pgvector sqlalchemy[asyncio]
```

#### 代码实现

```python
# app/services/memory_service.py
from sqlalchemy import create_engine, Column, String, Float, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector
from openai import OpenAI
import uuid

Base = declarative_base()

class StoryMemory(Base):
    __tablename__ = "story_memories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("threads.id"), nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(Vector(1536), nullable=False)  # OpenAI embedding 维度
    scene = Column(String)
    importance = Column(Float, default=0.5)
    metadata = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)

class MemoryService:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        self.openai_client = OpenAI()
    
    def store_memory(
        self, 
        thread_id: str, 
        content: str, 
        scene: str = None,
        importance: float = 0.5,
        metadata: dict = None
    ):
        """存储记忆向量"""
        # 生成向量
        embedding_response = self.openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=content
        )
        embedding = embedding_response.data[0].embedding
        
        # 存储到数据库
        session = self.Session()
        try:
            memory = StoryMemory(
                thread_id=uuid.UUID(thread_id),
                content=content,
                embedding=embedding,  # pgvector 会自动处理
                scene=scene,
                importance=importance,
                metadata=metadata or {}
            )
            session.add(memory)
            session.commit()
        finally:
            session.close()
    
    def get_relevant_context(
        self, 
        thread_id: str, 
        query: str, 
        top_k: int = 5,
        scene: str = None
    ):
        """检索相关上下文"""
        # 生成查询向量
        query_embedding_response = self.openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=query
        )
        query_embedding = query_embedding_response.data[0].embedding
        
        # 构建 SQL 查询（使用余弦相似度）
        session = self.Session()
        try:
            # 使用 SQL 直接查询（更高效）
            query_sql = """
                SELECT content, metadata, importance,
                       1 - (embedding <=> %s::vector) as similarity
                FROM story_memories
                WHERE thread_id = %s
            """
            
            params = [str(query_embedding), thread_id]
            
            if scene:
                query_sql += " AND scene = %s"
                params.append(scene)
            
            query_sql += """
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            params.append(str(query_embedding))
            params.append(top_k)
            
            result = session.execute(query_sql, params)
            
            # 构建上下文
            contexts = []
            for row in result:
                contexts.append(row.content)
            
            return "\n".join(contexts)
        finally:
            session.close()
    
    def get_relevant_context_with_sqlalchemy(
        self, 
        thread_id: str, 
        query_embedding: list,
        top_k: int = 5
    ):
        """使用 SQLAlchemy ORM 查询（示例）"""
        session = self.Session()
        try:
            # 注意：SQLAlchemy ORM 对向量查询支持有限
            # 建议使用原始 SQL 查询（如上方法）
            memories = session.query(StoryMemory)\
                .filter(StoryMemory.thread_id == uuid.UUID(thread_id))\
                .order_by(StoryMemory.embedding.cosine_distance(query_embedding))\
                .limit(top_k)\
                .all()
            
            return [m.content for m in memories]
        finally:
            session.close()
```

#### 使用原始 SQL（推荐，性能更好）

```python
# app/services/memory_service.py (优化版)
from sqlalchemy import create_engine, text
from openai import OpenAI
import json

class MemoryService:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.openai_client = OpenAI()
    
    def get_relevant_context(self, thread_id: str, query: str, top_k: int = 5):
        """检索相关上下文（使用原始 SQL，性能更好）"""
        # 生成查询向量
        query_embedding = self.openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=query
        ).data[0].embedding
        
        # 使用原始 SQL 查询
        with self.engine.connect() as conn:
            # <=> 是 pgvector 的余弦距离操作符
            # ORDER BY embedding <=> query_vector 会使用 HNSW 索引
            result = conn.execute(
                text("""
                    SELECT content, metadata,
                           1 - (embedding <=> :query_vector::vector) as similarity
                    FROM story_memories
                    WHERE thread_id = :thread_id
                    ORDER BY embedding <=> :query_vector::vector
                    LIMIT :top_k
                """),
                {
                    "query_vector": json.dumps(query_embedding),
                    "thread_id": thread_id,
                    "top_k": top_k
                }
            )
            
            contexts = [row.content for row in result]
            return "\n".join(contexts)
```

---

## 五、方案对比总结

### 5.1 PostgreSQL + pgvector vs Chroma

| 维度 | PostgreSQL + pgvector | Chroma | 推荐 |
|------|----------------------|--------|------|
| **架构统一** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | **pgvector** |
| **开发速度** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Chroma |
| **性能** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 相当 |
| **事务支持** | ⭐⭐⭐⭐⭐ | ⭐⭐ | **pgvector** |
| **学习曲线** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Chroma |
| **维护成本** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | **pgvector** |
| **适合团队** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **pgvector** |

### 5.2 最终推荐

#### 🎯 推荐：PostgreSQL + pgvector ✅

**理由**：

1. ✅ **架构统一**
   - 所有数据在同一数据库
   - 简化部署和运维
   - 适合 2 人小团队

2. ✅ **事务支持**
   - 向量数据和结构化数据可以在同一事务中
   - 数据一致性更强

3. ✅ **性能足够**
   - 对于项目规模（10万-100万向量），性能完全足够
   - pgvector 使用 HNSW 索引，性能优秀

4. ✅ **成本优势**
   - 无需额外的向量数据库
   - 统一维护，降低运维成本

5. ✅ **成熟稳定**
   - PostgreSQL + pgvector 组合成熟
   - 生产环境广泛使用

---

## 六、实施建议

### 6.1 如果选择 PostgreSQL + pgvector

**优势**：
- ✅ 架构统一，只需一个数据库
- ✅ 事务支持，数据一致性更强
- ✅ 降低运维复杂度
- ✅ 适合小团队

**注意事项**：
- ⚠️ 需要学习 pgvector 扩展
- ⚠️ SQL 查询相对复杂一些
- ⚠️ 性能在大规模数据时可能不如专用向量数据库（但项目规模足够）

### 6.2 如果选择 Chroma

**优势**：
- ✅ 开发速度快
- ✅ API 简洁
- ✅ 学习曲线平缓

**注意事项**：
- ⚠️ 需要维护两个数据库系统
- ⚠️ 无事务支持
- ⚠️ 架构稍复杂

---

## 七、代码示例对比

### 7.1 PostgreSQL + pgvector

```python
# 存储
memory = StoryMemory(
    thread_id=thread_id,
    content=content,
    embedding=embedding,  # 直接存储向量
    scene=scene
)
session.add(memory)
session.commit()

# 查询（使用原始 SQL）
result = conn.execute(
    text("""
        SELECT content
        FROM story_memories
        WHERE thread_id = :thread_id
        ORDER BY embedding <=> :query_vector::vector
        LIMIT :top_k
    """),
    {"thread_id": thread_id, "query_vector": json.dumps(query_embedding), "top_k": 5}
)
```

### 7.2 Chroma

```python
# 存储
collection.add(
    embeddings=[embedding],
    documents=[content],
    metadatas=[{"thread_id": thread_id, "scene": scene}],
    ids=[id]
)

# 查询
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"thread_id": thread_id}
)
```

---

## 八、最终建议

### 对于 No End Story 项目

**推荐：PostgreSQL + pgvector ✅**

**理由**：
1. 项目已经有 PostgreSQL（结构化数据）
2. 统一架构，降低运维复杂度
3. 适合 2 人小团队
4. 性能足够，功能完整
5. 事务支持，数据一致性更强

**实施步骤**：
1. 安装 pgvector 扩展
2. 创建向量存储表
3. 实现 MemoryService（使用原始 SQL）
4. 集成到剧情生成流程

---

*本文档基于项目实际需求分析，建议根据团队技能和时间安排选择*
