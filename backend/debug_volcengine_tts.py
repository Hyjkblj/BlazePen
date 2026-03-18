#!/usr/bin/env python3
"""火山引擎 TTS 调试脚本"""

import os
import sys
import json
import requests
from pathlib import Path

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

def test_api_connectivity():
    """测试API连通性"""
    print("=== API连通性测试 ===")
    
    try:
        # 测试基本网络连接
        response = requests.get("https://openspeech.bytedance.com", timeout=10)
        print(f"✅ 网络连接正常: {response.status_code}")
    except Exception as e:
        print(f"❌ 网络连接失败: {e}")
        return False
    
    return True

def test_different_resource_ids():
    """测试不同的资源ID"""
    print("\n=== 资源ID测试 ===")
    
    # 常见的资源ID格式
    resource_ids = [
        "volc.tts.default",
        "volc.service_type.10029", 
        "volc.tts.streaming",
        "volc.tts.bigtts",
        "volc.tts.seed",
        "volc.tts.seed-tts-2.0",
        "volc.tts.doubao",
        "volc.tts.doubao-streaming"
    ]
    
    for resource_id in resource_ids:
        print(f"\n🔍 测试资源ID: {resource_id}")
        result = test_tts_with_resource_id(resource_id)
        if result:
            print(f"✅ 资源ID {resource_id} 可用")
            return resource_id
        else:
            print(f"❌ 资源ID {resource_id} 不可用")
    
    return None

def test_tts_with_resource_id(resource_id: str) -> bool:
    """使用指定资源ID测试TTS"""
    
    # 构建请求参数
    request_data = {
        "app": {
            "appid": config.VOLCENGINE_TTS_APP_ID,
            "token": config.VOLCENGINE_TTS_ACCESS_TOKEN,
            "cluster": "volcano_tts"
        },
        "user": {
            "uid": "debug_user"
        },
        "audio": {
            "voice_type": "BV001_streaming",
            "encoding": "wav",
            "speed_ratio": 1.0,
            "volume_ratio": 1.0,
            "pitch_ratio": 1.0
        },
        "request": {
            "reqid": f"debug_test_{resource_id.replace('.', '_')}",
            "text": "测试",
            "text_type": "plain",
            "operation": "query"
        }
    }
    
    # 构建请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer; {config.VOLCENGINE_TTS_ACCESS_TOKEN}",
        "X-Resource-Id": resource_id
    }
    
    try:
        response = requests.post(
            "https://openspeech.bytedance.com/api/v1/tts",
            headers=headers,
            json=request_data,
            timeout=10
        )
        
        print(f"   响应状态: {response.status_code}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                if response_data.get('code') == 3000:
                    print(f"   ✅ 成功: {response_data.get('message', '无消息')}")
                    return True
                else:
                    print(f"   ❌ API错误: {response_data.get('message', '未知错误')}")
            except:
                print(f"   ❌ 响应解析失败")
        else:
            try:
                error_data = response.json()
                print(f"   ❌ HTTP错误: {error_data.get('message', '未知错误')}")
            except:
                print(f"   ❌ HTTP错误: {response.text[:200]}")
        
        return False
        
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
        return False

def test_different_endpoints():
    """测试不同的API端点"""
    print("\n=== API端点测试 ===")
    
    endpoints = [
        "https://openspeech.bytedance.com/api/v1/tts",
        "https://openspeech.bytedance.com/api/v2/tts", 
        "https://openspeech.bytedance.com/api/v3/tts",
        "https://tts-api.volcengineapi.com/api/v1/tts",
        "https://speech.volcengineapi.com/api/v1/tts"
    ]
    
    for endpoint in endpoints:
        print(f"\n🔍 测试端点: {endpoint}")
        result = test_endpoint(endpoint)
        if result:
            print(f"✅ 端点 {endpoint} 可用")
            return endpoint
        else:
            print(f"❌ 端点 {endpoint} 不可用")
    
    return None

def test_endpoint(endpoint: str) -> bool:
    """测试指定端点"""
    
    request_data = {
        "app": {
            "appid": config.VOLCENGINE_TTS_APP_ID,
            "token": config.VOLCENGINE_TTS_ACCESS_TOKEN,
            "cluster": "volcano_tts"
        },
        "user": {
            "uid": "debug_user"
        },
        "audio": {
            "voice_type": "BV001_streaming",
            "encoding": "wav"
        },
        "request": {
            "reqid": "debug_endpoint_test",
            "text": "测试",
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
        response = requests.post(endpoint, headers=headers, json=request_data, timeout=10)
        print(f"   响应状态: {response.status_code}")
        
        if response.status_code in [200, 400, 403]:  # 至少能连接到服务器
            return True
        else:
            return False
            
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        return False

def test_auth_formats():
    """测试不同的认证格式"""
    print("\n=== 认证格式测试 ===")
    
    auth_formats = [
        f"Bearer; {config.VOLCENGINE_TTS_ACCESS_TOKEN}",
        f"Bearer {config.VOLCENGINE_TTS_ACCESS_TOKEN}",
        f"Token {config.VOLCENGINE_TTS_ACCESS_TOKEN}",
        config.VOLCENGINE_TTS_ACCESS_TOKEN
    ]
    
    for auth_format in auth_formats:
        print(f"\n🔍 测试认证格式: {auth_format[:20]}...")
        result = test_auth_format(auth_format)
        if result:
            print(f"✅ 认证格式可用")
            return auth_format
        else:
            print(f"❌ 认证格式不可用")
    
    return None

def test_auth_format(auth_format: str) -> bool:
    """测试指定认证格式"""
    
    request_data = {
        "app": {
            "appid": config.VOLCENGINE_TTS_APP_ID,
            "token": config.VOLCENGINE_TTS_ACCESS_TOKEN,
            "cluster": "volcano_tts"
        },
        "user": {
            "uid": "debug_user"
        },
        "audio": {
            "voice_type": "BV001_streaming",
            "encoding": "wav"
        },
        "request": {
            "reqid": "debug_auth_test",
            "text": "测试",
            "text_type": "plain",
            "operation": "query"
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_format,
        "X-Resource-Id": "volc.tts.default"
    }
    
    try:
        response = requests.post(
            "https://openspeech.bytedance.com/api/v1/tts",
            headers=headers,
            json=request_data,
            timeout=10
        )
        
        print(f"   响应状态: {response.status_code}")
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                if response_data.get('code') == 3000:
                    return True
            except:
                pass
        
        # 检查是否是认证问题还是其他问题
        if response.status_code == 401:
            print(f"   ❌ 认证失败")
        elif response.status_code == 403:
            print(f"   ⚠️  认证通过但权限不足")
            return True  # 认证格式是对的，只是权限问题
        
        return False
        
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
        return False

def print_config_info():
    """打印配置信息"""
    print("=== 配置信息 ===")
    print(f"应用ID: {config.VOLCENGINE_TTS_APP_ID}")
    print(f"访问令牌: {config.VOLCENGINE_TTS_ACCESS_TOKEN[:8]}...{config.VOLCENGINE_TTS_ACCESS_TOKEN[-8:] if len(config.VOLCENGINE_TTS_ACCESS_TOKEN) > 16 else '***'}")
    print(f"密钥: {config.VOLCENGINE_TTS_SECRET_KEY[:8]}...{config.VOLCENGINE_TTS_SECRET_KEY[-8:] if len(config.VOLCENGINE_TTS_SECRET_KEY) > 16 else '***'}")
    print(f"区域: {config.VOLCENGINE_REGION}")
    print(f"TTS模型: {config.VOLCENGINE_TTS_MODEL}")
    print(f"资源ID: {config.VOLCENGINE_TTS_RESOURCE_ID}")

def main():
    """主函数"""
    print("🔍 火山引擎 TTS 调试工具")
    print("=" * 50)
    
    # 打印配置信息
    print_config_info()
    
    # 测试网络连接
    if not test_api_connectivity():
        print("❌ 网络连接失败，无法继续测试")
        return
    
    # 测试不同的认证格式
    working_auth = test_auth_formats()
    
    # 测试不同的API端点
    working_endpoint = test_different_endpoints()
    
    # 测试不同的资源ID
    working_resource_id = test_different_resource_ids()
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 调试结果总结:")
    
    if working_auth:
        print(f"✅ 可用的认证格式: {working_auth[:30]}...")
    else:
        print("❌ 没有找到可用的认证格式")
    
    if working_endpoint:
        print(f"✅ 可用的API端点: {working_endpoint}")
    else:
        print("❌ 没有找到可用的API端点")
    
    if working_resource_id:
        print(f"✅ 可用的资源ID: {working_resource_id}")
    else:
        print("❌ 没有找到可用的资源ID")
    
    # 建议
    print("\n💡 建议:")
    if not working_auth and not working_endpoint and not working_resource_id:
        print("   1. 检查火山引擎账户是否已开通TTS服务")
        print("   2. 确认Access Token是否正确且未过期")
        print("   3. 确认应用ID是否正确")
        print("   4. 联系火山引擎技术支持获取正确的API配置")
    else:
        print("   1. 使用上述找到的可用配置更新config.py")
        print("   2. 重新测试TTS功能")

if __name__ == "__main__":
    main()