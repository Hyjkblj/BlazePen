"""清除PostgreSQL数据库所有数据"""
import sys
import os
import argparse

# 设置UTF-8编码（Windows控制台支持）
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database.db_manager import DatabaseManager
from models.character import Character, CharacterAttribute, CharacterState
from sqlalchemy import text
import config


def clear_postgresql_database(force=False, drop_tables=False):
    """清除PostgreSQL数据库中的所有数据
    
    Args:
        force: 如果为True，跳过确认直接清除
        drop_tables: 如果为True，删除表并重建（完全重置）
    """
    print("=" * 60)
    print("清除PostgreSQL数据库数据")
    print("=" * 60)
    
    try:
        # 初始化数据库管理器
        db_manager = DatabaseManager()
        engine = db_manager.engine
        
        # 显示数据库配置信息
        print(f"\n数据库配置:")
        print(f"  主机: {config.DB_CONFIG['host']}")
        print(f"  端口: {config.DB_CONFIG['port']}")
        print(f"  数据库: {config.DB_CONFIG['database']}")
        print(f"  用户: {config.DB_CONFIG['user']}")
        
        # 测试连接
        print("\n正在连接数据库...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"  连接成功！PostgreSQL版本: {version.split(',')[0]}")
        
        # 统计当前数据量
        print("\n正在统计当前数据量...")
        with db_manager.get_session() as session:
            char_count = session.query(Character).count()
            attr_count = session.query(CharacterAttribute).count()
            state_count = session.query(CharacterState).count()
            
            total = char_count + attr_count + state_count
            
            print(f"  characters 表: {char_count} 条记录")
            print(f"  character_attributes 表: {attr_count} 条记录")
            print(f"  character_states 表: {state_count} 条记录")
            print(f"  总计: {total} 条记录")
        
        if total == 0:
            print("\n数据库已经是空的，无需清除。")
            return 0
        
        # 确认操作
        if not force:
            print(f"\n[警告] 即将删除所有 {total} 条数据！")
            if drop_tables:
                print("[警告] 将删除所有表并重建表结构！")
            try:
                confirm = input("确认清除所有数据？(输入 'yes' 确认): ")
                if confirm.lower() != 'yes':
                    print("操作已取消。")
                    return 0
            except (EOFError, KeyboardInterrupt):
                print("\n操作已取消。")
                return 0
        else:
            print(f"\n[信息] 强制模式：将删除所有 {total} 条数据！")
            if drop_tables:
                print("[信息] 将删除所有表并重建表结构！")
        
        # 执行清除操作
        print("\n正在清除数据...")
        
        if drop_tables:
            # 方式1：删除所有表并重建
            print("  方式: 删除表并重建")
            from models.character import Base
            Base.metadata.drop_all(engine)
            print("  [完成] 已删除所有表")
            Base.metadata.create_all(engine)
            print("  [完成] 已重建所有表")
        else:
            # 方式2：只删除数据，保留表结构
            print("  方式: 删除数据（保留表结构）")
            with db_manager.get_session() as session:
                # 由于外键关系，先删除子表数据
                deleted_states = session.query(CharacterState).delete()
                print(f"  [完成] 已删除 {deleted_states} 条状态记录")
                
                deleted_attrs = session.query(CharacterAttribute).delete()
                print(f"  [完成] 已删除 {deleted_attrs} 条属性记录")
                
                # 最后删除主表数据
                deleted_chars = session.query(Character).delete()
                print(f"  [完成] 已删除 {deleted_chars} 条角色记录")
                
                session.commit()
        
        # 验证清除结果
        print("\n正在验证清除结果...")
        with db_manager.get_session() as session:
            new_char_count = session.query(Character).count()
            new_attr_count = session.query(CharacterAttribute).count()
            new_state_count = session.query(CharacterState).count()
            new_total = new_char_count + new_attr_count + new_state_count
        
        print(f"\n[成功] 清除完成！")
        print(f"删除前: {total} 条记录")
        print(f"删除后: {new_total} 条记录")
        
        if new_total == 0:
            print("\n所有数据已成功清除。")
        else:
            print(f"\n[警告] 仍有 {new_total} 条数据未删除。")
            
    except Exception as e:
        print(f"\n[错误] 清除失败: {e}")
        import traceback
        traceback.print_exc()
        print(f"\n提示：")
        print(f"  1. 请检查数据库连接配置（.env文件）")
        print(f"  2. 确保PostgreSQL服务正在运行")
        print(f"  3. 确保数据库用户有足够权限")
        return 1
    
    print("\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='清除PostgreSQL数据库所有数据')
    parser.add_argument('--force', '-f', action='store_true', 
                       help='强制清除，跳过确认')
    parser.add_argument('--drop-tables', '-d', action='store_true',
                       help='删除表并重建（完全重置，保留表结构请不使用此选项）')
    args = parser.parse_args()
    
    exit_code = clear_postgresql_database(force=args.force, drop_tables=args.drop_tables)
    sys.exit(exit_code)

