"""合并所有ChromaDB库到一个库"""
import os
import sys
import chromadb
from chromadb.config import Settings

# 项目根目录
root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))

# 所有可能的库路径
all_paths = [
    os.path.join(root, 'vector_db'),  # 目标库（项目根目录）
    os.path.join(root, 'backend', 'vector_db'),
    os.path.join(root, 'backend', 'api', 'vector_db'),
]

# 目标库路径（项目根目录的vector_db）
target_path = os.path.join(root, 'vector_db')

print("=" * 80)
print("ChromaDB库合并工具")
print("=" * 80)
print(f"目标库: {target_path}")
print()

# 检查所有库
sources = []
for path in all_paths:
    sqlite_file = os.path.join(path, 'chroma.sqlite3')
    if os.path.exists(sqlite_file):
        try:
            client = chromadb.PersistentClient(
                path=path,
                settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            collections = client.list_collections()
            if collections:
                for col in collections:
                    count = col.count()
                    if count > 0:
                        sources.append({
                            'path': path,
                            'collection': col,
                            'count': count
                        })
                        print(f"[OK] 发现数据源: {path}")
                        print(f"  集合: {col.name}, 记录数: {count}")
                    else:
                        print(f"[空] 空库: {path} (0条记录)")
            else:
                print(f"[空] 空库: {path} (无集合)")
        except Exception as e:
            print(f"[错误] 无法读取: {path} - {e}")

print()

# 如果没有数据源，退出
if not sources:
    print("没有找到任何数据，退出。")
    sys.exit(0)

# 确保目标库存在
os.makedirs(target_path, exist_ok=True)

# 创建目标客户端
print(f"正在合并到目标库: {target_path}")
target_client = chromadb.PersistentClient(
    path=target_path,
    settings=Settings(anonymized_telemetry=False, allow_reset=True)
)

# 获取或创建目标集合
target_collection = target_client.get_or_create_collection(
    name="story_events",
    metadata={"description": "存储剧情事件内容"}
)

print(f"目标集合当前记录数: {target_collection.count()}")

# 合并所有数据源
total_added = 0
total_skipped = 0

for source in sources:
    print(f"\n正在处理: {source['path']}")
    print(f"  记录数: {source['count']}")
    
    # 获取源集合的所有数据
    source_data = source['collection'].get()
    
    if not source_data.get('ids'):
        print("  跳过：无数据")
        continue
    
    # 获取目标集合中已有的ID（避免重复）
    existing_ids = set()
    if target_collection.count() > 0:
        existing_data = target_collection.get()
        existing_ids = set(existing_data.get('ids', []))
    
    # 准备要添加的数据
    ids_to_add = []
    documents_to_add = []
    metadatas_to_add = []
    
    for i, doc_id in enumerate(source_data['ids']):
        if doc_id not in existing_ids:
            ids_to_add.append(doc_id)
            documents_to_add.append(source_data['documents'][i])
            metadatas_to_add.append(source_data['metadatas'][i])
        else:
            total_skipped += 1
    
    # 批量添加数据
    if ids_to_add:
        # ChromaDB的add方法有数量限制，分批添加
        batch_size = 100
        for i in range(0, len(ids_to_add), batch_size):
            batch_ids = ids_to_add[i:i+batch_size]
            batch_docs = documents_to_add[i:i+batch_size]
            batch_metas = metadatas_to_add[i:i+batch_size]
            
            target_collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metas
            )
            total_added += len(batch_ids)
            print(f"  已添加: {len(batch_ids)} 条记录 (批次 {i//batch_size + 1})")
    else:
        print(f"  跳过：所有记录已存在")

print()
print("=" * 80)
print("合并完成！")
print(f"  新增记录: {total_added} 条")
print(f"  跳过记录: {total_skipped} 条（已存在）")
print(f"  目标库总记录数: {target_collection.count()} 条")
print("=" * 80)

# 自动删除空库
print("\n正在清理空库...")
do_cleanup = True  # 自动清理
if do_cleanup:
    for path in all_paths:
        if path != target_path:
            sqlite_file = os.path.join(path, 'chroma.sqlite3')
            if os.path.exists(sqlite_file):
                try:
                    client = chromadb.PersistentClient(
                        path=path,
                        settings=Settings(anonymized_telemetry=False, allow_reset=True)
                    )
                    collections = client.list_collections()
                    has_data = False
                    for col in collections:
                        if col.count() > 0:
                            has_data = True
                            break
                    
                    if not has_data:
                        import shutil
                        import time
                        # 关闭客户端连接
                        try:
                            client.clear_system_cache()
                        except:
                            pass
                        time.sleep(0.5)  # 等待文件释放
                        try:
                            shutil.rmtree(path)
                            print(f"[OK] 已删除空库: {path}")
                        except Exception as e2:
                            print(f"[警告] 无法删除（可能被占用）: {path}")
                            print(f"  请手动删除或重启服务后重试")
                    else:
                        print(f"[保留] 保留库（有数据）: {path}")
                except Exception as e:
                    print(f"[错误] 无法删除: {path} - {e}")
    print("\n清理完成！")
else:
    print("保留其他库。")

