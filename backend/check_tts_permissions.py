#!/usr/bin/env python3
"""火山引擎 TTS 权限检查脚本"""

import os
import sys
import requests
import json

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

def check_permissions():
    """检查TTS权限"""
    print("🔍 火山引擎 TTS 权限检查")
    print("=" * 40)
    
    # 配置信息
    print("📋 配置信息:")
    print(f"   应用ID: {config.VOLCENGINE_TTS_APP_ID}")
    print(f"   访问令牌: {config.VOLCENGINE_TTS_ACCESS_TOKEN[:8]}...{config.VOLCENGINE_TTS_ACCESS_TOKEN[-4:]}")
    print(f"   区域: {config.VOLCENGINE_REGION}")
    print()
    
    # 测试基本连接
    print("🌐 网络连接测试:")
    try:
        response = requests.get("https://openspeech.bytedance.com", timeout=5)
        print(f"   ✅ 网络连接正常 (状态: {response.status_code})")
    except Exception as e:
        print(f"   ❌ 网络连接失败: {e}")
        return False
    
    # 测试TTS权限
    print("\n🔐 TTS权限测试:")
    
    # 构建测试请求
    request_data = {
        "app": {
            "appid": config.VOLCENGINE_TTS_APP_ID,
            "token": config.VOLCENGINE_TTS_ACCESS_TOKEN,
            "cluster": "volcano_tts"
        },
        "user": {
            "uid": "permission_test"
        },
        "audio": {
            "voice_type": "BV001_streaming",
            "encoding": "wav"
        },
        "request": {
            "reqid": "permission_check_001",
            "text": "权限测试",
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
        response = requests.post(
            "https://openspeech.bytedance.com/api/v1/tts",
            headers=headers,
            json=request_data,
            timeout=10
        )
        
        print(f"   HTTP状态: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('code') == 3000:
                    print("   ✅ TTS权限正常！服务可用")
                    return True
                else:
                    print(f"   ❌ TTS API错误: {data.get('message', '未知错误')}")
            except:
                print("   ❌ 响应解析失败")
        elif response.status_code == 403:
            try:
                error_data = response.json()
                error_msg = error_data.get('message', '')
                print(f"   ❌ 权限不足: {error_msg}")
                
                if 'resource not granted' in error_msg:
                    print("\n💡 解决建议:")
                    print("   1. 登录火山引擎控制台: https://console.volcengine.com/")
                    print("   2. 进入 '语音技术' -> '语音合成'")
                    print("   3. 确认服务已开通且有可用配额")
                    print("   4. 检查资源权限设置")
                    print("   5. 如需要，联系技术支持申请TTS服务权限")
                
            except:
                print(f"   ❌ 权限错误: {response.text[:100]}")
        elif response.status_code == 401:
            print("   ❌ 认证失败: 请检查Access Token是否正确")
        else:
            print(f"   ❌ 未知错误: HTTP {response.status_code}")
            print(f"   响应: {response.text[:200]}")
        
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
    
    return False

def main():
    """主函数"""
    success = check_permissions()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 权限检查通过！可以使用火山引擎TTS服务")
        print("\n下一步:")
        print("   运行: python test_doubao_tts.py")
    else:
        print("⚠️  权限检查失败，需要解决权限问题")
        print("\n建议:")
        print("   1. 按照上述建议检查控制台设置")
        print("   2. 权限问题解决后重新运行此脚本")
        print("   3. 如果问题持续，考虑使用备用TTS方案")

if __name__ == "__main__":
    main()