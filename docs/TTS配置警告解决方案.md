# TTS配置警告解决方案

**警告信息**：
```
UserWarning: 开发环境警告：以下TTS配置项未设置，TTS功能将不可用：
VOLCENGINE_TTS_APP_ID, VOLCENGINE_TTS_ACCESS_TOKEN, VOLCENGINE_TTS_SECRET_KEY。
请复制 .env.example 为 .env 并填写相应配置。
```

---

## 📋 问题说明

这是一个**开发环境的友好警告**，不会阻止应用启动。它只是提醒你TTS功能需要这些配置才能使用。

---

## ✅ 解决方案

### 方案1：配置TTS（如果需要TTS功能）

如果你需要使用TTS（文本转语音）功能，需要配置火山引擎TTS的密钥：

#### 步骤1：创建 `.env` 文件

```bash
# 在 backend 目录下
cd backend
cp .env.example .env
```

#### 步骤2：填写TTS配置

编辑 `backend/.env` 文件，填写以下配置：

```env
# TTS语音合成配置（必需，如果使用火山引擎TTS）
VOLCENGINE_TTS_APP_ID=你的应用ID
VOLCENGINE_TTS_ACCESS_TOKEN=你的访问令牌
VOLCENGINE_TTS_SECRET_KEY=你的密钥
VOLCENGINE_TTS_MODEL=seed-tts-2.0
VOLCENGINE_TTS_RESOURCE_ID=volc.tts.default
```

#### 步骤3：获取火山引擎TTS密钥

1. 访问 [火山引擎控制台](https://console.volcengine.com/)
2. 创建应用并获取TTS服务的密钥
3. 将密钥填入 `.env` 文件

#### 步骤4：重启应用

配置完成后，重启应用，警告就会消失。

---

### 方案2：禁用警告（如果不需要TTS功能）

如果你**不需要TTS功能**，可以：

#### 选项A：设置空值（推荐）

在 `backend/.env` 文件中设置空值：

```env
VOLCENGINE_TTS_APP_ID=
VOLCENGINE_TTS_ACCESS_TOKEN=
VOLCENGINE_TTS_SECRET_KEY=
```

这样警告仍然会出现，但不会影响应用运行。

#### 选项B：修改配置代码（不推荐）

如果你确定不需要TTS功能，可以修改 `backend/config.py`，将警告改为只在需要时显示：

```python
# 只在TTS_PROVIDER为volcengine时检查
if _env == 'dev' and config.TTS_PROVIDER == 'volcengine':
    # 显示警告...
```

**注意**：不推荐修改代码，因为这会降低配置的可见性。

---

### 方案3：切换到其他TTS提供商

如果你不想使用火山引擎TTS，可以切换到其他提供商：

#### 使用DashScope TTS

在 `backend/.env` 文件中：

```env
# 切换到DashScope TTS
TTS_PROVIDER=dashscope
DASHSCOPE_API_KEY=你的DashScope API Key
DASHSCOPE_TTS_MODEL=sambert-zhichu-v1
```

这样就不需要配置火山引擎TTS密钥了。

---

## 🔍 检查当前配置

你可以运行以下命令检查当前TTS配置：

```bash
cd backend
python -c "import config; print(f'TTS Provider: {config.TTS_PROVIDER}'); print(f'VolcEngine TTS Enabled: {bool(config.VOLCENGINE_TTS_APP_ID)}')"
```

---

## 📝 配置优先级

1. **环境变量** (`.env` 文件) - 最高优先级
2. **默认值** - 如果环境变量未设置

---

## ⚠️ 注意事项

1. **开发环境**：警告不会阻止应用启动，TTS功能只是不可用
2. **生产环境**：如果 `ENV=prod`，未配置TTS密钥会**抛出异常**，阻止启动
3. **安全**：`.env` 文件包含敏感信息，**不要提交到Git仓库**

---

## 🎯 推荐做法

- **开发环境**：如果暂时不需要TTS，可以忽略警告
- **生产环境**：必须配置所有必需的密钥
- **团队协作**：使用 `.env.example` 作为模板，每个开发者创建自己的 `.env` 文件

---

## 📚 相关文档

- [密钥配置指南](./密钥配置指南.md)
- [.env.example](../backend/.env.example) - 配置模板
- [TTS服务文档](./WEBSOCKET_TTS_GUIDE.md)
