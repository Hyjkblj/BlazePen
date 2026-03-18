"""测试Voice Design API调用"""
import os
import sys

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# 设置环境变量
os.environ['DASHSCOPE_API_KEY'] = 'sk-972acd8d4be44cd497bc396f38a6a088'
# Voice Design 音色仅支持此模型，且需 WebSocket 调用
os.environ['DASHSCOPE_TTS_MODEL'] = 'qwen3-tts-vd-realtime-2025-12-16'

try:
    import dashscope
    from dashscope import MultiModalConversation
    dashscope.api_key = os.environ['DASHSCOPE_API_KEY']
    dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'
    print("[信息] DashScope SDK已导入")
except ImportError as e:
    print(f"[错误] DashScope SDK未安装: {e}")
    print("[提示] 请运行: pip install dashscope>=1.25.2")
    sys.exit(1)


def test_voice_design_api():
    """测试Voice Design API（使用正确的API端点）"""
    print("=" * 60)
    print("测试Voice Design API")
    print("=" * 60)
    
    # 测试描述文本
    description = "温柔的女声，音调中等偏高，语速适中，带有甜美的感觉，适合年轻女性角色"
    preview_text = "你好，很高兴认识你。"
    
    print(f"\n[测试] Voice Design描述:")
    print(f"描述文本: {description}")
    print(f"长度: {len(description)} 字符")
    print(f"预览文本: {preview_text}")
    
    try:
        import requests
        
        # 使用正确的Voice Design API端点（根据DashScope官方文档）
        api_url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
        
        headers = {
            "Authorization": f"Bearer {os.environ['DASHSCOPE_API_KEY']}",
            "Content-Type": "application/json"
        }
        
        # 构建请求体（根据DashScope官方文档格式）
        data = {
            "model": "qwen-voice-design",  # 固定值
            "input": {
                "action": "create",  # 固定值
                "target_model": "qwen3-tts-vd-realtime-2025-12-16",  # 必须与后续TTS使用的模型一致
                "voice_prompt": description,
                "preview_text": preview_text,
                "preferred_name": "test_voice",  # 可选
                "language": "zh"  # 中文
            },
            "parameters": {
                "sample_rate": 24000,
                "response_format": "wav"
            }
        }
        
        print(f"\n[调用] 正在调用Voice Design API...")
        print(f"[URL] {api_url}")
        
        # 发送POST请求
        response = requests.post(
            api_url,
            headers=headers,
            json=data,
            timeout=60
        )
        
        print(f"\n[响应] HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"[响应] 响应内容: {result}")
            
            # 获取生成的voice_id
            if "output" in result and "voice" in result["output"]:
                voice_id = result["output"]["voice"]
                print(f"\n[成功] 音色创建成功！")
                print(f"[成功] voice_id: {voice_id}")
                
                # 保存预览音频
                if "preview_audio" in result["output"] and "data" in result["output"]["preview_audio"]:
                    import base64
                    preview_audio_data = result["output"]["preview_audio"]["data"]
                    audio_bytes = base64.b64decode(preview_audio_data)
                    
                    output_path = os.path.join(backend_dir, 'audio', 'cache', f'{voice_id}_preview.wav')
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(audio_bytes)
                    print(f"[成功] 预览音频已保存: {output_path}")
                
                return voice_id
            else:
                print(f"\n[错误] 响应中未找到voice字段")
                print(f"[调试] 完整响应: {result}")
                return None
        else:
            error_msg = response.text
            print(f"\n[错误] API调用失败: HTTP {response.status_code}")
            print(f"[错误] 错误信息: {error_msg}")
            return None
        
    except Exception as e:
        print(f"\n[错误] Voice Design API调用异常: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def test_tts_with_voice_id(voice_id: str = None):
    """测试使用voice_id进行TTS合成
    
    注意：Voice Design 生成的音色仅支持 qwen3-tts-vd-realtime-2025-12-16，
    且该模型需通过 WebSocket（QwenTtsRealtime）调用，HTTP MultiModalConversation 可能返回 403。
    此处先尝试 HTTP，若失败会提示使用 WebSocket。
    """
    print("\n" + "=" * 60)
    print("测试TTS合成（使用Voice Design生成的音色）")
    print("=" * 60)
    
    test_text = "你好，这是一个测试。"
    # 必须与 Voice Design 创建时的 target_model 一致（官方文档为 2025-12-16）
    vd_tts_model = 'qwen3-tts-vd-realtime-2025-12-16'
    
    print(f"\n[测试] TTS文本: {test_text}")
    print(f"[测试] 音色ID: {voice_id or '默认音色'}")
    print(f"[测试] 模型: {vd_tts_model}（需与创建音色时的 target_model 一致）")
    
    try:
        request_params = {
            'model': vd_tts_model,
            'text': test_text,
            'language_type': 'Chinese',
        }
        
        if voice_id:
            request_params['voice'] = voice_id
        
        print(f"\n[调用] 正在调用TTS API（HTTP）...")
        response = MultiModalConversation.call(**request_params)
        
        print(f"\n[响应] 状态码: {response.status_code}")
        
        if response.status_code == 200:
            print(f"[响应] 响应类型: {type(response)}")
            
            # 检查音频数据
            if hasattr(response, 'output'):
                print(f"[响应] output属性存在")
                if hasattr(response.output, 'audio'):
                    audio_data = response.output.audio
                    print(f"[成功] 音频数据已获取")
                    print(f"[信息] 音频数据类型: {type(audio_data)}")
                    print(f"[信息] 音频数据长度: {len(audio_data) if isinstance(audio_data, (str, bytes)) else 'N/A'}")
                    
                    # 保存音频文件
                    if isinstance(audio_data, str):
                        import base64
                        audio_bytes = base64.b64decode(audio_data)
                    else:
                        audio_bytes = audio_data
                    
                    output_path = os.path.join(backend_dir, 'audio', 'cache', 'test_output.wav')
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, 'wb') as f:
                        f.write(audio_bytes)
                    print(f"[成功] 音频已保存: {output_path}")
                    return True
                else:
                    print(f"[警告] output中未找到audio属性")
                    print(f"[调试] output的所有属性: {dir(response.output)}")
            else:
                print(f"[警告] 响应中没有output属性")
                print(f"[调试] 响应的所有属性: {dir(response)}")
        else:
            error_msg = getattr(response, 'message', f"状态码: {response.status_code}")
            print(f"\n[错误] TTS API调用失败: {error_msg}")
            if response.status_code == 403:
                print("\n[说明] 使用 Voice Design 音色进行合成时，需通过 WebSocket 接口（QwenTtsRealtime）调用，")
                print("        HTTP MultiModalConversation 可能返回 403。请参考文档实现 WebSocket 客户端。")
            return False
        
        return False
        
    except Exception as e:
        print(f"\n[错误] TTS API调用异常: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def test_basic_tts():
    """测试基础TTS（不使用Voice Design）"""
    print("\n" + "=" * 60)
    print("测试基础TTS（使用预设音色）")
    print("=" * 60)
    
    test_text = "你好，这是一个基础TTS测试。"
    
    print(f"\n[测试] TTS文本: {test_text}")
    
    try:
        # 先尝试使用qwen3-tts-flash（非realtime版本）
        print(f"\n[尝试1] 使用模型: qwen3-tts-flash")
        response = MultiModalConversation.call(
            model='qwen3-tts-flash',
            text=test_text,
            voice='Cherry',  # 添加voice参数
            language_type='Chinese'
        )
        
        if response.status_code != 200:
            print(f"[尝试1失败] 状态码: {response.status_code}, 错误: {response.message}")
            # 尝试不使用voice参数
            print(f"\n[尝试2] 使用模型: qwen3-tts-flash（不指定voice）")
            response = MultiModalConversation.call(
                model='qwen3-tts-flash',
                text=test_text,
                language_type='Chinese'
            )
        
        print(f"\n[响应] 状态码: {response.status_code}")
        
        if response.status_code == 200:
            if hasattr(response, 'output') and hasattr(response.output, 'audio'):
                audio_data = response.output.audio
                print(f"[成功] 音频数据已获取")
                
                # 保存音频文件
                if isinstance(audio_data, str):
                    import base64
                    audio_bytes = base64.b64decode(audio_data)
                else:
                    audio_bytes = audio_data
                
                output_path = os.path.join(backend_dir, 'audio', 'cache', 'test_basic.wav')
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(audio_bytes)
                print(f"[成功] 音频已保存: {output_path}")
                return True
        else:
            error_msg = getattr(response, 'message', f"状态码: {response.status_code}")
            print(f"\n[错误] TTS API调用失败: {error_msg}")
            return False
        
    except Exception as e:
        print(f"\n[错误] TTS API调用异常: {e}")
        import traceback
        print(traceback.format_exc())
        return False


if __name__ == '__main__':
    print("\n开始测试DashScope TTS和Voice Design API...\n")
    
    # 测试1: 基础TTS
    print("\n" + "=" * 60)
    print("测试1: 基础TTS（不使用Voice Design）")
    print("=" * 60)
    test_basic_tts()
    
    # 测试2: Voice Design API
    print("\n" + "=" * 60)
    print("测试2: Voice Design API")
    print("=" * 60)
    voice_id = test_voice_design_api()
    
    # 测试3: 使用Voice Design生成的音色进行TTS
    if voice_id:
        print("\n" + "=" * 60)
        print("测试3: 使用Voice Design生成的音色进行TTS")
        print("=" * 60)
        test_tts_with_voice_id(voice_id)
    else:
        print("\n[跳过] Voice Design未返回voice_id，跳过测试3")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print("\n请检查:")
    print("1. 控制台输出的响应信息")
    print("2. backend/audio/cache/ 目录下的音频文件")
    print("3. 如果出现错误，请检查API密钥和模型名称是否正确")
