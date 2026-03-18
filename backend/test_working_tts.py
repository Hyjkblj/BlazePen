#!/usr/bin/env python3
"""测试可用的火山引擎TTS"""

import os
import sys
import requests
import json
import base64
from pathlib import Path

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

def test_working_tts():
    """测试可用的TTS配置"""
    print("🎉 测试可用的火山引擎TTS配置")
    print("=" * 50)
    
    # 使用诊断脚本中成功的配置
    request_data = {
        "app": {
            "appid": config.VOLCENGINE_TTS_APP_ID,
            "token": config.VOLCENGINE_TTS_ACCESS_TOKEN,
            "cluster": "volcano_tts"
        },
        "user": {
            "uid": "test_user"
        },
        "audio": {
            "voice_type": "BV001_streaming",
            "encoding": "wav"
        },
        "request": {
            "reqid": "working_test",
            "text": "你好，这是火山引擎豆包TTS语音合成测试。",
            "text_type": "plain",
            "operation": "query"
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer; {config.VOLCENGINE_TTS_ACCESS_TOKEN}",
        "X-Resource-Id": "volc.tts.default"
    }
    
    try:
        print("📞 调用火山引擎TTS API...")
        response = requests.post(
            "https://openspeech.bytedance.com/api/v1/tts",
            headers=headers,
            json=request_data,
            timeout=30
        )
        
        print(f"📊 响应状态: {response.status_code}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                print(f"📋 响应代码: {response_data.get('code')}")
                print(f"📋 响应消息: {response_data.get('message')}")
                
                if response_data.get('code') == 3000:
                    # 成功！获取音频数据
                    audio_data_b64 = response_data.get('data', '')
                    if audio_data_b64:
                        # 解码音频数据
                        audio_data = base64.b64decode(audio_data_b64)
                        print(f"🎵 音频数据大小: {len(audio_data)} bytes")
                        
                        # 保存音频文件
                        audio_dir = Path(backend_dir) / 'audio' / 'test'
                        audio_dir.mkdir(parents=True, exist_ok=True)
                        audio_path = audio_dir / 'test_success.wav'
                        
                        audio_path.write_bytes(audio_data)
                        print(f"💾 音频已保存到: {audio_path}")
                        
                        # 获取音频时长
                        try:
                            from pydub import AudioSegment
                            audio = AudioSegment.from_file(str(audio_path))
                            duration = len(audio) / 1000.0
                            print(f"⏱️  音频时长: {duration:.2f}秒")
                        except ImportError:
                            print("⚠️  pydub未安装，无法获取音频时长")
                        except Exception as e:
                            print(f"⚠️  获取音频时长失败: {e}")
                        
                        print("\n🎉 火山引擎豆包TTS测试成功！")
                        print("✅ 服务已正确开通并可用")
                        return True
                    else:
                        print("❌ 响应中没有音频数据")
                else:
                    print(f"❌ API返回错误: {response_data.get('message', '未知错误')}")
            except json.JSONDecodeError:
                print("❌ 响应不是有效的JSON格式")
                print(f"响应内容: {response.text[:500]}")
        else:
            print(f"❌ HTTP错误: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")
        
        return False
        
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        return False

def main():
    """主函数"""
    success = test_working_tts()
    
    print("\n" + "=" * 50)
    if success:
        print("🎊 恭喜！火山引擎豆包TTS服务已成功开通！")
        print("\n下一步:")
        print("1. 运行完整测试: python test_doubao_tts.py")
        print("2. 集成到项目中使用")
        print("3. 测试WebSocket流式功能")
    else:
        print("❌ 测试失败，需要进一步调试")
        print("\n建议:")
        print("1. 检查网络连接")
        print("2. 确认API配置正确")
        print("3. 联系技术支持")

if __name__ == "__main__":
    main()