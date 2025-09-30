#!/usr/bin/env python3
"""
Quick test script to verify the FastAPI server is working correctly.
"""

import requests
import json
import time

def test_server():
    """Test the FastAPI server endpoints."""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing iConnect FastAPI Server")
    print("=" * 50)
    
    # Test 1: Health check
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Health check passed")
            print(f"   Response: {response.json()}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Health check failed: {e}")
        return False
    
    # Test 2: Homepage
    print("\n2. Testing homepage...")
    try:
        response = requests.get(base_url, timeout=5)
        if response.status_code == 200:
            print("   ✅ Homepage loads successfully")
            print(f"   Content length: {len(response.text)} characters")
        else:
            print(f"   ❌ Homepage failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Homepage failed: {e}")
    
    # Test 3: API Status
    print("\n3. Testing API status...")
    try:
        response = requests.get(f"{base_url}/api/status", timeout=5)
        if response.status_code == 200:
            print("   ✅ API status check passed")
            status_data = response.json()
            print(f"   System status: {status_data.get('status', 'unknown')}")
        else:
            print(f"   ❌ API status failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ API status failed: {e}")
    
    # Test 4: Search API (light test)
    print("\n4. Testing search API...")
    try:
        search_data = {
            "query": "test query",
            "sources": ["confluence"],
            "audience": "technical"
        }
        response = requests.post(
            f"{base_url}/api/search", 
            json=search_data, 
            timeout=10
        )
        if response.status_code == 200:
            print("   ✅ Search API responds successfully")
            result = response.json()
            print(f"   Response contains: {list(result.keys())}")
        else:
            print(f"   ⚠️  Search API returned: {response.status_code}")
            print(f"   This might be expected if no documents are ingested yet")
    except requests.exceptions.RequestException as e:
        print(f"   ⚠️  Search API error: {e}")
        print("   This might be expected if no documents are ingested yet")
    
    print("\n" + "=" * 50)
    print("🎉 Server test complete!")
    print(f"🌐 Access your application at: {base_url}")
    print(f"📖 API documentation at: {base_url}/docs")
    
    return True

if __name__ == "__main__":
    test_server()