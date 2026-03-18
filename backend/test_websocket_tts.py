#!/usr/bin/env python3
"""测试火山引擎双向流式WebSocket TTS功能"""

import os
import sys
import json
import asyncio
from pathlib import Path

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from api.services.websocket_tts_service import WebSocketTTSService, WebSocketTTSServiceSync
from data.preset_voices import get_preset_voice, get_all_preset_voices, get_emotion_voices, create_mix_config

def test_configuration():
    """测试配置信息"""
    print("=== 测试配置信息 ===")
    
    try:
        import config
        
        print(f"🔧 TTS提供商: {getattr(config, 'TTS_PROVIDER', '未配置')}")
        print(f"🔧 火山引擎应用ID: {'已配置' if config.VOLCENGINE_TTS_APP_ID else '未配置'}")
        print(f"🔧 火山引擎访问令牌: {'已配置' if config.VOLCENGINE_TTS_ACCESS_TOKEN else '未配置'}")
        print(f"🔧 火山引擎密钥: {'已配置' if config.VOLCENGINE_TTS_SECRET_KEY else '未配置'}")
        print(f"🔧 火山引擎区域: {config.VOLCENGINE_REGION}")
        print(f"🔧 TTS模型: {getattr(config, 'VOLCENGINE_TTS_MODEL', '未配置')}")
        print(f"🔧 资源ID: {getattr(config, 'VOLCENGINE_TTS_RESOURCE_ID', '未配置')}")
        print(f"🔧 WebSocket URL: {getattr(config, 'VOLCENGINE_TTS_WEBSOCKET_URL', '未配置')}")
        print(f"🔧 使用WebSocket: {getattr(config, 'VOLCENGINE_TTS_USE_WEBSOCKET', '未配置')}")
        
        # 检查环境变量
        env_vars = [
            'VOLCENGINE_TTS_APP_ID',
            'VOLCENGINE_TTS_ACCESS_TOKEN', 
            'VOLCENGINE_TTS_SECRET_KEY',
            'VOLCENGINE_REGION',
            'VOLCENGINE_TTS_MODEL',
            'VOLCENGINE_TTS_RESOURCE_ID',
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

async def test_websocket_connection():
    """测试WebSocket连接"""
    print("\n=== 测试WebSocket连接 ===")
    
    try:
        service = WebSocketTTSService()
        
        if not service.enabled:
            print("❌ WebSocket TTS服务未启用，请检查配置")
            return False
        
        print(f"📡 连接到: {service.websocket_url}")
        
        # 测试连接
        connected = await service.connect()
        
        if connected:
            print("✅ WebSocket连接建立成功!")
            print(f"   连接ID: {service.connection_id}")
            
            # 断开连接
            await service.disconnect()
            print("✅ WebSocket连接断开成功!")
            return True
        else:
            print("❌ WebSocket连接失败")
            return False
            
    except Exception as e:
        print(f"❌ WebSocket连接测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

async def test_basic_tts():
    """测试基本TTS功能"""
    print("\n=== 测试基本TTS功能 ===")
    
    try:
        service = WebSocketTTSService()
        
        if not service.enabled:
            print("❌ WebSocket TTS服务未启用")
            return False
        
        # 测试文本
        test_text = "你好，我是火山引擎的双向流式语音合成服务。今天天气真不错！"
        character_id = 1
        
        print(f"📝 测试文本: {test_text}")
        print(f"🎭 角色ID: {character_id}")
        
        # 生成语音
        async with service:
            result = await service.generate_speech(
                text=test_text,
                character_id=character_id,
                speaker="BV001_streaming",
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

async def test_streaming_tts():
    """测试流式TTS功能"""
    print("\n=== 测试流式TTS功能 ===")
    
    try:
        service = WebSocketTTSService()
        
        if not service.enabled:
            print("❌ WebSocket TTS服务未启用")
            return False
        
        test_text = "这是一个流式语音合成的测试。我们将实时接收音频数据块。"
        
        print(f"📝 测试文本: {test_text}")
        print("🔄 开始流式合成...")
        
        chunk_count = 0
        total_size = 0
        
        async with service:
            async for chunk in service.generate_speech_stream(
                text=test_text,
                speaker="BV002_streaming"
            ):
                chunk_count += 1
                total_size += len(chunk)
                print(f"   📦 接收音频块 {chunk_count}: {len(chunk)} bytes")
        
        print(f"✅ 流式合成完成!")
        print(f"   总音频块数: {chunk_count}")
        print(f"   总数据大小: {total_size} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ 流式测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

async def test_emotion_tts():
    """测试情感TTS功能"""
    print("\n=== 测试情感TTS功能 ===")
    
    try:
        service = WebSocketTTSService()
        
        if not service.enabled:
            print("❌ WebSocket TTS服务未启用")
            return False
        
        test_text = "这是一个情感语音合成的测试。"
        
        # 测试不同情感参数
        emotion_tests = [
            {
                'name': '开心情感',
                'params': {'emotion': 'happy', 'emotion_scale': 4}
            },
            {
                'name': '快速语音',
                'params': {'speech_rate': 50}  # 1.5倍速
            },
            {
                'name': '大音量',
                'params': {'loudness_rate': 30}  # 1.3倍音量
            },
        ]
        
        async with service:
            for test in emotion_tests:
                print(f"\n🎭 测试: {test['name']}")
                print(f"   参数: {test['params']}")
                
                try:
                    result = await service.generate_speech(
                        text=test_text,
                        character_id=1,
                        speaker="BV004_streaming",  # 情感女声
                        emotion_params=test['params'],
                        use_cache=False
                    )
                    
                    print(f"   ✅ 生成成功: {result['audio_url']}")
                    
                except Exception as e:
                    print(f"   ❌ 生成失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 情感测试失败: {e}")
        return False

async def test_mix_tts():
    """测试混音TTS功能"""
    print("\n=== 测试混音TTS功能 ===")
    
    try:
        service = WebSocketTTSService()
        
        if not service.enabled:
            print("❌ WebSocket TTS服务未启用")
            return False
        
        test_text = "这是一个混音语音合成的测试，融合了多种音色的特点。"
        
        # 创建混音配置
        mix_configs = [
            {
                'name': '女声混音',
                'speakers': [
                    {'source_speaker': 'BV001_streaming', 'mix_factor': 0.6},
                    {'source_speaker': 'BV002_streaming', 'mix_factor': 0.4}
                ]
            },
            {
                'name': '男女混音',
                'speakers': [
                    {'source_speaker': 'BV001_streaming', 'mix_factor': 0.5},
                    {'source_speaker': 'BV006_streaming', 'mix_factor': 0.5}
                ]
            }
        ]
        
        async with service:
            for config in mix_configs:
                print(f"\n🎵 测试: {config['name']}")
                print(f"   混音配置: {config['speakers']}")
                
                try:
                    result = await service.generate_speech(
                        text=test_text,
                        character_id=1,
                        speaker="custom_mix_bigtts",
                        mix_speakers=config['speakers'],
                        use_cache=False
                    )
                    
                    print(f"   ✅ 生成成功: {result['audio_url']}")
                    
                except Exception as e:
                    print(f"   ❌ 生成失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 混音测试失败: {e}")
        return False

def test_sync_wrapper():
    """测试同步包装器"""
    print("\n=== 测试同步包装器 ===")
    
    try:
        service = WebSocketTTSServiceSync()
        
        if not service.enabled:
            print("❌ 同步WebSocket TTS服务未启用")
            return False
        
        test_text = "这是同步接口的测试。"
        
        print(f"📝 测试文本: {test_text}")
        
        # 使用同步接口生成语音
        result = service.generate_speech(
            text=test_text,
            character_id=1,
            override_voice_id="female_001",
            use_cache=False
        )
        
        print(f"✅ 同步语音生成成功!")
        print(f"   音频URL: {result['audio_url']}")
        print(f"   音频路径: {result['audio_path']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 同步测试失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

async def main():
    """主测试函数"""
    print("🚀 火山引擎双向流式WebSocket TTS 测试开始")
    print("=" * 60)
    
    # 运行所有测试
    tests = [
        ("配置检查", test_configuration, False),
        ("WebSocket连接", test_websocket_connection, True),
        ("基本TTS功能", test_basic_tts, True),
        ("流式TTS功能", test_streaming_tts, True),
        ("情感TTS功能", test_emotion_tts, True),
        ("混音TTS功能", test_mix_tts, True),
        ("同步包装器", test_sync_wrapper, False),
    ]
    
    results = []
    for test_name, test_func, is_async in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if is_async:
                success = await test_func()
            else:
                success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
            results.append((test_name, False))
    
    # 输出测试结果汇总
    print("\n" + "="*60)
    print("📊 测试结果汇总:")
    
    passed = 0
    for test_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\n🎯 总计: {passed}/{len(results)} 个测试通过")
    
    if passed == len(results):
        print("🎉 所有测试通过！火山引擎双向流式WebSocket TTS 集成成功！")
    else:
        print("⚠️  部分测试失败，请检查配置和网络连接")

if __name__ == "__main__":
    asyncio.run(main())