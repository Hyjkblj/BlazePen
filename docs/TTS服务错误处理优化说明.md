# TTS 服务错误处理优化说明

## 问题描述

用户反馈前端试听音色时出现 503 错误，错误信息显示"请检查阿里云百炼（DashScope）账号状态与计费"，但实际配置使用的是火山引擎（VolcEngine）TTS 服务。错误信息与实际提供商不匹配，导致用户困惑。

## 优化内容

### 1. 后端错误处理优化

**文件**：`backend/api/routers/tts.py`

#### 1.1 修复错误信息硬编码问题

- **问题**：`_tts_error_response` 函数硬编码了 DashScope 的错误信息
- **解决方案**：根据实际的 TTS 提供商动态生成错误信息

```python
def _tts_error_response(exc: Exception, provider: str = 'volcengine') -> tuple[int, str]:
    """根据 TTS 提供商生成对应的错误提示"""
    provider_messages = {
        'volcengine': '语音服务暂不可用，请检查火山引擎（VolcEngine）账号状态与计费。',
        'dashscope': '语音服务暂不可用，请检查阿里云百炼（DashScope）账号状态与计费。',
        'edge-tts': '语音服务暂不可用，请检查网络连接或 Edge TTS 服务状态。',
    }
    default_message = provider_messages.get(provider, '语音服务暂不可用，请检查服务配置。')
    # ...
```

#### 1.2 更新所有错误处理调用

- 在所有调用 `_tts_error_response` 的地方传入 `tts_service.provider` 参数
- 确保错误信息根据实际使用的 TTS 提供商生成

#### 1.3 添加 TTS 服务状态检查接口

**新增接口**：`GET /api/v1/tts/status`

**返回数据**：
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "enabled": true,
    "provider": "volcengine",
    "model": "seed-tts-2.0",
    "voice_design_enabled": false,
    "message": "TTS服务已启用"
  }
}
```

**用途**：
- 前端可以查询 TTS 服务的状态和提供商信息
- 根据状态显示相应的提示信息

#### 1.4 优化试听接口错误提示

- 当 TTS 服务未启用时，根据提供商显示对应的错误信息
- 例如：`"TTS服务未启用，请检查火山引擎（VolcEngine）配置"`

### 2. 前端错误处理优化

**文件**：
- `frontend/src/services/api.ts`
- `frontend/src/pages/CharacterSelection.tsx`

#### 2.1 添加 TTS 状态查询 API

```typescript
export const getTtsStatus = async (): Promise<{
  enabled: boolean;
  provider: string;
  model?: string;
  voice_design_enabled: boolean;
  message: string;
} | null>
```

#### 2.2 优化试听错误处理

- **改进前**：错误信息硬编码为 DashScope
- **改进后**：使用后端返回的错误信息（已根据实际提供商生成）

```typescript
catch (error: unknown) {
  const err = error as { response?: { status?: number; data?: { message?: string } }; message?: string };
  const is503 = err.response?.status === 503;
  // 使用后端返回的错误信息（已根据实际 TTS 提供商生成）
  const errorMsg = err.response?.data?.message || err.message || '试听失败';
  if (is503) {
    message.warning(`${errorMsg}。您仍可选择此音色，游戏中使用时需确保 TTS 服务已启用。`);
  } else {
    message.warning(`试听失败：${errorMsg}`);
  }
}
```

#### 2.3 增强错误对象结构

- 在 `getVoicePreviewAudio` 函数中，确保错误对象包含完整的响应信息
- 便于前端组件访问错误详情

## 支持的 TTS 提供商

| 提供商 | 配置项 | 错误提示 |
|--------|--------|----------|
| 火山引擎（VolcEngine） | `TTS_PROVIDER=volcengine` | "请检查火山引擎（VolcEngine）账号状态与计费" |
| 阿里云百炼（DashScope） | `TTS_PROVIDER=dashscope` | "请检查阿里云百炼（DashScope）账号状态与计费" |
| Edge TTS | `TTS_PROVIDER=edge-tts` | "请检查网络连接或 Edge TTS 服务状态" |

## 使用示例

### 查询 TTS 服务状态

```typescript
import { getTtsStatus } from '@/services/api';

const status = await getTtsStatus();
if (status) {
  console.log(`TTS 提供商: ${status.provider}`);
  console.log(`服务状态: ${status.enabled ? '已启用' : '未启用'}`);
  console.log(`提示信息: ${status.message}`);
}
```

### 试听音色（带错误处理）

```typescript
import { getVoicePreviewAudio } from '@/services/api';

try {
  const result = await getVoicePreviewAudio('female_001', '你好，这是试听。');
  if (result?.audio_url) {
    // 播放音频
  }
} catch (error: any) {
  // 错误信息已根据实际 TTS 提供商生成
  const errorMsg = error.response?.data?.message || error.message;
  console.error('试听失败:', errorMsg);
}
```

## 注意事项

1. **错误信息准确性**：错误信息现在根据实际的 TTS 提供商动态生成，确保用户看到正确的提示
2. **服务状态检查**：可以通过 `/api/v1/tts/status` 接口查询 TTS 服务状态，提前了解服务是否可用
3. **用户体验**：即使 TTS 服务不可用，用户仍可选择音色，只是试听功能会提示服务不可用
4. **向后兼容**：所有修改都保持向后兼容，不影响现有功能

## 测试建议

1. **测试不同 TTS 提供商**：
   - 切换 `TTS_PROVIDER` 配置
   - 验证错误信息是否正确显示对应的提供商名称

2. **测试服务不可用场景**：
   - 禁用 TTS 服务（移除配置或设置无效密钥）
   - 验证错误提示是否友好且准确

3. **测试试听功能**：
   - 正常情况：验证试听功能正常工作
   - 异常情况：验证错误提示准确且不影响音色选择

## 相关文件

- `backend/api/routers/tts.py` - TTS API 路由和错误处理
- `backend/api/services/tts_service.py` - TTS 服务实现
- `backend/models/voice_model_service.py` - 语音大模型服务
- `frontend/src/services/api.ts` - 前端 API 服务
- `frontend/src/pages/CharacterSelection.tsx` - 角色选择页面（音色选择）
