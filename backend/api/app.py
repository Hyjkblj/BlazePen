"""FastAPI应用主文件"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from api.routers import characters, game, vector_db_admin, tts, training
from database.db_manager import DatabaseManager
from api.exceptions import ServiceException
from api.middleware.error_handler import service_exception_handler, general_exception_handler
from utils.logger import setup_logger
import uvicorn
import os
import config

# 配置日志
logger = setup_logger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="无限流剧情游戏API",
    description="无限流剧情游戏后端API接口",
    version="1.0.0"
)

# 注册异常处理器
app.add_exception_handler(ServiceException, service_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# 应用启动时只检查数据库连接，不再隐式补表。
# 数据库 schema 的创建和升级统一交给显式脚本处理，避免不同环境启动时出现“偷偷改库”。
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    try:
        logger.info("正在检查数据库连接...")
        db_manager = DatabaseManager()
        db_manager.check_connection()
        logger.info("数据库连接检查通过")
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}", exc_info=True)
        # 不阻止应用启动，但会记录错误，真正的建库建表请先执行 scripts/init_db.py

# 配置CORS（允许前端跨域请求）
# 根据环境变量配置允许的来源（安全最佳实践）
_env = os.getenv('ENV', 'dev')
if _env == 'prod':
    # 生产环境：只允许指定的前端域名
    allowed_origins_str = os.getenv('ALLOWED_ORIGINS', '')
    if not allowed_origins_str:
        raise ValueError("生产环境必须设置 ALLOWED_ORIGINS 环境变量（逗号分隔的前端域名列表）")
    allowed_origins = [origin.strip() for origin in allowed_origins_str.split(',')]
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allowed_headers = ["Content-Type", "Authorization", "X-Requested-With"]
else:
    # 开发环境：允许本地开发服务器
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    # 如果设置了ALLOWED_ORIGINS，也添加到允许列表
    if os.getenv('ALLOWED_ORIGINS'):
        allowed_origins.extend([origin.strip() for origin in os.getenv('ALLOWED_ORIGINS').split(',')])
    allowed_methods = ["*"]
    allowed_headers = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # ✅ 只允许指定来源
    allow_credentials=True,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
)

# 注册路由
app.include_router(characters.router, prefix="/api")
app.include_router(game.router, prefix="/api")
app.include_router(vector_db_admin.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(training.router, prefix="/api")

# 配置静态文件服务（用于提供本地保存的图片）
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 配置角色图片静态文件服务
try:
    if os.path.isabs(config.IMAGE_SAVE_DIR):
        character_images_dir = config.IMAGE_SAVE_DIR
    else:
        character_images_dir = os.path.join(backend_dir, config.IMAGE_SAVE_DIR)
    
    # 确保目录存在
    os.makedirs(character_images_dir, exist_ok=True)
    
    # 挂载静态文件服务
    # 访问路径：/static/images/characters/{filename}
    app.mount("/static/images/characters", StaticFiles(directory=character_images_dir), name="character_images")
    logger.info(f"角色图片静态文件服务已配置: {character_images_dir} -> /static/images/characters")
except Exception as e:
    logger.warning(f"配置角色图片静态文件服务失败: {e}，本地图片将无法通过URL访问")

# 配置场景图片静态文件服务（大场景）
try:
    if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
        scene_images_dir = config.SCENE_IMAGE_SAVE_DIR
    else:
        scene_images_dir = os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR)
    
    # 确保目录存在
    os.makedirs(scene_images_dir, exist_ok=True)
    
    # 挂载静态文件服务
    # 访问路径：/static/images/scenes/{filename}
    app.mount("/static/images/scenes", StaticFiles(directory=scene_images_dir), name="scene_images")
    logger.info(f"场景图片静态文件服务已配置: {scene_images_dir} -> /static/images/scenes")
except Exception as e:
    logger.warning(f"配置场景图片静态文件服务失败: {e}，本地图片将无法通过URL访问")

# 配置小场景图片静态文件服务
try:
    if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
        small_scene_images_dir = config.SMALL_SCENE_IMAGE_SAVE_DIR
    else:
        small_scene_images_dir = os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR)
    
    # 确保目录存在
    os.makedirs(small_scene_images_dir, exist_ok=True)
    
    # 挂载静态文件服务
    # 访问路径：/static/images/smallscenes/{filename}
    app.mount("/static/images/smallscenes", StaticFiles(directory=small_scene_images_dir), name="small_scene_images")
    logger.info(f"小场景图片静态文件服务已配置: {small_scene_images_dir} -> /static/images/smallscenes")
except Exception as e:
    logger.warning(f"配置小场景图片静态文件服务失败: {e}，本地图片将无法通过URL访问")

# 配置合成图片静态文件服务
try:
    if os.path.isabs(config.COMPOSITE_IMAGE_SAVE_DIR):
        composite_images_dir = config.COMPOSITE_IMAGE_SAVE_DIR
    else:
        composite_images_dir = os.path.join(backend_dir, config.COMPOSITE_IMAGE_SAVE_DIR)
    
    # 确保目录存在
    os.makedirs(composite_images_dir, exist_ok=True)
    
    # 挂载静态文件服务
    # 访问路径：/static/images/composite/{filename}
    app.mount("/static/images/composite", StaticFiles(directory=composite_images_dir), name="composite_images")
    logger.info(f"合成图片静态文件服务已配置: {composite_images_dir} -> /static/images/composite")
except Exception as e:
    logger.warning(f"配置合成图片静态文件服务失败: {e}，本地图片将无法通过URL访问")

# 配置音频文件静态文件服务（TTS缓存）
try:
    audio_cache_dir = os.path.join(backend_dir, "audio", "cache")
    os.makedirs(audio_cache_dir, exist_ok=True)
    
    # 挂载音频文件静态文件服务
    # 访问路径：/static/audio/cache/{filename}
    app.mount("/static/audio/cache", StaticFiles(directory=audio_cache_dir), name="audio_cache")
    logger.info(f"音频缓存静态文件服务已配置: {audio_cache_dir} -> /static/audio/cache")
except Exception as e:
    logger.warning(f"配置音频缓存静态文件服务失败: {e}")

# 配置管理页面静态文件服务
try:
    admin_dir = os.path.join(backend_dir, "static", "admin")
    os.makedirs(admin_dir, exist_ok=True)
    
    # 挂载管理页面静态文件服务
    app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin")
    logger.info(f"管理页面静态文件服务已配置: {admin_dir} -> /admin")
except Exception as e:
    logger.warning(f"配置管理页面静态文件服务失败: {e}")


@app.get("/health")
async def check_server_health():
    """健康检查"""
    return JSONResponse(
        status_code=200,
        content={"status": "healthy", "message": "服务正常运行"}
    )


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "无限流剧情游戏API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    # 确保工作目录是backend目录，这样相对路径才能正确解析
    import os
    # __file__ 是 api/app.py，需要回到backend目录
    api_dir = os.path.dirname(os.path.abspath(__file__))  # backend/api
    backend_dir = os.path.dirname(api_dir)  # backend
    os.chdir(backend_dir)
    logger.info(f"API服务工作目录: {os.getcwd()}")
    
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

