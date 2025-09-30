#!/usr/bin/env python3
"""Test script to verify the RAG integration is working"""

import requests
import json
import time

def test_rag_integration():
    """Test the full RAG integration via API."""
    print("🧪 Testing RAG Integration...")
    
    # Wait for server to start
    print("⏳ Waiting for server to start...")
    for i in range(30):
        try:
            response = requests.get("http://localhost:8000/api/health", timeout=2)
            if response.status_code == 200:
                print("✅ Server is running!")
                break
        except:
            time.sleep(2)
    else:
        print("❌ Server failed to start")
        return False
    
    # Test search API
    print("\n🔍 Testing search API...")
    search_data = {
        "query": "What is cancer treatment?",
        "sources": ["confluence", "internal"],
        "audience": "technical"
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/api/search",
            json=search_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Search API working!")
            print(f"📝 Response: {result['response'][:100]}...")
            print(f"📚 Sources: {len(result['sources'])} found")
            print(f"🎯 Query Hash: {result['query_hash']}")
            return True
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Search error: {e}")
        return False

if __name__ == "__main__":
    success = test_rag_integration()
    if success:
        print("\n🎉 RAG Integration is working! The UI is now connected to the backend.")
        print("💡 Open http://localhost:8000 in your browser and try searching!")
    else:
        print("\n❌ RAG Integration test failed")