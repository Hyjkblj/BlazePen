"""简单测试TTS API（使用 qwen3-tts-flash-realtime）"""
import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ['DASHSCOPE_API_KEY'] = 'sk-972acd8d4be44cd497bc396f38a6a088'

try:
    import dashscope
    from dashscope import MultiModalConversation
    dashscope.api_key = os.environ['DASHSCOPE_API_KEY']
    dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
    print("[信息] DashScope SDK已导入")
except ImportError as e:
    print(f"[错误] DashScope SDK未安装: {e}")
    sys.exit(1)

def test_tts_flash():
    """测试 qwen3-tts-flash-realtime"""
    print("=" * 60)
    print("测试 qwen3-tts-flash-realtime")
    print("=" * 60)
    
    test_text = "你好，这是一个测试。"
    
    print(f"\n文本: {test_text}")
    print(f"模型: qwen3-tts-flash-realtime")
    print(f"音色: Cherry")
    
    try:
        response = MultiModalConversation.call(
            model='qwen3-tts-flash-realtime',
            text=test_text,
            voice='Cherry',
            language_type='Chinese'
        )
        
        print(f"\n状态码: {response.status_code}")
        print(f"响应类型: {type(response)}")
        
        if response.status_code == 200:
            print(f"\n[成功] API调用成功")
            print(f"响应内容: {response}")
            
            # 检查输出
            if hasattr(response, 'output'):
                print(f"\noutput属性存在")
                print(f"output类型: {type(response.output)}")
                print(f"output内容: {response.output}")
                print(f"output属性: {dir(response.output)}")
                
                # 尝试获取音频
                if hasattr(response.output, 'audio'):
                    audio_obj = response.output.audio
                    print(f"\n[成功] 找到音频对象")
                    print(f"音频对象类型: {type(audio_obj)}")
                    print(f"音频对象属性: {dir(audio_obj)}")
                    
                    # 检查audio对象的属性
                    if hasattr(audio_obj, 'data'):
                        print(f"audio.data: {audio_obj.data[:50] if audio_obj.data else '空'}")
                    if hasattr(audio_obj, 'url'):
                        print(f"audio.url: {audio_obj.url}")
                    
                    # 优先使用data字段
                    audio_bytes = None
                    if hasattr(audio_obj, 'data') and audio_obj.data:
                        import base64
                        audio_bytes = base64.b64decode(audio_obj.data)
                        print(f"[使用data字段] 音频长度: {len(audio_bytes)} bytes")
                    elif hasattr(audio_obj, 'url') and audio_obj.url:
                        # 从URL下载
                        import requests
                        print(f"[从URL下载] {audio_obj.url}")
                        audio_response = requests.get(audio_obj.url, timeout=30)
                        audio_response.raise_for_status()
                        audio_bytes = audio_response.content
                        print(f"[下载完成] 音频长度: {len(audio_bytes)} bytes")
                    
                    if audio_bytes:
                        output_path = os.path.join(backend_dir, 'audio', 'cache', 'test_simple.wav')
                        os.makedirs(os.path.dirname(output_path), exist_ok=True)
                        with open(output_path, 'wb') as f:
                            f.write(audio_bytes)
                        print(f"\n[成功] 音频已保存: {output_path}")
                        return True
                    else:
                        print(f"\n[错误] 无法获取音频数据")
                        return False
                else:
                    print(f"\n[警告] output中没有audio属性")
            else:
                print(f"\n[警告] 响应中没有output属性")
                print(f"响应属性: {dir(response)}")
        else:
            print(f"\n[错误] API调用失败")
            print(f"错误信息: {response.message}")
            print(f"错误代码: {getattr(response, 'code', 'N/A')}")
            return False
            
    except Exception as e:
        print(f"\n[错误] 异常: {e}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    print("\n开始测试...\n")
    success = test_tts_flash()
    
    if success:
        print("\n[成功] 测试成功！")
    else:
        print("\n[失败] 测试失败，请检查配置和错误信息")
