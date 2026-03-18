"""检查向量数据库存储路径"""
import sys
import os
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _backend_dir)

import config

print("=" * 60)
print("向量数据库存储位置信息")
print("=" * 60)
print(f"\n配置路径: {config.VECTOR_DB_PATH}")
print(f"绝对路径: {os.path.abspath(config.VECTOR_DB_PATH)}")
print(f"路径存在: {os.path.exists(config.VECTOR_DB_PATH)}")

if os.path.exists(config.VECTOR_DB_PATH):
    print(f"\n目录内容:")
    for item in os.listdir(config.VECTOR_DB_PATH):
        item_path = os.path.join(config.VECTOR_DB_PATH, item)
        if os.path.isdir(item_path):
            print(f"  [目录] {item}")
        else:
            size = os.path.getsize(item_path)
            print(f"  [文件] {item} ({size:,} 字节)")
    
    db_file = os.path.join(config.VECTOR_DB_PATH, "chroma.sqlite3")
    if os.path.exists(db_file):
        size = os.path.getsize(db_file)
        print(f"\n数据库文件: {db_file}")
        print(f"文件大小: {size:,} 字节 ({size / 1024 / 1024:.2f} MB)")
else:
    print("\n警告: 向量数据库目录不存在!")

# 检查实际使用的数据库
try:
    from database.vector_db import VectorDatabase
    vdb = VectorDatabase()
    print(f"\n实际使用的数据库路径: {vdb.client._path if hasattr(vdb.client, '_path') else '无法获取'}")
    print(f"Collection名称: {vdb.collection.name}")
    print(f"记录数: {vdb.collection.count()}")
except Exception as e:
    print(f"\n无法连接向量数据库: {e}")

print("\n" + "=" * 60)

