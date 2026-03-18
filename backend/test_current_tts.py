#!/usr/bin/env python3
"""测试当前TTS配置"""

import os
import sys

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

def main():
    print("🔍 当前TTS配置检查")
    print("=" * 40)
    
    print(f"TTS提供商: {config.TTS_PROVIDER}")
    print(f"阿里云API Key: {'已配置' if config.DASHSCOPE_API_KEY else '未配置'}")
    print(f"阿里云TTS模型: {config.DASHSCOPE_TTS_MODEL}")
    print(f"火山引擎应用ID: {config.VOLCENGINE_TTS_APP_ID}")
    print(f"火山引擎访问令牌: {'已配置' if config.VOLCENGINE_TTS_ACCESS_TOKEN else '未配置'}")
    
    print("\n🧪 测试TTS服务初始化")
    try:
        from api.services.tts_service import TTSService
        tts = TTSService()
        print(f"✅ TTS服务初始化成功")
        print(f"   提供商: {tts.provider}")
        print(f"   服务状态: {tts.enabled}")
        print(f"   服务模式: {getattr(tts, 'service_mode', '未知')}")
        
        if tts.enabled:
            print("\n🎵 测试语音生成")
            try:
                result = tts.generate_speech("测试语音生成", 1, use_cache=False)
                print(f"✅ 语音生成成功!")
                print(f"   音频URL: {result['audio_url']}")
                print(f"   音频路径: {result['audio_path']}")
                print(f"   是否缓存: {result['cached']}")
                if 'duration' in result:
                    print(f"   音频时长: {result['duration']:.2f}秒")
            except Exception as e:
                print(f"❌ 语音生成失败: {e}")
        else:
            print("❌ TTS服务未启用")
            
    except Exception as e:
        print(f"❌ TTS服务初始化失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()