#!/usr/bin/env python3
"""火山引擎 TTS 设置诊断脚本"""

import os
import sys
import requests
import json

# 添加backend目录到路径
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import config

def test_different_apis():
    """测试不同的API接口"""
    print("🔍 测试不同的API接口")
    print("=" * 40)
    
    # 测试不同的API路径
    api_paths = [
        "/api/v1/tts",
        "/api/v2/tts", 
        "/api/v3/tts",
        "/api/v1/tts/submit",
        "/api/v1/tts/query",
        "/tts/v1/submit",
        "/tts/v1/query"
    ]
    
    base_url = "https://openspeech.bytedance.com"
    
    for path in api_paths:
        print(f"\n🔍 测试路径: {path}")
        test_api_path(base_url + path)

def test_api_path(url):
    """测试特定API路径"""
    request_data = {
        "app": {
            "appid": config.VOLCENGINE_TTS_APP_ID,
            "token": config.VOLCENGINE_TTS_ACCESS_TOKEN,
            "cluster": "volcano_tts"
        },
        "user": {
            "uid": "test_user"
        },
        "audio": {
            "voice_type": "BV001_streaming",
            "encoding": "wav"
        },
        "request": {
            "reqid": "diagnose_test",
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
        response = requests.post(url, headers=headers, json=request_data, timeout=5)
        print(f"   状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ 成功响应")
            try:
                data = response.json()
                print(f"   响应: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}...")
            except:
                print(f"   响应: {response.text[:100]}...")
        elif response.status_code == 404:
            print("   ❌ 路径不存在")
        elif response.status_code == 403:
            print("   ⚠️  路径存在但权限不足")
            try:
                error_data = response.json()
                print(f"   错误: {error_data.get('message', '未知')}")
            except:
                print(f"   错误: {response.text[:100]}")
        else:
            print(f"   ⚠️  其他状态: {response.text[:100]}")
            
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")

def test_service_info():
    """测试服务信息接口"""
    print("\n🔍 测试服务信息接口")
    print("=" * 40)
    
    # 尝试获取服务信息的常见端点
    info_endpoints = [
        "https://openspeech.bytedance.com/api/v1/info",
        "https://openspeech.bytedance.com/api/v1/service/info",
        "https://openspeech.bytedance.com/api/v1/tts/info",
        "https://openspeech.bytedance.com/api/v1/tts/voices",
        "https://openspeech.bytedance.com/api/v1/voices"
    ]
    
    headers = {
        "Authorization": f"Bearer; {config.VOLCENGINE_TTS_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    for endpoint in info_endpoints:
        print(f"\n🔍 测试: {endpoint}")
        try:
            response = requests.get(endpoint, headers=headers, timeout=5)
            print(f"   状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"   ✅ 成功: {json.dumps(data, ensure_ascii=False, indent=2)[:300]}...")
                except:
                    print(f"   ✅ 成功: {response.text[:200]}...")
            elif response.status_code == 403:
                print("   ⚠️  权限不足")
            elif response.status_code == 404:
                print("   ❌ 不存在")
            else:
                print(f"   ⚠️  状态: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ 失败: {e}")

def test_minimal_request():
    """测试最小化请求"""
    print("\n🔍 测试最小化请求")
    print("=" * 40)
    
    # 最简单的请求格式
    minimal_data = {
        "appid": config.VOLCENGINE_TTS_APP_ID,
        "token": config.VOLCENGINE_TTS_ACCESS_TOKEN,
        "text": "测试",
        "voice_type": "BV001_streaming"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer; {config.VOLCENGINE_TTS_ACCESS_TOKEN}"
    }
    
    try:
        response = requests.post(
            "https://openspeech.bytedance.com/api/v1/tts",
            headers=headers,
            json=minimal_data,
            timeout=10
        )
        
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:500]}")
        
        if response.status_code == 200:
            print("✅ 最小化请求成功！")
        else:
            print("❌ 最小化请求失败")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def check_account_status():
    """检查账户状态建议"""
    print("\n💡 账户状态检查建议")
    print("=" * 40)
    
    print("请在火山引擎控制台检查以下项目：")
    print()
    print("1. 📋 服务开通状态")
    print("   - 进入控制台 → 语音技术 → 语音合成")
    print("   - 确认服务状态为'已开通'")
    print("   - 检查是否有'免费额度'或'付费套餐'")
    print()
    print("2. 🔑 API密钥状态")
    print("   - 检查Access Token是否有效")
    print("   - 确认密钥权限范围")
    print("   - 查看密钥是否有使用限制")
    print()
    print("3. 📊 配额和限制")
    print("   - 查看当前配额使用情况")
    print("   - 确认是否有地域限制")
    print("   - 检查是否有并发限制")
    print()
    print("4. 🎯 资源权限")
    print("   - 查看可用的资源ID列表")
    print("   - 确认已申请的服务类型")
    print("   - 检查是否需要额外申请权限")
    print()
    print("5. 📞 技术支持")
    print("   - 如果以上都正常，联系火山引擎技术支持")
    print("   - 提供应用ID: 6212235312")
    print("   - 提供错误信息: 'requested resource not granted'")

def main():
    """主函数"""
    print("🔍 火山引擎 TTS 设置诊断")
    print("=" * 50)
    
    print(f"📋 当前配置:")
    print(f"   应用ID: {config.VOLCENGINE_TTS_APP_ID}")
    print(f"   访问令牌: {config.VOLCENGINE_TTS_ACCESS_TOKEN[:8]}...{config.VOLCENGINE_TTS_ACCESS_TOKEN[-4:]}")
    print(f"   区域: {config.VOLCENGINE_REGION}")
    
    # 运行各种测试
    test_different_apis()
    test_service_info()
    test_minimal_request()
    check_account_status()
    
    print("\n" + "=" * 50)
    print("📊 诊断完成")
    print("如果所有测试都失败，问题可能在于：")
    print("1. TTS服务未完全开通")
    print("2. 需要申请特定的资源权限")
    print("3. 账户配额或地域限制")
    print("4. 服务正在激活中（可能需要等待）")

if __name__ == "__main__":
    main()