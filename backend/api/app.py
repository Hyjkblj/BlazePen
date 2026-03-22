"""FastAPI应用主文件"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from api.app_runtime import install_trace_context_middleware
from api.routers import characters, game, vector_db_admin, tts
from api.cors_config import build_cors_middleware_options
from database.db_manager import DatabaseManager
from api.middleware.error_handler import install_common_exception_handlers
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
install_common_exception_handlers(app)


install_trace_context_middleware(app)

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

app.add_middleware(
    CORSMiddleware,
    **build_cors_middleware_options(service_scope="story"),
)

# 注册路由
app.include_router(characters.router, prefix="/api")
app.include_router(game.router, prefix="/api")
app.include_router(vector_db_admin.router, prefix="/api")
app.include_router(tts.router, prefix="/api")

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

