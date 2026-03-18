# No End Story - Chroma 数据库使用指南

## 一、Chroma 简介

Chroma 是一个开源的向量数据库，专门用于存储和检索嵌入向量。它内部使用 FAISS 作为底层搜索引擎，提供了简洁的 Python API。

---

## 二、安装 Chroma

### 2.1 安装依赖

```bash
# 安装 ChromaDB
pip install chromadb

# 如果需要使用 SQLite 作为后端（默认）
# 无需额外安装，Chroma 默认使用 SQLite

# 如果需要 HTTP 客户端（可选）
pip install chromadb[client]
```

### 2.2 验证安装

```python
import chromadb
print(chromadb.__version__)
# 应该输出版本号，如 0.4.0
```

---

## 三、创建数据库

### 3.1 基本方式：本地持久化（推荐 MVP）

#### 方式一：PersistentClient（推荐）

```python
import chromadb
from chromadb.config import Settings

# 创建持久化客户端（数据存储在本地目录）
client = chromadb.PersistentClient(path="./chroma_db")

# 这将创建 ./chroma_db 目录，所有数据存储在其中
# 数据会持久化到磁盘，重启后不会丢失
```

**优点**：
- ✅ 数据持久化
- ✅ 无需额外服务
- ✅ 适合单机部署
- ✅ 适合 MVP 阶段

**缺点**：
- ⚠️ 不支持多进程并发写入（读取可以并发）
- ⚠️ 不适合分布式部署

#### 方式二：HttpClient（服务器模式）

```python
import chromadb

# 连接到远程 Chroma 服务器
client = chromadb.HttpClient(
    host="localhost",
    port=8000
)
```

**需要先启动服务器**：
```bash
chroma run --path ./chroma_db --port 8000
```

**优点**：
- ✅ 支持多进程/多服务器访问
- ✅ 适合分布式部署

**缺点**：
- ⚠️ 需要额外的服务器进程
- ⚠️ 增加运维复杂度
- ⚠️ 对于 MVP，过度设计

---

## 四、创建 Collection（表）

### 4.1 基本创建

```python
import chromadb

# 创建客户端
client = chromadb.PersistentClient(path="./chroma_db")

# 创建或获取 Collection（如果已存在则获取，不存在则创建）
collection = client.get_or_create_collection(
    name="story_memories",  # Collection 名称
    metadata={"hnsw:space": "cosine"}  # 使用余弦相似度（推荐）
)
```

### 4.2 Collection 配置选项

```python
collection = client.get_or_create_collection(
    name="story_memories",
    metadata={
        "hnsw:space": "cosine",  # 距离度量：cosine（推荐）/ l2 / ip
        "description": "存储剧情记忆向量"
    }
)
```

**距离度量说明**：
- `cosine`：余弦相似度（推荐，适合文本向量）
- `l2`：欧氏距离
- `ip`：内积

---

## 五、项目集成示例

### 5.1 创建 MemoryService

```python
# app/services/memory_service.py
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from typing import List, Dict, Optional
import os

class MemoryService:
    def __init__(self, chroma_db_path: str = "./chroma_db"):
        """
        初始化 Chroma 数据库服务
        
        Args:
            chroma_db_path: Chroma 数据库存储路径
        """
        # 创建 Chroma 客户端（持久化模式）
        self.client = chromadb.PersistentClient(path=chroma_db_path)
        
        # 创建或获取 Collection
        self.collection = self.client.get_or_create_collection(
            name="story_memories",
            metadata={
                "hnsw:space": "cosine",  # 使用余弦相似度
                "description": "剧情记忆向量存储"
            }
        )
        
        # OpenAI 客户端（用于生成向量）
        self.openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def store_memory(
        self,
        thread_id: str,
        content: str,
        scene: Optional[str] = None,
        importance: float = 0.5,
        metadata: Optional[Dict] = None
    ):
        """
        存储剧情记忆向量
        
        Args:
            thread_id: 线程 ID（玩家会话 ID）
            content: 记忆内容（原始文本）
            scene: 场景名称（可选）
            importance: 重要性评分 0-1（可选）
            metadata: 额外元数据（可选）
        """
        # 使用 OpenAI Embeddings API 生成向量
        embedding_response = self.openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=content
        )
        embedding = embedding_response.data[0].embedding
        
        # 构建元数据
        memory_metadata = {
            "thread_id": thread_id,
            "importance": str(importance)
        }
        
        if scene:
            memory_metadata["scene"] = scene
        
        if metadata:
            memory_metadata.update(metadata)
        
        # 生成唯一 ID
        import uuid
        memory_id = f"{thread_id}_{uuid.uuid4().hex[:8]}"
        
        # 存储到 Chroma
        self.collection.add(
            embeddings=[embedding],  # 向量列表（单个向量也要放在列表中）
            documents=[content],  # 原始文本
            metadatas=[memory_metadata],  # 元数据
            ids=[memory_id]  # 唯一 ID
        )
        
        return memory_id
    
    def get_relevant_context(
        self,
        thread_id: str,
        query: str,
        top_k: int = 5,
        scene: Optional[str] = None
    ) -> str:
        """
        检索相关上下文
        
        Args:
            thread_id: 线程 ID
            query: 查询文本
            top_k: 返回前 k 个最相关的结果
            scene: 场景过滤（可选）
        
        Returns:
            相关上下文的文本（用换行符连接）
        """
        # 生成查询向量
        query_embedding_response = self.openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=query
        )
        query_embedding = query_embedding_response.data[0].embedding
        
        # 构建查询过滤器（元数据过滤）
        where_filter = {"thread_id": thread_id}
        if scene:
            where_filter["scene"] = scene
        
        # 查询相似向量
        results = self.collection.query(
            query_embeddings=[query_embedding],  # 查询向量（列表形式）
            n_results=top_k,  # 返回数量
            where=where_filter,  # 元数据过滤
            include=["documents", "metadatas", "distances"]  # 返回的字段
        )
        
        # 构建上下文（从 documents 中提取）
        if results["documents"] and len(results["documents"][0]) > 0:
            contexts = results["documents"][0]
            return "\n".join(contexts)
        else:
            return ""
    
    def delete_memory(self, memory_id: str):
        """删除指定记忆"""
        self.collection.delete(ids=[memory_id])
    
    def delete_thread_memories(self, thread_id: str):
        """删除指定线程的所有记忆"""
        # 获取所有该线程的记忆
        results = self.collection.get(
            where={"thread_id": thread_id}
        )
        
        if results["ids"]:
            self.collection.delete(ids=results["ids"])
    
    def get_collection_info(self):
        """获取 Collection 信息"""
        return {
            "name": self.collection.name,
            "count": self.collection.count(),
            "metadata": self.collection.metadata
        }
```

### 5.2 配置集成

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Chroma 配置
    chroma_db_path: str = "./chroma_db"  # 数据库存储路径
    
    # OpenAI 配置
    openai_api_key: str
    openai_embedding_model: str = "text-embedding-3-large"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 5.3 在项目中使用

```python
# app/core/story_engine.py
from app.services.memory_service import MemoryService
from app.core.config import settings

class StoryEngine:
    def __init__(self):
        # 初始化记忆服务
        self.memory_service = MemoryService(
            chroma_db_path=settings.chroma_db_path
        )
    
    async def process_input(self, thread_id: str, user_input: str):
        # 1. 检索相关上下文
        context = self.memory_service.get_relevant_context(
            thread_id=thread_id,
            query=user_input,
            top_k=5
        )
        
        # 2. 生成剧情（使用 context）
        story_content = await self.generate_story(context, user_input)
        
        # 3. 存储新的记忆
        self.memory_service.store_memory(
            thread_id=thread_id,
            content=story_content,
            scene=current_scene,
            importance=0.7
        )
        
        return story_content
```

---

## 六、数据库初始化脚本

### 6.1 初始化脚本

```python
# scripts/init_chroma.py
"""
初始化 Chroma 数据库
"""
import chromadb
from chromadb.config import Settings
import os
from pathlib import Path

def init_chroma_db(db_path: str = "./chroma_db"):
    """
    初始化 Chroma 数据库
    
    Args:
        db_path: 数据库存储路径
    """
    # 创建目录（如果不存在）
    Path(db_path).mkdir(parents=True, exist_ok=True)
    
    # 创建客户端
    client = chromadb.PersistentClient(path=db_path)
    
    # 创建 Collection
    collection = client.get_or_create_collection(
        name="story_memories",
        metadata={
            "hnsw:space": "cosine",
            "description": "剧情记忆向量存储"
        }
    )
    
    print(f"✅ Chroma 数据库初始化成功！")
    print(f"   路径: {os.path.abspath(db_path)}")
    print(f"   Collection: {collection.name}")
    print(f"   当前记录数: {collection.count()}")

if __name__ == "__main__":
    import sys
    
    # 从命令行参数获取路径，或使用默认路径
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./chroma_db"
    
    init_chroma_db(db_path)
```

### 6.2 运行初始化

```bash
# 运行初始化脚本
python scripts/init_chroma.py

# 或指定路径
python scripts/init_chroma.py /path/to/chroma_db
```

---

## 七、环境配置

### 7.1 .env 文件配置

```env
# Chroma 数据库配置
CHROMA_DB_PATH=./chroma_db

# OpenAI 配置（用于生成向量）
OPENAI_API_KEY=sk-...
OPENAI_EMBEDDING_MODEL=text-embedding-3-large
```

### 7.2 requirements.txt

```txt
# Chroma 数据库
chromadb==0.4.22

# OpenAI（用于生成向量）
openai==1.12.0

# 其他依赖...
```

---

## 八、使用示例

### 8.1 基本操作示例

```python
from app.services.memory_service import MemoryService

# 初始化服务
memory_service = MemoryService(chroma_db_path="./chroma_db")

# 1. 存储记忆
memory_id = memory_service.store_memory(
    thread_id="thread_123",
    content="Alice 在海边遇到了 Bob，他们成为了朋友。",
    scene="beach",
    importance=0.8
)
print(f"存储记忆 ID: {memory_id}")

# 2. 检索相关上下文
context = memory_service.get_relevant_context(
    thread_id="thread_123",
    query="Alice 和 Bob 的关系如何？",
    top_k=5
)
print(f"相关上下文:\n{context}")

# 3. 获取 Collection 信息
info = memory_service.get_collection_info()
print(f"Collection 信息: {info}")

# 4. 删除记忆
memory_service.delete_memory(memory_id)

# 5. 删除线程的所有记忆
memory_service.delete_thread_memories("thread_123")
```

### 8.2 批量操作示例

```python
# 批量存储记忆
def store_batch_memories(memory_service: MemoryService, memories: List[Dict]):
    """批量存储记忆"""
    embeddings = []
    documents = []
    metadatas = []
    ids = []
    
    for memory in memories:
        # 生成向量
        embedding = memory_service.openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=memory["content"]
        ).data[0].embedding
        
        embeddings.append(embedding)
        documents.append(memory["content"])
        metadatas.append(memory["metadata"])
        ids.append(memory["id"])
    
    # 批量添加
    memory_service.collection.add(
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )

# 使用示例
memories = [
    {
        "id": "memory_1",
        "content": "Alice 在海边遇到了 Bob...",
        "metadata": {"thread_id": "thread_123", "scene": "beach"}
    },
    {
        "id": "memory_2",
        "content": "Bob 告诉 Alice 一个秘密...",
        "metadata": {"thread_id": "thread_123", "scene": "beach"}
    }
]

store_batch_memories(memory_service, memories)
```

---

## 九、最佳实践

### 9.1 数据库路径管理

```python
# 推荐：使用配置文件管理路径
# config.py
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")

# 或者使用绝对路径（生产环境推荐）
CHROMA_DB_PATH = "/var/lib/no-end-story/chroma_db"
```

### 9.2 错误处理

```python
from chromadb.errors import ChromaError

try:
    collection = client.get_or_create_collection(name="story_memories")
except ChromaError as e:
    print(f"Chroma 错误: {e}")
    # 处理错误
```

### 9.3 性能优化

**1. 批量操作**
```python
# ✅ 推荐：批量添加
collection.add(
    embeddings=[emb1, emb2, emb3],
    documents=[doc1, doc2, doc3],
    metadatas=[meta1, meta2, meta3],
    ids=[id1, id2, id3]
)

# ❌ 不推荐：逐个添加
for i in range(3):
    collection.add(embeddings=[emb[i]], ...)  # 效率低
```

**2. 使用元数据过滤**
```python
# ✅ 推荐：使用元数据过滤，减少搜索范围
results = collection.query(
    query_embeddings=[query_embedding],
    where={"thread_id": thread_id},  # 只搜索该线程的数据
    n_results=5
)
```

**3. 合理设置 top_k**
```python
# ✅ 推荐：根据需求设置合理的 top_k
# 一般 5-10 个结果足够
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5  # 不要设置太大
)
```

### 9.4 数据备份

```python
# Chroma 数据存储在本地目录
# 备份就是备份整个目录

import shutil
from datetime import datetime

def backup_chroma_db(db_path: str = "./chroma_db"):
    """备份 Chroma 数据库"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}_backup_{timestamp}"
    
    shutil.copytree(db_path, backup_path)
    print(f"✅ 备份完成: {backup_path}")

# 使用
backup_chroma_db("./chroma_db")
```

---

## 十、常见问题

### 10.1 数据库位置

**Q: 数据存储在哪里？**

A: 使用 `PersistentClient` 时，数据存储在指定的路径中（如 `./chroma_db`）。目录结构：

```
chroma_db/
├── chroma.sqlite3          # SQLite 数据库（元数据）
└── ...                     # 其他数据文件
```

### 10.2 并发访问

**Q: 支持并发访问吗？**

A: 
- **PersistentClient**：支持并发读取，但不支持并发写入
- **HttpClient**：支持并发读写（需要运行 Chroma 服务器）

### 10.3 数据迁移

**Q: 如何迁移数据？**

A: 直接复制整个数据库目录即可：

```bash
# 复制数据库目录
cp -r ./chroma_db /backup/location/
```

### 10.4 性能优化

**Q: 如何优化性能？**

A:
1. 使用批量操作
2. 使用元数据过滤减少搜索范围
3. 合理设置 top_k
4. 定期清理不必要的数据

---

## 十一、完整集成示例

### 11.1 项目结构

```
backend/
├── app/
│   ├── services/
│   │   └── memory_service.py    # Chroma 服务
│   └── core/
│       └── config.py            # 配置
├── scripts/
│   └── init_chroma.py           # 初始化脚本
└── chroma_db/                   # 数据库目录（自动创建）
    └── ...
```

### 11.2 使用流程

```python
# 1. 初始化（项目启动时）
from app.services.memory_service import MemoryService
from app.core.config import settings

memory_service = MemoryService(
    chroma_db_path=settings.chroma_db_path
)

# 2. 在剧情生成中使用
def generate_story(thread_id: str, user_input: str):
    # 检索相关上下文
    context = memory_service.get_relevant_context(
        thread_id=thread_id,
        query=user_input,
        top_k=5
    )
    
    # 生成剧情（使用 context）
    story = generate_with_context(context, user_input)
    
    # 存储新记忆
    memory_service.store_memory(
        thread_id=thread_id,
        content=story,
        scene=current_scene
    )
    
    return story
```

---

## 十二、总结

### 12.1 快速开始

```bash
# 1. 安装
pip install chromadb

# 2. 创建数据库（代码中自动创建）
python scripts/init_chroma.py

# 3. 使用
from app.services.memory_service import MemoryService
memory_service = MemoryService()
memory_service.store_memory(...)
```

### 12.2 关键点

1. ✅ **使用 PersistentClient**（MVP 推荐）
2. ✅ **数据自动持久化**到指定目录
3. ✅ **Collection 自动创建**（get_or_create_collection）
4. ✅ **使用元数据过滤**提高性能
5. ✅ **批量操作**提高效率

---

*本文档提供了 Chroma 数据库的完整使用指南，可以根据项目需求调整*
