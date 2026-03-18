#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""验证所有依赖是否正常安装"""

import sys
import io

# 设置标准输出为 UTF-8 编码（Windows 兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def check_dependency(name, import_statement, version_attr=None):
    """检查依赖是否可以导入"""
    try:
        module = __import__(import_statement, fromlist=[version_attr] if version_attr else [])
        if version_attr and hasattr(module, version_attr):
            version = getattr(module, version_attr)
            print(f"✓ {name}: {version}")
        else:
            print(f"✓ {name}: 已安装")
        return True
    except ImportError as e:
        print(f"✗ {name}: 导入失败 - {e}")
        return False
    except Exception as e:
        print(f"✗ {name}: 错误 - {e}")
        return False

def main():
    print("=" * 60)
    print("依赖验证")
    print("=" * 60)
    
    results = []
    
    # 核心依赖
    print("\n【核心依赖】")
    results.append(check_dependency("NumPy", "numpy", "__version__"))
    results.append(check_dependency("ChromaDB", "chromadb", "__version__"))
    results.append(check_dependency("rembg", "rembg", "__version__"))
    
    # 数据库相关
    print("\n【数据库相关】")
    results.append(check_dependency("psycopg2", "psycopg2"))
    results.append(check_dependency("SQLAlchemy", "sqlalchemy", "__version__"))
    
    # AI 相关
    print("\n【AI 相关】")
    results.append(check_dependency("dashscope", "dashscope"))
    results.append(check_dependency("sentence_transformers", "sentence_transformers"))
    
    # Web 框架
    print("\n【Web 框架】")
    results.append(check_dependency("FastAPI", "fastapi", "__version__"))
    results.append(check_dependency("Uvicorn", "uvicorn", "__version__"))
    results.append(check_dependency("Pydantic", "pydantic", "__version__"))
    
    # 图片处理
    print("\n【图片处理】")
    results.append(check_dependency("Pillow (PIL)", "PIL", "__version__"))
    
    # HTTP 请求
    print("\n【HTTP 请求】")
    results.append(check_dependency("requests", "requests", "__version__"))
    
    # 测试 rembg 功能
    print("\n【rembg 功能测试】")
    try:
        from rembg import new_session
        session = new_session('isnet-general-use')
        print("✓ rembg 会话创建成功 (isnet-general-use 模型)")
        results.append(True)
    except Exception as e:
        print(f"✗ rembg 会话创建失败: {e}")
        results.append(False)
    
    # 测试 ChromaDB 功能
    print("\n【ChromaDB 功能测试】")
    try:
        import chromadb
        client = chromadb.Client()
        print("✓ ChromaDB 客户端创建成功")
        results.append(True)
    except Exception as e:
        print(f"✗ ChromaDB 客户端创建失败: {e}")
        results.append(False)
    
    # 总结
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"验证结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✓ 所有依赖验证成功！")
        return 0
    else:
        print("✗ 部分依赖验证失败，请检查上面的错误信息")
        return 1

if __name__ == "__main__":
    sys.exit(main())
