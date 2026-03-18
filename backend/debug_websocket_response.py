#!/usr/bin/env python3
"""调试WebSocket响应数据"""

import os
import sys
import json
import asyncio
import websockets
import struct
from pathlib import Path

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

async def debug_websocket_response():
    """调试WebSocket响应"""
    print("=== 调试WebSocket响应数据 ===")
    
    # 配置信息
    app_id = config.VOLCENGINE_TTS_APP_ID
    access_token = config.VOLCENGINE_TTS_ACCESS_TOKEN
    resource_id = config.VOLCENGINE_TTS_RESOURCE_ID
    websocket_url = config.VOLCENGINE_TTS_WEBSOCKET_URL
    
    print(f"应用ID: {app_id}")
    print(f"资源ID: {resource_id}")
    print(f"WebSocket URL: {websocket_url}")
    
    # 构建连接头
    headers = {
        'X-Api-App-Key': app_id,
        'X-Api-Access-Key': access_token,
        'X-Api-Resource-Id': resource_id,
        'X-Api-Connect-Id': 'debug-connection-001'
    }
    
    print(f"连接头: {headers}")
    
    try:
        print("\n连接到WebSocket...")
        websocket = await websockets.connect(
            websocket_url,
            extra_headers=headers,
            ping_interval=30,
            ping_timeout=10
        )
        
        print("✅ WebSocket连接成功!")
        
        # 构建开始连接消息 - 使用简化的V3协议格式
        payload = json.dumps({
            "user": {"uid": "debug_user"},
            "event": 100,  # StartConnection
            "namespace": "BidirectionalTTS"
        }).encode('utf-8')
        
        # 使用简化的协议格式打包消息
        header = bytearray(4)
        header[0] = 0x12  # 协议版本1 + 头部大小2个4字节单位
        header[1] = 0x18  # 消息类型1 + 事件标志(bit3)
        header[2] = 0x10  # JSON序列化 + 无压缩
        header[3] = 0x00  # 保留字段
        
        # 构建完整消息: 固定头部 + 事件号 + payload长度 + payload
        message = bytearray()
        message.extend(header)
        message.extend(struct.pack('>I', 100))  # 事件号
        message.extend(struct.pack('>I', len(payload)))  # payload长度
        message.extend(payload)
        
        print(f"\n发送消息长度: {len(message)}")
        print(f"消息头部: {message[:12].hex()}")
        print(f"Payload: {payload.decode('utf-8')}")
        
        # 发送消息
        await websocket.send(bytes(message))
        print("✅ 消息发送成功!")
        
        # 接收响应
        print("\n等待响应...")
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)  # 10秒超时
        except asyncio.TimeoutError:
            print("❌ 等待响应超时（10秒）")
            print("可能的原因：")
            print("1. 协议格式不正确")
            print("2. 服务器未响应")
            print("3. 网络连接问题")
            await websocket.close()
            return
        
        print(f"✅ 接收到响应，长度: {len(response)}")
        print(f"响应数据 (hex): {response.hex()}")
        print(f"响应数据 (前50字节): {response[:50]}")
        
        # 尝试解析为文本
        try:
            text_response = response.decode('utf-8', errors='ignore')
            print(f"响应文本: {text_response[:200]}")
        except:
            print("无法解析为文本")
        
        # 尝试解析为JSON
        try:
            if response.startswith(b'{'):
                json_response = json.loads(response.decode('utf-8'))
                print(f"响应JSON: {json.dumps(json_response, indent=2, ensure_ascii=False)}")
        except:
            print("无法解析为JSON")
        
        # 分析二进制协议
        if len(response) >= 4:
            header = response[:4]
            print(f"\n二进制协议分析:")
            print(f"头部字节: {header.hex()}")
            print(f"第1字节 (0x{header[0]:02x}): 协议版本={(header[0]>>4)&0x0F}, 头部大小标志={header[0]&0x0F}")
            print(f"第2字节 (0x{header[1]:02x}): 消息类型={(header[1]>>4)&0x0F}, 标志位={header[1]&0x0F:04b}")
            print(f"第3字节 (0x{header[2]:02x}): 序列化={(header[2]>>4)&0x0F}, 压缩={header[2]&0x0F}")
            print(f"第4字节 (0x{header[3]:02x}): 保留/错误码={header[3]}")
            
            # 检查是否有事件号
            if header[1] & 0x04:
                if len(response) >= 8:
                    event = struct.unpack('>I', response[4:8])[0]
                    print(f"事件号: {event}")
                    
                    # 检查payload长度
                    if len(response) >= 12:
                        payload_size = struct.unpack('>I', response[8:12])[0]
                        print(f"Payload长度: {payload_size}")
                        
                        if len(response) >= 12 + payload_size:
                            payload = response[12:12+payload_size]
                            try:
                                payload_json = json.loads(payload.decode('utf-8'))
                                print(f"Payload JSON: {json.dumps(payload_json, indent=2, ensure_ascii=False)}")
                            except:
                                print(f"Payload (文本): {payload.decode('utf-8', errors='ignore')}")
        
        await websocket.close()
        print("\n✅ WebSocket连接已关闭")
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(debug_websocket_response())