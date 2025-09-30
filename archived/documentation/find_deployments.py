#!/usr/bin/env python3
"""
Find Azure OpenAI Deployment Names
This script tests common deployment names to find which one works.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_deployment_names():
    """Test common Azure OpenAI deployment names."""
    print("🔍 Testing Common Azure OpenAI Deployment Names...")
    print("=" * 60)
    
    try:
        from openai import AzureOpenAI
        
        # Get credentials
        api_key = os.getenv('AZURE_OPENAI_API_KEY')
        endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-10-21')
        
        if not all([api_key, endpoint]):
            print("❌ Missing Azure OpenAI credentials")
            return
        
        # Initialize client
        client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version
        )
        
        # Common deployment names to test
        common_names = [
            # GPT-4 variants
            "gpt-4",
            "gpt4",
            "GPT-4",
            "gpt-4-32k",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-4o-mini",
            
            # GPT-3.5 variants
            "gpt-35-turbo",
            "gpt-3.5-turbo",
            "gpt35turbo",
            "GPT-35-turbo",
            
            # Generic names
            "chat",
            "completions",
            "default",
            "main",
            "test",
            "demo",
            
            # User-specific patterns (common naming)
            "my-gpt-4",
            "my-gpt-35-turbo",
            "chat-gpt",
            "openai-gpt",
        ]
        
        working_deployments = []
        
        for deployment_name in common_names:
            try:
                print(f"🧪 Testing: {deployment_name}...", end=" ")
                
                response = client.chat.completions.create(
                    model=deployment_name,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5,
                    temperature=0
                )
                
                result = response.choices[0].message.content
                print(f"✅ SUCCESS!")
                print(f"    Response: {result}")
                working_deployments.append(deployment_name)
                
                # Show usage info
                if hasattr(response, 'usage'):
                    usage = response.usage
                    print(f"    Usage: {usage.total_tokens} tokens")
                
                print()
                
            except Exception as e:
                if "DeploymentNotFound" in str(e):
                    print("❌ Not found")
                elif "quota" in str(e).lower() or "limit" in str(e).lower():
                    print("⚠️ Quota/Rate limit")
                    working_deployments.append(f"{deployment_name} (has quota limits)")
                else:
                    print(f"❌ Error: {str(e)[:50]}...")
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 RESULTS SUMMARY")
        print("=" * 60)
        
        if working_deployments:
            print("✅ Working Deployments Found:")
            for deployment in working_deployments:
                print(f"   • {deployment}")
            
            recommended = working_deployments[0].split(" (")[0]  # Remove quota note
            print(f"\n💡 RECOMMENDED: Update your config.yaml with:")
            print(f"   llm:")
            print(f"     model: \"{recommended}\"")
            print(f"     provider: \"azure_openai\"")
            
        else:
            print("❌ No working deployments found.")
            print("\n💡 NEXT STEPS:")
            print("   1. Check Azure OpenAI Studio → Deployments")
            print("   2. Create a new deployment if none exists")
            print("   3. Use the exact deployment name in config.yaml")
            
        return working_deployments
        
    except Exception as e:
        print(f"❌ Script failed: {e}")
        return []

if __name__ == "__main__":
    working_deployments = test_deployment_names()
    
    if working_deployments:
        print(f"\n🎉 SUCCESS: Found {len(working_deployments)} working deployment(s)!")
        sys.exit(0)
    else:
        print(f"\n❌ No deployments found. Check Azure OpenAI Studio.")
        sys.exit(1)