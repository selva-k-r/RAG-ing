#!/usr/bin/env python3
"""
Azure OpenAI API Key Verification Script
This script tests your Azure OpenAI credentials configuration.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent / "src"))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

def test_environment_variables():
    """Test if environment variables are properly set."""
    print("🔍 Checking Environment Variables...")
    
    required_vars = {
        'AZURE_OPENAI_API_KEY': os.getenv('AZURE_OPENAI_API_KEY'),
        'AZURE_OPENAI_ENDPOINT': os.getenv('AZURE_OPENAI_ENDPOINT'),
        'AZURE_OPENAI_API_VERSION': os.getenv('AZURE_OPENAI_API_VERSION')
    }
    
    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value:
            # Mask the API key for security
            if 'API_KEY' in var_name:
                display_value = var_value[:8] + "*" * (len(var_value) - 8) if len(var_value) > 8 else "*" * len(var_value)
            else:
                display_value = var_value
            print(f"  ✅ {var_name}: {display_value}")
        else:
            print(f"  ❌ {var_name}: Not set")
            all_set = False
    
    return all_set

def test_config_loading():
    """Test if our configuration system can load the credentials."""
    print("\n🔧 Testing Configuration Loading...")
    
    try:
        from rag_ing.config.settings import Settings
        
        # Load settings
        settings = Settings.from_yaml('./config.yaml')
        
        # Check Azure OpenAI credentials
        azure_key = settings.azure_openai_api_key
        azure_endpoint = settings.azure_openai_endpoint
        azure_version = settings.azure_openai_api_version
        
        if azure_key:
            masked_key = azure_key[:8] + "*" * (len(azure_key) - 8) if len(azure_key) > 8 else "*" * len(azure_key)
            print(f"  ✅ Azure OpenAI API Key loaded: {masked_key}")
        else:
            print(f"  ❌ Azure OpenAI API Key: Not loaded")
            return False
            
        if azure_endpoint:
            print(f"  ✅ Azure OpenAI Endpoint: {azure_endpoint}")
        else:
            print(f"  ❌ Azure OpenAI Endpoint: Not loaded")
            return False
            
        print(f"  ✅ Azure OpenAI API Version: {azure_version}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration loading failed: {e}")
        return False

def test_azure_openai_connection():
    """Test actual connection to Azure OpenAI."""
    print("\n🌐 Testing Azure OpenAI Connection...")
    
    try:
        # Import Azure OpenAI
        from openai import AzureOpenAI
        
        # Get credentials from environment
        api_key = os.getenv('AZURE_OPENAI_API_KEY')
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01')
        
        if not all([api_key, endpoint]):
            print("  ❌ Missing credentials")
            return False
        
        # Initialize client
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
        
        print("  ✅ Azure OpenAI client initialized successfully")
        
        # Test with a simple completion (this will use your deployment)
        print("  🧪 Testing simple completion...")
        
        # Note: You'll need to update this with your actual deployment name
        test_models = ["gpt-4", "gpt-4o", "gpt-35-turbo", "gpt-3.5-turbo"]
        
        for model in test_models:
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "Hello, this is a test. Please respond with 'Azure OpenAI connection successful!'"}],
                    max_tokens=50,
                    temperature=0
                )
                
                result = response.choices[0].message.content
                print(f"  ✅ Model '{model}' test successful!")
                print(f"  📝 Response: {result}")
                
                # Show usage info
                if hasattr(response, 'usage'):
                    usage = response.usage
                    print(f"  📊 Usage: {usage.prompt_tokens} prompt + {usage.completion_tokens} completion = {usage.total_tokens} total tokens")
                
                return True
                
            except Exception as model_error:
                print(f"  ⚠️  Model '{model}' failed: {str(model_error)}")
                continue
        
        print("  ❌ All test models failed. Please check your deployment names in Azure.")
        return False
        
    except Exception as e:
        print(f"  ❌ Connection test failed: {e}")
        return False

def test_rag_integration():
    """Test if the RAG system can use Azure OpenAI."""
    print("\n🔗 Testing RAG System Integration...")
    
    try:
        from rag_ing.config.settings import Settings
        from rag_ing.modules.llm_orchestration import LLMOrchestrationModule
        
        # Load configuration
        settings = Settings.from_yaml('./config.yaml')
        
        # Check if provider is set to azure_openai
        if settings.llm.provider != "azure_openai":
            print(f"  ⚠️  LLM provider is set to '{settings.llm.provider}', not 'azure_openai'")
            print("  💡 To use Azure OpenAI, update config.yaml:")
            print("     llm:")
            print("       provider: 'azure_openai'")
            print("       model: 'your-deployment-name'")
            return False
        
        # Initialize LLM orchestration module
        llm_module = LLMOrchestrationModule(settings)
        
        # Test initialization
        if llm_module._initialize_azure_openai():
            print("  ✅ LLM orchestration module initialized with Azure OpenAI")
            return True
        else:
            print("  ❌ LLM orchestration module failed to initialize")
            return False
            
    except Exception as e:
        print(f"  ❌ RAG integration test failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("🚀 Azure OpenAI Configuration Verification")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = Path('.env')
    if env_file.exists():
        print(f"✅ Found .env file at: {env_file.absolute()}")
    else:
        print(f"⚠️  No .env file found. Make sure you have:")
        print("   1. Created .env file from .env.example")
        print("   2. Added your Azure OpenAI credentials")
        print("")
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Configuration Loading", test_config_loading),
        ("Azure OpenAI Connection", test_azure_openai_connection),
        ("RAG Integration", test_rag_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
        print()
    
    # Summary
    print("📋 VERIFICATION SUMMARY")
    print("=" * 50)
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your Azure OpenAI configuration is working correctly.")
        print("\n🚀 You can now run queries with:")
        print("   python main.py --query 'What are the key topics in oncology?' --audience clinical")
    else:
        print("\n🔧 Some tests failed. Please check the errors above and:")
        print("   1. Verify your .env file has correct Azure OpenAI credentials")
        print("   2. Check that your deployment name matches the model in config.yaml")
        print("   3. Ensure your Azure OpenAI endpoint URL is correct")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)