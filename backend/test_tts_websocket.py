"""测试 TTS WebSocket 实时合成（QwenTtsRealtime）

使用方式：
  cd backend
  set TTS_USE_WEBSOCKET=1
  python test_tts_websocket.py

依赖：dashscope >= 1.25.2（需包含 dashscope.audio.qwen_tts_realtime）
"""
import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 启用 WebSocket 路径
os.environ['TTS_USE_WEBSOCKET'] = '1'

# 可选：从 .env 或环境变量读取 DASHSCOPE_API_KEY
if not os.getenv('DASHSCOPE_API_KEY'):
    os.environ['DASHSCOPE_API_KEY'] = os.getenv('DASHSCOPE_API_KEY', 'sk-972acd8d4be44cd497bc396f38a6a088')


def main():
    from api.services.tts_service import TTSService, QWEN_TTS_REALTIME_AVAILABLE

    if not QWEN_TTS_REALTIME_AVAILABLE:
        print("[错误] WebSocket 实时 TTS 不可用，请安装 dashscope>=1.25.2")
        print("  pip install 'dashscope>=1.25.2'")
        sys.exit(1)

    tts = TTSService()
    if not tts.enabled:
        print("[错误] TTS 服务未启用，请配置 DASHSCOPE_API_KEY")
        sys.exit(1)

    print("=" * 60)
    print("测试 TTS WebSocket（QwenTtsRealtime）")
    print("=" * 60)
    print(f"TTS_USE_WEBSOCKET: {os.getenv('TTS_USE_WEBSOCKET')}")
    print()

    text = "你好，这是 WebSocket 实时语音合成测试。"
    character_id = 1

    print(f"文本: {text}")
    print(f"角色ID: {character_id}")
    print("调用 generate_speech（将走 WebSocket 路径）...")
    print()

    try:
        result = tts.generate_speech(
            text=text,
            character_id=character_id,
            use_cache=False,
        )
        if result and result.get('audio_url'):
            print("[成功] 语音合成完成")
            print(f"  audio_url: {result['audio_url']}")
            print(f"  duration: {result.get('duration', 'N/A')} 秒")
            print(f"  cached: {result.get('cached', False)}")
            # 可选：复制到测试文件便于播放
            out_path = os.path.join(backend_dir, 'audio', 'cache', 'test_websocket.wav')
            if result.get('audio_path') and os.path.isfile(result['audio_path']):
                import shutil
                shutil.copy(result['audio_path'], out_path)
                print(f"  已复制到: {out_path}")
        else:
            print("[失败] 未返回音频 URL")
            sys.exit(1)
    except Exception as e:
        print(f"[失败] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print()
    print("测试完成。")


if __name__ == '__main__':
    main()
