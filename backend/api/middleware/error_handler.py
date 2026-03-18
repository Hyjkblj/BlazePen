"""统一异常处理中间件"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from api.exceptions import ServiceException
import logging

logger = logging.getLogger(__name__)


async def service_exception_handler(request: Request, exc: ServiceException):
    """处理ServiceException异常"""
    logger.error(
        f"Service异常: {exc.message}",
        extra={
            "code": exc.code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.code,
        content={
            "error": exc.message,
            "code": exc.code,
            "details": exc.details
        }
    )


async def general_exception_handler(request: Request, exc: Exception):
    """处理通用异常"""
    logger.exception(
        f"未处理的异常: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "服务器内部错误",
            "code": 500,
            "message": str(exc) if logger.level == logging.DEBUG else "请联系管理员"
        }
    )
