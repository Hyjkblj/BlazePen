#!/usr/bin/env python3
"""测试火山引擎 Doubao TTS 语音合成功能（支持HTTP和WebSocket模式）"""

import os
import sys
import json
from pathlib import Path

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from api.services.tts_service import TTSService
from data.preset_voices import get_preset_voice, get_all_preset_voices

def test_basic_tts():
    """测试基本TTS功能"""
    print("=== 测试基本TTS功能 ===")
    
    try:
        tts_service = TTSService()
        
        if not tts_service.enabled:
            print("❌ TTS服务未启用，请检查配置")
            return False
        
        # 测试文本
        test_text = "你好，我是火山引擎的语音合成服务。今天天气真不错！"
        character_id = 1
        
        print(f"📝 测试文本: {test_text}")
        print(f"🎭 角色ID: {character_id}")
        print(f"🔧 服务模式: {getattr(tts_service, 'service_mode', '未知')}")
        
        # 生成语音
        result = tts_service.generate_speech(
            text=test_text,
            character_id=character_id,
            use_cache=False  # 不使用缓存，确保调用API
        )
        
        print(f"✅ 语音生成成功!")
        print(f"   音频URL: {result['audio_url']}")
        print(f"   音频路径: {result['audio_path']}")
        print(f"   是否缓存: {result['cached']}")
        if 'duration' in result:
            print(f"   音频时长: {result['duration']:.2f}秒")
        
        # 检查文件是否存在
        audio_path = Path(result['audio_path'])
        if audio_path.exists():
            file_size = audio_path.stat().st_size
            print(f"   文件大小: {file_size} bytes")
        else:
            print("❌ 音频文件不存在")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_preset_voices():
    """测试预设音色"""
    print("\n=== 测试预设音色 ===")
    
    try:
        tts_service = TTSService()
        
        if not tts_service.enabled:
            print("❌ TTS服务未启用")
            return False
        
        # 获取所有预设音色
        all_voices = get_all_preset_voices()
        
        # 测试几个代表性音色
        test_voices = [
            'female_001',  # 通用女声
            'male_001',    # 标准男声
        ]
        
        for voice_id in test_voices:
            voice = get_preset_voice(voice_id)
            if not voice:
                print(f"❌ 音色 {voice_id} 不存在")
                continue
            
            print(f"\n🎵 测试音色: {voice['name']} ({voice_id})")
            print(f"   描述: {voice['description']}")
            print(f"   音色ID: {voice['voice_id']}")
            print(f"   模型版本: {voice.get('model_version', '未知')}")
            
            try:
                result = tts_service.generate_speech(
                    text=voice['preview_text'],
                    character_id=1,
                    override_voice_id=voice_id,
                    use_cache=False
                )
                
                print(f"   ✅ 生成成功: {result['audio_url']}")
                
            except Exception as e:
                print(f"   ❌ 生成失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_emotion_params():
    """测试情绪参数"""
    print("\n=== 测试情绪参数 ===")
    
    try:
        tts_service = TTSService()
        
        if not tts_service.enabled:
            print("❌ TTS服务未启用")
            return False
        
        test_text = "这是一个测试情绪参数的例子。"
        
        # 测试不同的情绪参数
        emotion_tests = [
            {
                'name': '正常语速',
                'params': {'speech_rate': 0, 'loudness_rate': 0}
            },
            {
                'name': '快速语音',
                'params': {'speech_rate': 50, 'loudness_rate': 0}  # 1.5倍速
            },
            {
                'name': '慢速语音',
                'params': {'speech_rate': -20, 'loudness_rate': 0}  # 0.8倍速
            },
            {
                'name': '大音量',
                'params': {'speech_rate': 0, 'loudness_rate': 30}  # 1.3倍音量
            },
        ]
        
        # 如果支持情感，添加情感测试
        if tts_service.service_mode == 'websocket':
            emotion_tests.append({
                'name': '开心情感',
                'params': {'emotion': 'happy', 'emotion_scale': 4}
            })
        
        for test in emotion_tests:
            print(f"\n🎭 测试: {test['name']}")
            print(f"   参数: {test['params']}")
            
            try:
                result = tts_service.generate_speech(
                    text=test_text,
                    character_id=1,
                    emotion_params=test['params'],
                    use_cache=False
                )
                
                print(f"   ✅ 生成成功: {result['audio_url']}")
                
            except Exception as e:
                print(f"   ❌ 生成失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_configuration():
    """测试配置信息"""
    print("\n=== 测试配置信息 ===")
    
    try:
        import config
        
        print(f"🔧 TTS提供商: {getattr(config, 'TTS_PROVIDER', '未配置')}")
        print(f"🔧 火山引擎应用ID: {'已配置' if config.VOLCENGINE_TTS_APP_ID else '未配置'}")
        print(f"🔧 火山引擎访问令牌: {'已配置' if config.VOLCENGINE_TTS_ACCESS_TOKEN else '未配置'}")
        print(f"🔧 火山引擎密钥: {'已配置' if config.VOLCENGINE_TTS_SECRET_KEY else '未配置'}")
        print(f"🔧 火山引擎区域: {config.VOLCENGINE_REGION}")
        print(f"🔧 TTS模型: {getattr(config, 'VOLCENGINE_TTS_MODEL', '未配置')}")
        print(f"🔧 资源ID: {getattr(config, 'VOLCENGINE_TTS_RESOURCE_ID', '未配置')}")
        print(f"🔧 使用WebSocket: {getattr(config, 'VOLCENGINE_TTS_USE_WEBSOCKET', '未配置')}")
        
        # 检查环境变量
        env_vars = [
            'VOLCENGINE_TTS_APP_ID',
            'VOLCENGINE_TTS_ACCESS_TOKEN', 
            'VOLCENGINE_TTS_SECRET_KEY',
            'VOLCENGINE_REGION',
            'VOLCENGINE_TTS_MODEL',
            'VOLCENGINE_TTS_RESOURCE_ID',
            'VOLCENGINE_TTS_USE_WEBSOCKET',
            'TTS_PROVIDER'
        ]
        
        print("\n📋 环境变量检查:")
        for var in env_vars:
            value = os.getenv(var)
            if value:
                # 隐藏敏感信息
                if any(keyword in var for keyword in ['TOKEN', 'KEY', 'SECRET']):
                    if len(value) > 8:
                        display_value = value[:4] + '...' + value[-4:]
                    else:
                        display_value = '***'
                else:
                    display_value = value
                print(f"   ✅ {var}: {display_value}")
            else:
                print(f"   ❌ {var}: 未设置")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 火山引擎 Doubao TTS 测试开始")
    print("=" * 50)
    
    # 运行所有测试
    tests = [
        ("配置检查", test_configuration),
        ("基本TTS功能", test_basic_tts),
        ("预设音色", test_preset_voices),
        ("情绪参数", test_emotion_params),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果汇总
    print("\n" + "="*50)
    print("📊 测试结果汇总:")
    
    passed = 0
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 总计: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！火山引擎 Doubao TTS 集成成功！")
    else:
        print("⚠️  部分测试失败，请检查配置和网络连接")
    
    # 提示WebSocket测试
    print("\n💡 提示:")
    print("   如需测试WebSocket流式功能，请运行: python test_websocket_tts.py")

if __name__ == "__main__":
    main()