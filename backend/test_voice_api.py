#!/usr/bin/env python3
"""测试音色API接口"""

import requests
import json
from data.preset_voices import get_all_preset_voices

def test_preset_voices_data():
    """测试预设音色数据"""
    print("=== 测试预设音色数据 ===")
    voices = get_all_preset_voices()
    
    print(f"音色类别数量: {len(voices)}")
    for category, voice_list in voices.items():
        print(f"  {category}: {len(voice_list)} 个音色")
    
    print(f"总计: {sum(len(v) for v in voices.values())} 个音色")
    
    # 显示每个类别的前几个音色
    for category, voice_list in voices.items():
        print(f"\n{category.upper()} 音色列表:")
        for i, voice in enumerate(voice_list[:3]):  # 只显示前3个
            print(f"  {i+1}. {voice['name']} ({voice['style']}) - {voice['description']}")
        if len(voice_list) > 3:
            print(f"  ... 还有 {len(voice_list) - 3} 个音色")

def test_api_endpoint():
    """测试API接口（需要后端服务运行）"""
    print("\n=== 测试API接口 ===")
    
    try:
        # 测试获取所有音色
        response = requests.get("http://localhost:8000/api/v1/tts/presets", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ API接口正常")
            print(f"响应数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        else:
            print(f"❌ API接口异常: {response.status_code}")
            print(f"响应内容: {response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务，请确保后端服务已启动")
    except Exception as e:
        print(f"❌ 请求失败: {e}")

def test_voice_categories():
    """测试按性别获取音色"""
    print("\n=== 测试按性别获取音色 ===")
    
    from data.preset_voices import get_preset_voices_by_gender
    
    for gender in ['female', 'male', 'neutral']:
        voices = get_preset_voices_by_gender(gender)
        print(f"{gender}: {len(voices)} 个音色")
        if voices:
            print(f"  示例: {voices[0]['name']} - {voices[0]['description']}")

if __name__ == "__main__":
    test_preset_voices_data()
    test_voice_categories()
    test_api_endpoint()