"""创建数据库脚本 - 创建PostgreSQL数据库和表结构"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2 import sql
import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 直接读取配置，避免导入可能依赖其他模块的config
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'noendstory'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}


def create_database():
    """创建PostgreSQL数据库（如果不存在）"""
    # 连接到PostgreSQL服务器（使用默认的postgres数据库）
    try:
        print("正在连接到PostgreSQL服务器...")
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database='postgres',  # 连接到默认数据库
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 检查数据库是否存在
        db_name = DB_CONFIG['database']
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        
        exists = cursor.fetchone()
        
        if exists:
            print(f"数据库 '{db_name}' 已存在，跳过创建。")
        else:
            # 创建数据库
            print(f"正在创建数据库 '{db_name}'...")
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(db_name)
                )
            )
            print(f"数据库 '{db_name}' 创建成功！")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"[错误] 连接PostgreSQL服务器失败：{e}")
        print("\n请检查：")
        print("1. PostgreSQL服务是否正在运行")
        print("2. .env文件是否存在且配置正确")
        print("3. 用户名和密码是否正确")
        if not DB_CONFIG['password']:
            print("\n提示：.env文件中DB_PASSWORD为空，请设置数据库密码")
        return False
    except Exception as e:
        print(f"[错误] 创建数据库时发生错误：{e}")
        return False


def drop_existing_tables():
    """删除已存在的表（如果存在）"""
    try:
        print("\n正在检查并删除旧表...")
        import psycopg2
        
        # 连接到目标数据库
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # 需要删除的表（按依赖顺序，先删除外键表）
        tables_to_drop = ['character_attributes', 'character_states', 'characters']
        
        for table_name in tables_to_drop:
            cursor.execute(
                f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')"
            )
            exists = cursor.fetchone()[0]
            if exists:
                print(f"  删除表: {table_name}")
                cursor.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;')
        
        cursor.close()
        conn.close()
        print("[成功] 旧表清理完成")
        return True
    except Exception as e:
        print(f"[警告] 清理旧表时发生错误: {e}")
        import traceback
        traceback.print_exc()
        # 不阻止继续执行，尝试继续创建表
        return True


def init_tables():
    """初始化数据库表结构"""
    try:
        print("\n正在初始化数据库表结构...")
        # 延迟导入，避免在创建数据库阶段就需要所有依赖
        from sqlalchemy import create_engine
        from models.character import Base
        
        engine = create_engine(
            f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        )
        Base.metadata.create_all(engine)
        print("[成功] 数据库表结构初始化完成！")
        return True
    except Exception as e:
        print(f"[错误] 初始化表结构时发生错误：{e}")
        import traceback
        traceback.print_exc()
        return False


def verify_database():
    """验证数据库和表是否创建成功"""
    try:
        print("\n正在验证数据库...")
        from sqlalchemy import create_engine, inspect
        
        engine = create_engine(
            f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        )
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = ['characters', 'character_attributes', 'character_states']
        missing_tables = [t for t in expected_tables if t not in tables]
        
        if missing_tables:
            print(f"[警告] 缺少表：{', '.join(missing_tables)}")
            return False
        else:
            print("[成功] 所有表已成功创建：")
            for table in expected_tables:
                print(f"   - {table}")
            return True
                
    except Exception as e:
        print(f"[错误] 验证数据库时发生错误：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("数据库创建脚本")
    print("=" * 60)
    
    # 检查配置
    if not os.path.exists('.env'):
        print("\n[警告] 未找到 .env 文件")
        print("请先创建 .env 文件并配置数据库连接信息：")
        print("\nDB_HOST=localhost")
        print("DB_PORT=5432")
        print("DB_NAME=noendstory")
        print("DB_USER=postgres")
        print("DB_PASSWORD=你的数据库密码")
        print("\n或者直接运行以下命令创建示例文件：")
        print("  echo DB_HOST=localhost > .env")
        print("  echo DB_PORT=5432 >> .env")
        print("  echo DB_NAME=noendstory >> .env")
        print("  echo DB_USER=postgres >> .env")
        print("  echo DB_PASSWORD=你的密码 >> .env")
        sys.exit(1)
    
    print(f"\n目标数据库：{DB_CONFIG['database']}")
    print(f"数据库主机：{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print(f"数据库用户：{DB_CONFIG['user']}")
    if not DB_CONFIG['password']:
        print("[警告] 数据库密码未设置，如果连接失败请检查 .env 文件中的 DB_PASSWORD")
    print("=" * 60)
    
    # 步骤1: 创建数据库
    if not create_database():
        print("\n[错误] 数据库创建失败，请检查配置后重试。")
        sys.exit(1)
    
    # 步骤1.5: 删除旧表（如果存在）
    drop_existing_tables()
    
    # 步骤2: 初始化表结构
    if not init_tables():
        print("\n[错误] 表结构初始化失败。")
        sys.exit(1)
    
    # 步骤3: 验证数据库
    if not verify_database():
        print("\n[警告] 数据库验证失败，但可能已部分创建。")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("[成功] 数据库创建和初始化完成！")
    print("=" * 60)
    print("\n现在可以运行游戏了：")
    print("  python main.py")


if __name__ == '__main__':
    main()

