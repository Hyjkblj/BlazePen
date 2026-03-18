# print()语句替换进度报告

## ✅ 已完成

### 路由文件 (routers/)
- ✅ `characters.py` - 64处print已全部替换为logger
- ✅ `game.py` - 11处print已全部替换为logger
- ✅ `tts.py` - 9处print已全部替换为logger

**总计**: 84处print已替换

### 服务文件 (services/)
- ✅ `game_session.py` - 6处print已全部替换为logger
- ✅ `character_service.py` - 9处print已全部替换为logger
- ✅ `tts_service.py` - 部分print已替换（之前已完成）

## 🟡 进行中

### 服务文件 (services/)
- 🟡 `game_service.py` - 121处print待替换
- 🟡 `image_service.py` - 132处print待替换（已处理导入部分）
- 🟡 `websocket_tts_service.py` - 27处print待替换

## 📊 统计

- **已完成**: 99处print已替换
- **待处理**: 约280处print待替换
- **完成进度**: 约26%

## 🎯 下一步

1. 继续处理`game_service.py`（121处）- 这是最大的文件
2. 处理`image_service.py`（132处）- 注意这个文件很大，需要仔细处理
3. 处理`websocket_tts_service.py`（27处）

## 📝 替换规则

- `print("[信息] ...")` → `logger.info("...")`
- `print("[警告] ...")` → `logger.warning("...")`
- `print("[错误] ...")` → `logger.error("...", exc_info=True)`
- `print("[调试] ...")` → `logger.debug("...")`
- `print(traceback.format_exc())` → 使用`exc_info=True`参数

## ⚠️ 注意事项

1. 确保每个文件顶部都添加了logger导入：
   ```python
   from utils.logger import get_logger
   logger = get_logger(__name__)
   ```

2. 对于错误处理，使用`exc_info=True`而不是单独打印traceback

3. 对于调试信息，使用`logger.debug()`而不是`logger.info()`

4. 保持日志消息的简洁性，移除`[API]`、`[信息]`等前缀（日志级别已经说明了）
