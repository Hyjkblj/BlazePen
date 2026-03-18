"""启动FastAPI服务器"""
import uvicorn
import os

if __name__ == "__main__":
    # 确保工作目录是backend目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"API服务工作目录: {os.getcwd()}")
    
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

