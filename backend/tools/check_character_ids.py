"""检查角色ID情况"""
import sys
import os

# 设置UTF-8编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database.db_manager import DatabaseManager
from sqlalchemy import text


def check_character_ids():
    """检查角色ID情况"""
    print("=" * 60)
    print("检查角色ID情况")
    print("=" * 60)
    
    try:
        db_manager = DatabaseManager()
        
        with db_manager.get_session() as session:
            # 查询所有角色
            result = session.execute(text("""
                SELECT id, name, created_at 
                FROM characters 
                ORDER BY id
            """))
            rows = result.fetchall()
            
            print(f"\n总角色数: {len(rows)}")
            print(f"\n所有角色记录:")
            for row in rows:
                print(f"  ID: {row[0]}, 名称: {row[1]}, 创建时间: {row[2]}")
            
            if rows:
                max_id = max([r[0] for r in rows])
                print(f"\n最大ID: {max_id}")
                
                # 检查是否有ID跳跃
                ids = [r[0] for r in rows]
                missing_ids = []
                for i in range(1, max_id + 1):
                    if i not in ids:
                        missing_ids.append(i)
                
                if missing_ids:
                    print(f"\n缺失的ID: {missing_ids}")
                    print(f"说明: 这些ID对应的角色可能已被删除")
                else:
                    print(f"\nID连续，无缺失")
            
            # 查询序列当前值
            result2 = session.execute(text("""
                SELECT last_value, is_called 
                FROM characters_id_seq
            """))
            seq_info = result2.fetchone()
            if seq_info:
                print(f"\n序列信息:")
                print(f"  当前值: {seq_info[0]}")
                print(f"  是否已调用: {seq_info[1]}")
                print(f"  下次插入的ID将是: {seq_info[0] + 1 if not seq_info[1] else seq_info[0]}")
        
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n[错误] 检查失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    check_character_ids()

