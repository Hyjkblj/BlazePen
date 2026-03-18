"""数据库迁移脚本：为characters表添加character_data字段"""
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

from sqlalchemy import text
from database.db_manager import DatabaseManager
import config


def migrate_add_character_data():
    """为characters表添加character_data字段（JSON类型）"""
    print("=" * 60)
    print("数据库迁移：添加character_data字段")
    print("=" * 60)
    
    try:
        db_manager = DatabaseManager()
        engine = db_manager.engine
        
        print("\n正在检查字段是否存在...")
        
        # 检查字段是否已存在
        with engine.connect() as conn:
            # PostgreSQL检查字段是否存在
            check_sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'characters' 
                AND column_name = 'character_data'
            """)
            result = conn.execute(check_sql)
            exists = result.fetchone() is not None
        
        if exists:
            print("  [信息] character_data字段已存在，无需迁移")
            return 0
        
        print("  [信息] character_data字段不存在，开始添加...")
        
        # 添加character_data字段
        with engine.connect() as conn:
            # PostgreSQL添加JSON字段
            alter_sql = text("""
                ALTER TABLE characters 
                ADD COLUMN character_data JSON
            """)
            conn.execute(alter_sql)
            conn.commit()
        
        print("  [成功] character_data字段已添加")
        
        # 验证
        with engine.connect() as conn:
            check_sql = text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'characters' 
                AND column_name = 'character_data'
            """)
            result = conn.execute(check_sql)
            row = result.fetchone()
            if row:
                print(f"  [验证] 字段类型: {row[1]}")
        
        print("\n迁移完成！")
        return 0
        
    except Exception as e:
        print(f"\n[错误] 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = migrate_add_character_data()
    sys.exit(exit_code)

