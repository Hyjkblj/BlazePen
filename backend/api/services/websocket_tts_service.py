"""火山引擎双向流式WebSocket TTS服务"""
import os
import json
import time
import uuid
import struct
import asyncio
import websockets
import hashlib
from typing import Optional, Dict, Any, List, AsyncGenerator
from pathlib import Path
import sys
import base64

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config
from utils.logger import get_logger

logger = get_logger(__name__)

# 尝试导入websockets
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    logger.warning("websockets未安装，WebSocket TTS功能将不可用。请运行: pip install websockets")


class WebSocketTTSService:
    """火山引擎双向流式WebSocket TTS服务"""
    
    def __init__(self):
        """初始化WebSocket TTS服务"""
        self.provider = 'volcengine_websocket'
        self.cache_dir = Path(backend_dir) / 'audio' / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 火山引擎WebSocket TTS配置
        self.app_id = config.VOLCENGINE_TTS_APP_ID
        self.access_token = config.VOLCENGINE_TTS_ACCESS_TOKEN
        self.secret_key = config.VOLCENGINE_TTS_SECRET_KEY
        self.resource_id = config.VOLCENGINE_TTS_RESOURCE_ID
        self.websocket_url = config.VOLCENGINE_TTS_WEBSOCKET_URL
        
        # TTS模型配置
        self.tts_model = config.VOLCENGINE_TTS_MODEL
        self.enable_timestamp = config.VOLCENGINE_TTS_ENABLE_TIMESTAMP
        self.enable_cache = config.VOLCENGINE_TTS_ENABLE_CACHE
        self.enable_emotion = config.VOLCENGINE_TTS_ENABLE_EMOTION
        
        # WebSocket连接管理
        self.websocket = None
        self.connection_id = None
        self.session_id = None
        
        # 检查可用性
        if WEBSOCKETS_AVAILABLE and self.app_id and self.access_token:
            self.enabled = True
            logger.info(f"WebSocket TTS服务已启用 - 提供商: 火山引擎(Doubao), 模型: {self.tts_model}")
        else:
            self.enabled = False
            if not WEBSOCKETS_AVAILABLE:
                logger.warning("websockets未安装，WebSocket TTS功能不可用")
            elif not self.app_id:
                logger.warning("未配置 VOLCENGINE_TTS_APP_ID，WebSocket TTS功能不可用")
            elif not self.access_token:
                logger.warning("未配置 VOLCENGINE_TTS_ACCESS_TOKEN，WebSocket TTS功能不可用")
    
    def _generate_connection_id(self) -> str:
        """生成连接ID"""
        return str(uuid.uuid4())
    
    def _generate_session_id(self) -> str:
        """生成会话ID"""
        return str(uuid.uuid4())
    
    def _build_websocket_headers(self) -> Dict[str, str]:
        """构建WebSocket连接头"""
        return {
            'X-Api-App-Key': self.app_id,
            'X-Api-Access-Key': self.access_token,
            'X-Api-Resource-Id': self.resource_id,  # 使用配置的资源ID
            'X-Api-Connect-Id': self.connection_id,
            'X-Control-Require-Usage-Tokens-Return': '*'
        }
    
    def _pack_message(self, message_type: int, event: Optional[int] = None, 
                     payload: bytes = b'', serialization: int = 1, compression: int = 0) -> bytes:
        """打包WebSocket二进制消息 - 火山引擎V3协议"""
        
        # 构建4字节固定头部
        header = bytearray(4)
        
        # 第1字节: 协议版本(高4位) + 头部大小标志(低4位)
        if event is not None:
            header[0] = 0x12  # 协议版本1 + 头部大小2个4字节单位(包含事件号)
        else:
            header[0] = 0x11  # 协议版本1 + 头部大小1个4字节单位(仅固定头部)
        
        # 第2字节: 消息类型(高4位) + 可选字段标志(低4位)
        header[1] = message_type << 4  # 消息类型
        if event is not None:
            header[1] |= 0x08  # bit 3: 包含事件号
        
        # 第3字节: 序列化方法(高4位) + 压缩方法(低4位)
        header[2] = (serialization << 4) | compression
        
        # 第4字节: 保留字段
        header[3] = 0x00
        
        # 构建完整消息
        message = bytearray()
        message.extend(header)
        
        # 添加事件号（如果有）
        if event is not None:
            message.extend(struct.pack('>I', event))  # 大端序4字节事件号
        
        # 添加payload长度和payload
        message.extend(struct.pack('>I', len(payload)))  # 大端序payload长度
        message.extend(payload)
        
        return bytes(message)
    
    def _build_start_connection_message(self) -> bytes:
        """构建开始连接消息"""
        payload = json.dumps({
            "user": {"uid": "user_001"},
            "event": 100,  # StartConnection
            "namespace": "BidirectionalTTS"
        }).encode('utf-8')
        
        return self._pack_message(
            message_type=1, 
            event=100, 
            payload=payload
        )
    
    def _build_start_session_message(self, speaker: str, audio_params: Dict[str, Any], 
                                   additions: Optional[Dict[str, Any]] = None) -> bytes:
        """构建开始会话消息"""
        req_params = {
            "text": "",  # 初始为空，后续通过TaskRequest发送
            "speaker": speaker,
            "audio_params": audio_params
        }
        
        # 添加模型参数
        if self.tts_model:
            req_params["model"] = self.tts_model
        
        # 添加高级参数
        if additions:
            req_params["additions"] = additions
        
        payload = json.dumps({
            "user": {"uid": "user_001"},
            "event": 110,  # StartSession
            "namespace": "BidirectionalTTS",
            "req_params": req_params
        }).encode('utf-8')
        
        return self._pack_message(
            message_type=1, 
            event=110, 
            payload=payload
        )
    
    def _build_task_request_message(self, text: str) -> bytes:
        """构建任务请求消息"""
        payload = json.dumps({
            "user": {"uid": "user_001"},
            "event": 120,  # TaskRequest
            "namespace": "BidirectionalTTS",
            "req_params": {"text": text}
        }).encode('utf-8')
        
        return self._pack_message(
            message_type=1, 
            event=120, 
            payload=payload
        )
    
    def _build_finish_session_message(self) -> bytes:
        """构建结束会话消息"""
        payload = json.dumps({
            "user": {"uid": "user_001"},
            "event": 130,  # FinishSession
            "namespace": "BidirectionalTTS"
        }).encode('utf-8')
        
        return self._pack_message(
            message_type=1, 
            event=130, 
            payload=payload
        )
    
    def _build_finish_connection_message(self) -> bytes:
        """构建结束连接消息"""
        payload = json.dumps({
            "user": {"uid": "user_001"},
            "event": 140,  # FinishConnection
            "namespace": "BidirectionalTTS"
        }).encode('utf-8')
        
        return self._pack_message(
            message_type=1, 
            event=140, 
            payload=payload
        )
    
    def _parse_response_message(self, data: bytes) -> Dict[str, Any]:
        """解析响应消息"""
        if len(data) < 4:
            return {"error": "消息太短", "raw_data": data.hex()}
        
        try:
            # 打印原始数据用于调试
            logger.debug(f"接收到数据长度: {len(data)}, 前20字节: {data[:20].hex()}")
            
            # 解析头部 - 根据火山引擎V3协议
            header = data[:4]
            protocol_version = (header[0] >> 4) & 0x0F
            header_size_flag = header[0] & 0x0F
            message_type = (header[1] >> 4) & 0x0F
            has_event = (header[1] & 0x04) != 0
            has_connect_id = (header[1] & 0x02) != 0
            has_session_id = (header[1] & 0x01) != 0
            serialization = (header[2] >> 4) & 0x0F
            compression = header[2] & 0x0F
            error_code = header[3] if message_type == 15 else 0  # 错误消息类型
            
            logger.debug(f"协议版本: {protocol_version}, 消息类型: {message_type}, 有事件: {has_event}")
            logger.debug(f"序列化: {serialization}, 压缩: {compression}, 错误码: {error_code}")
            
            offset = 4
            event = None
            connect_id = None
            session_id = None
            
            # 解析可选字段
            if has_event and len(data) >= offset + 4:
                event = struct.unpack('>I', data[offset:offset+4])[0]
                offset += 4
                logger.debug(f"事件号: {event}")
            
            if has_connect_id:
                if len(data) >= offset + 1:
                    connect_id_size = data[offset]
                    offset += 1
                    if len(data) >= offset + connect_id_size:
                        connect_id = data[offset:offset+connect_id_size].decode('utf-8', errors='ignore')
                        offset += connect_id_size
                        logger.debug(f"连接ID: {connect_id}")
            
            if has_session_id:
                if len(data) >= offset + 1:
                    session_id_size = data[offset]
                    offset += 1
                    if len(data) >= offset + session_id_size:
                        session_id = data[offset:offset+session_id_size].decode('utf-8', errors='ignore')
                        offset += session_id_size
                        logger.debug(f"会话ID: {session_id}")
            
            # 解析payload长度
            if len(data) < offset + 4:
                return {"error": "无法解析payload长度", "data_length": len(data), "offset": offset}
            
            payload_size = struct.unpack('>I', data[offset:offset+4])[0]
            offset += 4
            
            logger.debug(f"Payload大小: {payload_size}, 剩余数据: {len(data) - offset}")
            
            # 检查payload长度是否合理
            if payload_size > len(data) - offset:
                # 可能是协议解析错误，尝试直接解析为JSON错误响应
                try:
                    error_text = data[4:].decode('utf-8', errors='ignore')
                    logger.debug(f"尝试解析为错误文本: {error_text[:200]}")
                    if error_text.startswith('{'):
                        error_json = json.loads(error_text)
                        return {"error": "服务器错误", "server_error": error_json, "raw_data": data[:50].hex()}
                except:
                    pass
                
                return {
                    "error": f"payload长度异常: {payload_size}, 可用数据: {len(data) - offset}",
                    "data_length": len(data),
                    "raw_data": data[:50].hex()
                }
            
            # 解析payload
            payload = data[offset:offset+payload_size]
            
            result = {
                "message_type": message_type,
                "event": event,
                "connect_id": connect_id,
                "session_id": session_id,
                "serialization": serialization,
                "compression": compression,
                "payload_size": payload_size,
                "error_code": error_code
            }
            
            # 根据序列化方式解析payload
            if serialization == 1:  # JSON
                try:
                    result["payload"] = json.loads(payload.decode('utf-8'))
                except Exception as e:
                    result["payload"] = payload.decode('utf-8', errors='ignore')
                    result["parse_error"] = str(e)
            elif serialization == 0:  # Raw (音频数据)
                result["payload"] = payload
            else:
                result["payload"] = payload
            
            return result
            
        except Exception as e:
            return {
                "error": f"解析异常: {e}",
                "data_length": len(data),
                "raw_data": data[:50].hex()
            }
    
    async def connect(self) -> bool:
        """建立WebSocket连接"""
        if not self.enabled:
            return False
        
        try:
            self.connection_id = self._generate_connection_id()
            headers = self._build_websocket_headers()
            
            logger.info(f"连接到: {self.websocket_url}")
            logger.debug(f"连接ID: {self.connection_id}")
            
            self.websocket = await websockets.connect(
                self.websocket_url,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10
            )
            
            # 发送开始连接消息
            start_conn_msg = self._build_start_connection_message()
            await self.websocket.send(start_conn_msg)
            
            # 等待连接确认
            response = await self.websocket.recv()
            parsed = self._parse_response_message(response)
            
            if parsed.get("event") == 101:  # ConnectionStarted
                logger.info("连接建立成功")
                return True
            else:
                logger.error(f"连接失败: {parsed}")
                return False
                
        except Exception as e:
            logger.error(f"连接错误: {e}", exc_info=True)
            return False
    
    async def disconnect(self):
        """断开WebSocket连接"""
        if self.websocket:
            try:
                # 发送结束连接消息
                finish_conn_msg = self._build_finish_connection_message()
                await self.websocket.send(finish_conn_msg)
                
                # 等待连接结束确认
                response = await self.websocket.recv()
                parsed = self._parse_response_message(response)
                
                if parsed.get("event") == 141:  # ConnectionFinished
                    logger.info("连接已断开")
                
                await self.websocket.close()
            except Exception as e:
                logger.error(f"断开连接错误: {e}", exc_info=True)
            finally:
                self.websocket = None
                self.connection_id = None
                self.session_id = None
    
    async def generate_speech_stream(self, text: str, speaker: str = "BV001_streaming",
                                   audio_params: Optional[Dict[str, Any]] = None,
                                   emotion_params: Optional[Dict[str, Any]] = None,
                                   mix_speakers: Optional[List[Dict[str, Any]]] = None) -> AsyncGenerator[bytes, None]:
        """流式生成语音"""
        if not self.websocket:
            raise RuntimeError("WebSocket连接未建立")
        
        # 默认音频参数
        if audio_params is None:
            audio_params = {
                "format": "wav",
                "sample_rate": 24000,
                "bit_rate": 64000
            }
        
        # 构建高级参数
        additions = {}
        if self.enable_cache:
            additions["cache_config"] = {
                "text_type": 1,
                "use_cache": True,
                "use_segment_cache": True
            }
        
        if self.enable_timestamp:
            additions["enable_timestamp"] = True
        
        if emotion_params:
            if "emotion" in emotion_params:
                audio_params["emotion"] = emotion_params["emotion"]
            if "emotion_scale" in emotion_params:
                audio_params["emotion_scale"] = emotion_params["emotion_scale"]
            if "speech_rate" in emotion_params:
                audio_params["speech_rate"] = emotion_params["speech_rate"]
            if "loudness_rate" in emotion_params:
                audio_params["loudness_rate"] = emotion_params["loudness_rate"]
        
        # 混音配置
        req_speaker = speaker
        if mix_speakers:
            req_speaker = "custom_mix_bigtts"
            additions["mix_speaker"] = {"speakers": mix_speakers}
        
        try:
            self.session_id = self._generate_session_id()
            
            # 开始会话
            start_session_msg = self._build_start_session_message(req_speaker, audio_params, additions)
            await self.websocket.send(start_session_msg)
            
            # 等待会话开始确认
            response = await self.websocket.recv()
            parsed = self._parse_response_message(response)
            
            if parsed.get("event") != 111:  # SessionStarted
                raise RuntimeError(f"会话开始失败: {parsed}")
            
            logger.info(f"会话开始成功: {self.session_id}")
            
            # 发送文本请求
            task_msg = self._build_task_request_message(text)
            await self.websocket.send(task_msg)
            
            # 接收音频数据
            audio_chunks = []
            while True:
                response = await self.websocket.recv()
                parsed = self._parse_response_message(response)
                
                event = parsed.get("event")
                
                if event == 150:  # AudioData
                    # 音频数据
                    audio_data = parsed.get("payload")
                    if isinstance(audio_data, bytes):
                        audio_chunks.append(audio_data)
                        yield audio_data
                    
                elif event == 151:  # TaskFinished
                    logger.info("任务完成")
                    break
                    
                elif event == 152:  # SessionFinished
                    logger.info("会话结束")
                    break
                    
                elif event >= 200:  # 错误事件
                    error_msg = parsed.get("payload", {}).get("message", "未知错误")
                    raise RuntimeError(f"TTS错误 (事件{event}): {error_msg}")
            
            # 结束会话
            finish_session_msg = self._build_finish_session_message()
            await self.websocket.send(finish_session_msg)
            
        except Exception as e:
            logger.error(f"生成语音错误: {e}", exc_info=True)
            raise
    
    async def generate_speech(self, text: str, character_id: int = 1,
                            speaker: str = "BV001_streaming",
                            audio_params: Optional[Dict[str, Any]] = None,
                            emotion_params: Optional[Dict[str, Any]] = None,
                            mix_speakers: Optional[List[Dict[str, Any]]] = None,
                            use_cache: bool = True) -> Dict[str, Any]:
        """生成语音（非流式）"""
        # 生成缓存键
        cache_key = self._generate_cache_key(text, character_id, speaker, emotion_params, mix_speakers)
        cache_path = self.cache_dir / f"{cache_key}.wav"
        
        # 检查缓存
        if use_cache and cache_path.exists():
            return {
                'audio_url': f'/static/audio/cache/{cache_key}.wav',
                'audio_path': str(cache_path),
                'cached': True,
                'duration': self._get_audio_duration(cache_path)
            }
        
        # 确保连接
        if not self.websocket:
            connected = await self.connect()
            if not connected:
                raise RuntimeError("无法建立WebSocket连接")
        
        try:
            # 收集所有音频数据
            audio_data = b''
            async for chunk in self.generate_speech_stream(text, speaker, audio_params, emotion_params, mix_speakers):
                audio_data += chunk
            
            if not audio_data:
                raise ValueError("TTS 未返回音频数据")
            
            # 保存到缓存
            cache_path.write_bytes(audio_data)
            
            return {
                'audio_url': f'/static/audio/cache/{cache_key}.wav',
                'audio_path': str(cache_path),
                'duration': self._get_audio_duration(cache_path),
                'cached': False
            }
            
        except Exception as e:
            logger.error(f"生成语音失败: {e}", exc_info=True)
            raise
    
    def _generate_cache_key(self, text: str, character_id: int, speaker: str,
                          emotion_params: Optional[Dict[str, Any]] = None,
                          mix_speakers: Optional[List[Dict[str, Any]]] = None) -> str:
        """生成缓存键"""
        key_data = {
            'text': text,
            'character_id': character_id,
            'speaker': speaker,
            'emotion_params': emotion_params or {},
            'mix_speakers': mix_speakers or [],
            'model': self.tts_model
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频时长（秒）"""
        try:
            # 使用pydub获取音频时长
            from pydub import AudioSegment
            audio = AudioSegment.from_file(str(audio_path))
            return len(audio) / 1000.0  # 转换为秒
        except ImportError:
            logger.warning("pydub未安装，无法获取音频时长")
            return 0.0
        except Exception as e:
            logger.warning(f"获取音频时长失败: {e}", exc_info=True)
            return 0.0
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.disconnect()


# 同步包装器，用于兼容现有接口
class WebSocketTTSServiceSync:
    """WebSocket TTS服务的同步包装器"""
    
    def __init__(self):
        self.async_service = WebSocketTTSService()
        self.enabled = self.async_service.enabled
    
    def generate_speech(self, text: str, character_id: int = 1,
                       override_voice_id: Optional[str] = None,
                       emotion_params: Optional[Dict[str, Any]] = None,
                       use_cache: bool = True) -> Dict[str, Any]:
        """生成语音（同步接口）"""
        if not self.enabled:
            raise ValueError("WebSocket TTS服务未启用，请检查配置")
        
        # 解析音色ID
        speaker = override_voice_id or "BV001_streaming"
        
        # 运行异步方法
        return asyncio.run(self._generate_speech_async(
            text, character_id, speaker, emotion_params, use_cache
        ))
    
    async def _generate_speech_async(self, text: str, character_id: int, speaker: str,
                                   emotion_params: Optional[Dict[str, Any]], use_cache: bool) -> Dict[str, Any]:
        """异步生成语音"""
        async with self.async_service as service:
            return await service.generate_speech(
                text=text,
                character_id=character_id,
                speaker=speaker,
                emotion_params=emotion_params,
                use_cache=use_cache
            )