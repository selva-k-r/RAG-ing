"""
Comprehensive verification script for Azure OpenAI connections.
Tests both LLM (GPT) and Embedding deployments separately.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def check_environment_variables():
    """Check all required environment variables."""
    print("=" * 70)
    print("🔍 STEP 1: Checking Environment Variables")
    print("=" * 70)
    
    load_dotenv()
    
    # LLM variables
    llm_vars = {
        "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY"),
        "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    }
    
    # Embedding variables
    embedding_vars = {
        "AZURE_OPENAI_EMBEDDING_ENDPOINT": os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT"),
        "AZURE_OPENAI_EMBEDDING_API_KEY": os.getenv("AZURE_OPENAI_EMBEDDING_API_KEY"),
        "AZURE_OPENAI_EMBEDDING_API_VERSION": os.getenv("AZURE_OPENAI_EMBEDDING_API_VERSION", "2024-02-15-preview")
    }
    
    print("\n📱 LLM (GPT) Configuration:")
    print("-" * 70)
    llm_ok = True
    for var_name, var_value in llm_vars.items():
        if var_value:
            if "KEY" in var_name:
                display_value = f"{var_value[:10]}...{var_value[-4:]}" if len(var_value) > 14 else "***"
            else:
                display_value = var_value
            print(f"✅ {var_name}: {display_value}")
        else:
            print(f"❌ {var_name}: NOT SET")
            llm_ok = False
    
    print("\n🔤 Embedding Configuration:")
    print("-" * 70)
    embedding_ok = True
    for var_name, var_value in embedding_vars.items():
        if var_value:
            if "KEY" in var_name:
                display_value = f"{var_value[:10]}...{var_value[-4:]}" if len(var_value) > 14 else "***"
            else:
                display_value = var_value
            print(f"✅ {var_name}: {display_value}")
        else:
            print(f"❌ {var_name}: NOT SET")
            embedding_ok = False
    
    print()
    return llm_ok, embedding_ok, llm_vars, embedding_vars


def test_llm_connection(endpoint, api_key, api_version):
    """Test Azure OpenAI LLM (GPT) connection."""
    print("=" * 70)
    print("🤖 STEP 2: Testing Azure OpenAI LLM (GPT) Connection")
    print("=" * 70)
    
    try:
        from openai import AzureOpenAI
        
        # Initialize client
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
        
        print(f"📡 LLM Endpoint: {endpoint}")
        print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
        print(f"📅 API Version: {api_version}")
        print()
        
        # Test with a simple completion
        print("🧪 Testing LLM with sample query...")
        
        # Try to get a simple response
        # Note: gpt-5-nano uses max_completion_tokens instead of max_tokens
        response = client.chat.completions.create(
            model="gpt-5-nano",  # Your deployment name from config
            messages=[
                {"role": "user", "content": "Say 'Hello, I am working!' in exactly 5 words."}
            ],
            max_completion_tokens=50,  # GPT-5-nano parameter
            temperature=1.0  # GPT-5-nano only supports temperature=1.0
        )
        
        generated_text = response.choices[0].message.content
        
        print(f"✅ SUCCESS! LLM is responding")
        print(f"   📝 Response: {generated_text}")
        print(f"   🎯 Model: {response.model}")
        print(f"   📊 Tokens used: {response.usage.total_tokens}")
        print(f"   ⏱️ Finish reason: {response.choices[0].finish_reason}")
        print()
        
        return True, response
        
    except Exception as e:
        print(f"❌ FAILED! Error: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        
        # Provide helpful error messages
        if "401" in str(e) or "authentication" in str(e).lower():
            print("\n💡 Authentication Error - Check:")
            print("   1. API key is correct")
            print("   2. API key is not expired")
            print("   3. Endpoint URL is correct")
        elif "404" in str(e) or "not found" in str(e).lower():
            print("\n💡 Deployment Not Found - Check:")
            print("   1. Deployment name 'gpt-5-nano' exists in Azure")
            print("   2. Deployment name matches exactly (case-sensitive)")
        elif "429" in str(e):
            print("\n💡 Rate Limit - Your quota may be exhausted")
        
        print()
        return False, None


def test_embedding_connection(endpoint, api_key, api_version):
    """Test Azure OpenAI Embedding connection."""
    print("=" * 70)
    print("🔤 STEP 3: Testing Azure OpenAI Embedding Connection")
    print("=" * 70)
    
    try:
        from openai import AzureOpenAI
        
        # Initialize client
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
        
        print(f"📡 Embedding Endpoint: {endpoint}")
        print(f"🔑 API Key: {api_key[:10]}...{api_key[-4:]}")
        print(f"📅 API Version: {api_version}")
        print()
        
        # Test embedding generation
        print("🧪 Testing embedding with sample text...")
        test_text = "This is a test query for oncology biomarker analysis"
        
        response = client.embeddings.create(
            input=[test_text],
            model="text-embedding-ada-002"  # Your deployment name from config
        )
        
        embedding = response.data[0].embedding
        
        print(f"✅ SUCCESS! Embedding generated successfully")
        print(f"   📊 Vector dimension: {len(embedding)}")
        print(f"   📈 Sample values: [{embedding[0]:.6f}, {embedding[1]:.6f}, {embedding[2]:.6f}, ...]")
        print(f"   🎯 Tokens used: {response.usage.total_tokens}")
        print(f"   🔢 Model: {response.model}")
        print()
        
        return True, embedding
        
    except Exception as e:
        print(f"❌ FAILED! Error: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        
        # Provide helpful error messages
        if "401" in str(e) or "authentication" in str(e).lower():
            print("\n💡 Authentication Error - Check:")
            print("   1. API key is correct for embedding resource")
            print("   2. API key is not expired")
            print("   3. Endpoint URL is correct")
        elif "404" in str(e) or "not found" in str(e).lower():
            print("\n💡 Deployment Not Found - Check:")
            print("   1. Deployment 'text-embedding-ada-002' exists in Azure")
            print("   2. Deployment name matches exactly (case-sensitive)")
        elif "429" in str(e):
            print("\n💡 Rate Limit - Your quota may be exhausted")
        
        print()
        return False, None


def test_config_loading():
    """Test configuration loading from config.yaml."""
    print("=" * 70)
    print("⚙️ STEP 4: Testing Configuration Loading")
    print("=" * 70)
    
    try:
        from rag_ing.config.settings import Settings
        
        settings = Settings.from_yaml("config.yaml")
        
        print("✅ Config loaded successfully!\n")
        
        print("📱 LLM Configuration:")
        print(f"   Model: {settings.llm.model}")
        print(f"   Provider: {settings.llm.provider}")
        print(f"   Deployment: {settings.llm.azure_deployment_name}")
        print(f"   Max Tokens: {settings.llm.max_tokens}")
        print()
        
        print("🔤 Embedding Configuration:")
        print(f"   Provider: {settings.embedding_model.provider}")
        print(f"   Use Azure Primary: {settings.embedding_model.use_azure_primary}")
        print(f"   Model: {settings.embedding_model.azure_model}")
        print(f"   Deployment: {settings.embedding_model.azure_deployment_name}")
        print()
        
        return True, settings
        
    except Exception as e:
        print(f"❌ Config loading failed: {str(e)}")
        import traceback
        print(traceback.format_exc())
        print()
        return False, None


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("🔍 Azure OpenAI Complete Connection Verification")
    print("   Testing both LLM (GPT) and Embedding deployments")
    print("=" * 70)
    print()
    
    # Step 1: Check environment variables
    llm_env_ok, embedding_env_ok, llm_vars, embedding_vars = check_environment_variables()
    
    # Step 2: Test LLM connection
    llm_ok = False
    if llm_env_ok:
        llm_ok, _ = test_llm_connection(
            llm_vars["AZURE_OPENAI_ENDPOINT"],
            llm_vars["AZURE_OPENAI_API_KEY"],
            llm_vars["AZURE_OPENAI_API_VERSION"]
        )
    else:
        print("=" * 70)
        print("🤖 STEP 2: Skipping LLM Test (missing environment variables)")
        print("=" * 70)
        print()
    
    # Step 3: Test Embedding connection
    embedding_ok = False
    if embedding_env_ok:
        embedding_ok, _ = test_embedding_connection(
            embedding_vars["AZURE_OPENAI_EMBEDDING_ENDPOINT"],
            embedding_vars["AZURE_OPENAI_EMBEDDING_API_KEY"],
            embedding_vars["AZURE_OPENAI_EMBEDDING_API_VERSION"]
        )
    else:
        print("=" * 70)
        print("🔤 STEP 3: Skipping Embedding Test (missing environment variables)")
        print("=" * 70)
        print()
    
    # Step 4: Test config loading
    config_ok, settings = test_config_loading()
    
    # Final summary
    print("=" * 70)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"LLM Environment Variables:       {'✅ PASS' if llm_env_ok else '❌ FAIL'}")
    print(f"LLM Connection Test:             {'✅ PASS' if llm_ok else '❌ FAIL'}")
    print(f"Embedding Environment Variables: {'✅ PASS' if embedding_env_ok else '❌ FAIL'}")
    print(f"Embedding Connection Test:       {'✅ PASS' if embedding_ok else '❌ FAIL'}")
    print(f"Configuration Loading:           {'✅ PASS' if config_ok else '❌ FAIL'}")
    print("=" * 70)
    
    if all([llm_env_ok, llm_ok, embedding_env_ok, embedding_ok, config_ok]):
        print("\n🎉 ALL TESTS PASSED!")
        print("   Both LLM and Embedding connections are working properly.")
        print("   Your system is ready to use!")
        print("\n🚀 Next Steps:")
        print("   1. Run: python main.py --ingest    (Process your documents)")
        print("   2. Run: python main.py --ui         (Launch the web interface)")
        print()
        return True
    else:
        print("\n⚠️ SOME TESTS FAILED!")
        print("   Review the errors above and fix configuration issues.")
        print("\n📝 Required Environment Variables:")
        print("\n   For LLM (GPT models):")
        print("   - AZURE_OPENAI_ENDPOINT")
        print("   - AZURE_OPENAI_API_KEY")
        print("   - AZURE_OPENAI_API_VERSION (optional, defaults to 2024-02-15-preview)")
        print("\n   For Embeddings:")
        print("   - AZURE_OPENAI_EMBEDDING_ENDPOINT")
        print("   - AZURE_OPENAI_EMBEDDING_API_KEY")
        print("   - AZURE_OPENAI_EMBEDDING_API_VERSION (optional)")
        print()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
