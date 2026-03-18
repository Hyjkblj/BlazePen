#!/usr/bin/env python3
"""测试阿里云百炼TTS API"""

import os
import sys

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

def test_dashscope_tts():
    """测试阿里云百炼TTS"""
    try:
        import dashscope
        from dashscope.audio.tts_v2 import SpeechSynthesizer
        
        # 设置API Key
        dashscope.api_key = config.DASHSCOPE_API_KEY
        
        print("🔍 测试阿里云百炼TTS API")
        print(f"API Key: {config.DASHSCOPE_API_KEY[:8]}...{config.DASHSCOPE_API_KEY[-4:]}")
        print(f"模型: {config.DASHSCOPE_TTS_MODEL}")
        
        # 创建SpeechSynthesizer实例 - 使用基础模型
        synthesizer = SpeechSynthesizer(
            model='qwen3-tts-flash',  # 使用基础模型
            voice='zhichu'
        )
        
        # 尝试不同的参数组合
        test_cases = [
            # 基本调用
            {
                'name': '基本调用',
                'params': {
                    'text': '你好，这是测试'
                }
            },
            # 带模型参数
            {
                'name': '带模型参数',
                'params': {
                    'model': config.DASHSCOPE_TTS_MODEL,
                    'text': '你好，这是测试'
                }
            },
            # 带音色参数
            {
                'name': '带音色参数',
                'params': {
                    'text': '你好，这是测试',
                    'voice': 'zhichu'
                }
            }
        ]
        
        for test_case in test_cases:
            print(f"\n🧪 测试: {test_case['name']}")
            print(f"   参数: {test_case['params']}")
            
            try:
                result = synthesizer.call(**test_case['params'])
                print(f"   ✅ 调用成功")
                print(f"   状态码: {result.status_code}")
                
                if hasattr(result, 'message'):
                    print(f"   消息: {result.message}")
                
                if result.status_code == 200:
                    print(f"   🎵 语音生成成功！")
                    # 尝试获取音频数据
                    try:
                        audio_data = result.get_audio_data()
                        print(f"   音频数据大小: {len(audio_data)} bytes")
                        return True
                    except Exception as e:
                        print(f"   ⚠️  获取音频数据失败: {e}")
                else:
                    print(f"   ❌ 生成失败")
                    
            except Exception as e:
                print(f"   ❌ 调用失败: {e}")
        
        return False
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("请安装dashscope: pip install dashscope")
        return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主函数"""
    success = test_dashscope_tts()
    
    if success:
        print("\n🎉 阿里云百炼TTS测试成功！")
    else:
        print("\n❌ 阿里云百炼TTS测试失败")
        print("可能的原因：")
        print("1. API Key无效或过期")
        print("2. 服务未开通或配额不足")
        print("3. 网络连接问题")

if __name__ == "__main__":
    main()