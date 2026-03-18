"""清除向量数据库所有数据"""
import sys
import os

# 设置UTF-8编码（Windows控制台支持）
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database.vector_db import VectorDatabase
import config


def clear_vector_database(force=False):
    """清除向量数据库中的所有数据
    
    Args:
        force: 如果为True，跳过确认直接清除
    """
    print("=" * 60)
    print("清除向量数据库数据")
    print("=" * 60)
    
    try:
        # 初始化向量数据库
        vector_db = VectorDatabase()
        collection = vector_db.collection
        
        # 获取当前数据量
        count = collection.count()
        print(f"\n当前数据量: {count} 条记录")
        
        if count == 0:
            print("\n向量数据库已经是空的，无需清除。")
            return 0
        
        # 确认操作
        if not force:
            print(f"\n[警告] 即将删除所有 {count} 条数据！")
            try:
                confirm = input("确认清除所有数据？(输入 'yes' 确认): ")
                if confirm.lower() != 'yes':
                    print("操作已取消。")
                    return 0
            except (EOFError, KeyboardInterrupt):
                print("\n操作已取消。")
                return 0
        else:
            print(f"\n[警告] 强制模式：将删除所有 {count} 条数据！")
        
        # 获取所有文档ID
        print("\n正在获取所有数据...")
        all_results = collection.get()
        all_ids = all_results.get('ids', [])
        
        if not all_ids:
            print("没有找到数据。")
            return 0
        
        # 删除所有数据
        print(f"正在删除 {len(all_ids)} 条数据...")
        collection.delete(ids=all_ids)
        
        # 验证删除结果
        new_count = collection.count()
        print(f"\n[成功] 清除完成！")
        print(f"删除前: {count} 条")
        print(f"删除后: {new_count} 条")
        
        if new_count == 0:
            print("\n所有数据已成功清除。")
        else:
            print(f"\n[警告] 仍有 {new_count} 条数据未删除。")
            
    except Exception as e:
        print(f"\n[错误] 清除失败: {e}")
        print(f"\n提示：如果遇到文件锁定错误，请关闭所有Python进程后重试。")
        return 1
    
    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='清除向量数据库所有数据')
    parser.add_argument('--force', '-f', action='store_true', 
                       help='强制清除，跳过确认')
    args = parser.parse_args()
    
    exit_code = clear_vector_database(force=args.force)
    sys.exit(exit_code)
