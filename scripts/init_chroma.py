"""
初始化 Chroma 数据库（本地部署）
"""
import chromadb
import os
import sys
from pathlib import Path

# 设置 UTF-8 编码（Windows 控制台支持）
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="replace")


def init_chroma_db(db_path: str = "./chroma_db"):
    """
    初始化 Chroma 数据库（本地持久化部署）
    
    Args:
        db_path: 数据库存储路径
    """
    # 创建目录（如果不存在）
    Path(db_path).mkdir(parents=True, exist_ok=True)
    
    # 创建客户端（本地持久化模式）
    client = chromadb.PersistentClient(path=db_path)
    
    # 创建 Collection
    collection = client.get_or_create_collection(
        name="story_memories",
        metadata={
            "hnsw:space": "cosine",  # 使用余弦相似度
            "description": "剧情记忆向量存储"
        }
    )
    
    print(f"✅ Chroma 数据库初始化成功！")
    print(f"   部署方式: 本地部署（PersistentClient）")
    print(f"   路径: {os.path.abspath(db_path)}")
    print(f"   Collection: {collection.name}")
    print(f"   当前记录数: {collection.count()}")
    print(f"   配置: 余弦相似度（cosine）")


if __name__ == "__main__":
    import sys
    
    # 从命令行参数获取路径，或使用默认路径
    db_path = sys.argv[1] if len(sys.argv) > 1 else "./chroma_db"
    
    init_chroma_db(db_path)
