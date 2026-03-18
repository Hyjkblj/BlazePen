#!/usr/bin/env python3
"""测试音色试听功能"""

from api.services.tts_service import TTSService
from data.preset_voices import get_preset_voice

def test_voice_preview():
    """测试音色试听功能"""
    # 测试音色试听
    tts = TTSService()
    print('🎵 测试音色试听功能...')

    # 测试几个不同的音色
    test_voices = ['female_001', 'male_001', 'female_006']

    for voice_id in test_voices:
        voice = get_preset_voice(voice_id)
        if voice:
            print(f'\n🎤 测试音色: {voice["name"]} ({voice_id})')
            print(f'   描述: {voice["description"]}')
            print(f'   火山引擎音色ID: {voice["voice_id"]}')
            
            try:
                result = tts.generate_speech(
                    text=voice['preview_text'],
                    character_id=0,
                    override_voice_id=voice['voice_id']
                )
                print(f'   ✅ 生成成功: {result["audio_url"]}')
                print(f'   时长: {result.get("duration", 0):.2f}秒')
            except Exception as e:
                print(f'   ❌ 生成失败: {e}')

    print('\n🎉 音色试听测试完成！')

if __name__ == '__main__':
    test_voice_preview()