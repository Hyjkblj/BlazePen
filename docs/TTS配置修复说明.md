# TTS配置修复说明

**修复时间**：2025-02-13  
**问题**：TTS配置警告，需要保留TTS功能

---

## ✅ 已完成的修复

### 1. 添加了TTS配置模板到 `.env` 文件

已在 `backend/.env` 文件中添加了完整的TTS配置模板：

```env
# TTS语音合成配置（火山引擎）
VOLCENGINE_TTS_APP_ID=
VOLCENGINE_TTS_ACCESS_TOKEN=
VOLCENGINE_TTS_SECRET_KEY=
VOLCENGINE_TTS_MODEL=seed-tts-2.0
VOLCENGINE_TTS_RESOURCE_ID=volc.tts.default
TTS_PROVIDER=volcengine
```

### 2. 优化了配置验证逻辑

修改了 `backend/config.py` 中的配置验证逻辑：
- **改进前**：无论使用哪个TTS提供商，都会检查火山引擎TTS配置
- **改进后**：只有当 `TTS_PROVIDER=volcengine` 时才检查火山引擎TTS配置

这样，如果你使用DashScope TTS，就不会再显示火山引擎TTS的警告了。

---

## 📝 下一步操作

### 如果你之前配置过火山引擎TTS：

1. **打开 `backend/.env` 文件**
2. **填写你的TTS密钥**：
   ```env
   VOLCENGINE_TTS_APP_ID=你的应用ID
   VOLCENGINE_TTS_ACCESS_TOKEN=你的访问令牌
   VOLCENGINE_TTS_SECRET_KEY=你的密钥
   ```
3. **保存文件并重启应用**

### 如果你想使用DashScope TTS（不需要火山引擎密钥）：

1. **打开 `backend/.env` 文件**
2. **修改TTS提供商**：
   ```env
   TTS_PROVIDER=dashscope
   ```
3. **确保已配置DashScope API Key**（你的.env文件中已有）：
   ```env
   DASHSCOPE_API_KEY=sk-e0a59859ccfa439b8e11636493b51d80
   ```
4. **保存文件并重启应用**

这样就不会再显示火山引擎TTS的警告了。

---

## 🔍 验证配置

重启应用后，警告应该消失。如果使用火山引擎TTS，确保：
- `VOLCENGINE_TTS_APP_ID` 不为空
- `VOLCENGINE_TTS_ACCESS_TOKEN` 不为空
- `VOLCENGINE_TTS_SECRET_KEY` 不为空

如果使用DashScope TTS，确保：
- `TTS_PROVIDER=dashscope`
- `DASHSCOPE_API_KEY` 已配置

---

## 📚 相关文档

- [TTS配置警告解决方案](./TTS配置警告解决方案.md)
- [密钥配置指南](./密钥配置指南.md)
- [.env.example](../backend/.env.example)
