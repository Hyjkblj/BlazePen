"""测试TTS服务"""
import os
import sys

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from api.services.tts_service import TTSService

def test_tts_service():
    """测试TTS服务"""
    print("=" * 50)
    print("测试DashScope TTS服务")
    print("=" * 50)
    
    # 初始化TTS服务
    try:
        tts_service = TTSService()
        if not tts_service.enabled:
            print("[错误] TTS服务未启用，请检查配置")
            return False
    except Exception as e:
        print(f"[错误] 初始化TTS服务失败: {e}")
        return False
    
    # 测试文本
    test_text = "你好，很高兴认识你！这是一个测试。"
    character_id = 1
    
    print(f"\n[测试] 生成语音")
    print(f"文本: {test_text}")
    print(f"角色ID: {character_id}")
    
    try:
        # 生成语音
        audio_info = tts_service.generate_speech(
            text=test_text,
            character_id=character_id,
            emotion_params={
                'emotion': 'happy',
                'speed': 1.0
            },
            use_cache=True
        )
        
        print(f"\n[成功] 语音生成成功！")
        print(f"音频URL: {audio_info['audio_url']}")
        print(f"音频路径: {audio_info['audio_path']}")
        print(f"时长: {audio_info.get('duration', 0):.2f}秒")
        print(f"是否缓存: {audio_info.get('cached', False)}")
        
        # 检查文件是否存在
        import os
        if os.path.exists(audio_info['audio_path']):
            file_size = os.path.getsize(audio_info['audio_path'])
            print(f"文件大小: {file_size / 1024:.2f} KB")
            print(f"\n[成功] 音频文件已保存: {audio_info['audio_path']}")
            return True
        else:
            print(f"[错误] 音频文件不存在: {audio_info['audio_path']}")
            return False
            
    except Exception as e:
        print(f"\n[错误] 生成语音失败: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_preset_voices():
    """测试预设音色库"""
    print("\n" + "=" * 50)
    print("测试预设音色库")
    print("=" * 50)
    
    from data.preset_voices import get_preset_voices_by_gender, get_all_preset_voices
    
    # 获取所有预设音色
    all_voices = get_all_preset_voices()
    
    print(f"\n男声音色数量: {len(all_voices.get('male', []))}")
    print(f"女声音色数量: {len(all_voices.get('female', []))}")
    print(f"中性音色数量: {len(all_voices.get('neutral', []))}")
    
    # 显示男声音色
    print("\n[男声音色]")
    for voice in all_voices.get('male', []):
        print(f"  - {voice['name']}: {voice['description']} (ID: {voice['voice_id']})")
    
    # 显示女声音色
    print("\n[女声音色]")
    for voice in all_voices.get('female', []):
        print(f"  - {voice['name']}: {voice['description']} (ID: {voice['voice_id']})")
    
    return True

if __name__ == '__main__':
    print("\n开始测试TTS服务...\n")
    
    # 测试预设音色库
    test_preset_voices()
    
    # 测试TTS服务
    success = test_tts_service()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ 所有测试通过！")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("❌ 测试失败，请检查配置和错误信息")
        print("=" * 50)
        sys.exit(1)
