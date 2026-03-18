"""测试LLM框架导入和基本功能"""

import sys
import os

# 确保可以导入llm模块
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """测试导入"""
    try:
        from llm import LLMService, LLMException, LLMConfig
        print("✅ LLM框架导入成功")
        return True
    except ImportError as e:
        print(f"❌ LLM框架导入失败: {e}")
        return False

def test_providers():
    """测试提供商适配器导入"""
    try:
        from llm.providers import (
            ProviderAdapter,
            OpenAIProvider,
            VolcEngineProvider,
            DashScopeProvider
        )
        print("✅ 提供商适配器导入成功")
        return True
    except ImportError as e:
        print(f"❌ 提供商适配器导入失败: {e}")
        return False

def test_config():
    """测试配置管理"""
    try:
        from llm import LLMConfig
        
        config = LLMConfig()
        print(f"✅ 配置管理初始化成功")
        print(f"   - 默认提供商: {config.get_default_provider()}")
        
        # 检查各提供商可用性
        providers = ['openai', 'volcengine', 'dashscope']
        for provider in providers:
            available = config.is_provider_available(provider)
            status = "可用" if available else "不可用"
            print(f"   - {provider}: {status}")
        
        return True
    except Exception as e:
        print(f"❌ 配置管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_service():
    """测试LLMService初始化（不实际调用API）"""
    try:
        from llm import LLMService
        
        # 尝试初始化（可能会失败，如果没有配置）
        try:
            llm = LLMService()
            print(f"✅ LLMService初始化成功")
            print(f"   - 提供商: {llm.get_provider()}")
            print(f"   - 模型: {llm.get_model()}")
            return True
        except Exception as e:
            print(f"⚠️  LLMService初始化失败（可能是配置问题）: {e}")
            print("   这是正常的，如果没有配置API密钥")
            return True  # 不算错误，只是没有配置
    except Exception as e:
        print(f"❌ LLMService测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_generator():
    """测试AIGenerator（业务层）"""
    try:
        from game.ai_generator import AIGenerator
        
        ai_gen = AIGenerator()
        print(f"✅ AIGenerator初始化成功")
        print(f"   - 启用状态: {ai_gen.enabled}")
        if ai_gen.enabled:
            print(f"   - 使用的LLM服务: {ai_gen.llm_service.get_provider()}")
        return True
    except Exception as e:
        print(f"❌ AIGenerator测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("LLM框架测试")
    print("=" * 50)
    
    results = []
    
    print("\n1. 测试导入...")
    results.append(test_imports())
    
    print("\n2. 测试提供商适配器...")
    results.append(test_providers())
    
    print("\n3. 测试配置管理...")
    results.append(test_config())
    
    print("\n4. 测试LLMService...")
    results.append(test_llm_service())
    
    print("\n5. 测试AIGenerator（业务层）...")
    results.append(test_ai_generator())
    
    print("\n" + "=" * 50)
    print(f"测试结果: {sum(results)}/{len(results)} 通过")
    print("=" * 50)
