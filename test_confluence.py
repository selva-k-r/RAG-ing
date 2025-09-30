#!/usr/bin/env python3
"""Test script to explore HL7 Confluence and find available spaces."""

import requests
import base64
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_confluence_connection():
    """Test connection to HL7 Confluence and explore available spaces."""
    
    # Get credentials from environment
    base_url = os.getenv("CONFLUENCE_BASE_URL")
    username = os.getenv("CONFLUENCE_USERNAME")
    api_token = os.getenv("CONFLUENCE_API_TOKEN")
    
    print(f"🔗 Testing connection to: {base_url}")
    print(f"👤 Username: {username}")
    print(f"🔑 API Token: {'*' * 20}...")
    
    # Setup authentication
    auth_string = f"{username}:{api_token}"
    auth_bytes = auth_string.encode('ascii')
    auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/json"
    }
    
    try:
        # Test basic connection
        print("\n🧪 Testing basic connection...")
        test_url = f"{base_url}/rest/api/content"
        response = requests.get(test_url, headers=headers, params={"limit": 1}, timeout=30)
        
        if response.status_code == 200:
            print("✅ Connection successful!")
        else:
            print(f"❌ Connection failed: {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        # Get available spaces
        print("\n📚 Fetching available spaces...")
        spaces_url = f"{base_url}/rest/api/space"
        response = requests.get(spaces_url, headers=headers, params={"limit": 20}, timeout=30)
        
        if response.status_code == 200:
            spaces_data = response.json()
            spaces = spaces_data.get("results", [])
            
            print(f"Found {len(spaces)} spaces:")
            for space in spaces:
                key = space.get("key", "N/A")
                name = space.get("name", "N/A")
                type_info = space.get("type", "N/A")
                print(f"  📁 {key}: {name} ({type_info})")
        else:
            print(f"❌ Failed to fetch spaces: {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        # Try to get content from FHIR space (if it exists)
        fhir_spaces = [s for s in spaces if "FHIR" in s.get("key", "").upper()]
        if fhir_spaces:
            space_key = fhir_spaces[0]["key"]
            print(f"\n🔍 Exploring FHIR space: {space_key}")
            
            content_url = f"{base_url}/rest/api/content"
            params = {
                "spaceKey": space_key,
                "expand": "body.storage,version",
                "limit": 5
            }
            
            response = requests.get(content_url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                content_data = response.json()
                pages = content_data.get("results", [])
                
                print(f"Found {len(pages)} pages in {space_key}:")
                for page in pages:
                    title = page.get("title", "N/A")
                    page_id = page.get("id", "N/A")
                    url = f"{base_url}/pages/viewpage.action?pageId={page_id}"
                    print(f"  📄 {title} (ID: {page_id})")
                    print(f"      URL: {url}")
            else:
                print(f"❌ Failed to fetch content from {space_key}: {response.status_code}")
        else:
            # Try first available space
            if spaces:
                space_key = spaces[0]["key"]
                print(f"\n🔍 Exploring first available space: {space_key}")
                
                content_url = f"{base_url}/rest/api/content"
                params = {
                    "spaceKey": space_key,
                    "expand": "body.storage,version",
                    "limit": 3
                }
                
                response = requests.get(content_url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    content_data = response.json()
                    pages = content_data.get("results", [])
                    
                    print(f"Found {len(pages)} pages in {space_key}:")
                    for page in pages:
                        title = page.get("title", "N/A")
                        page_id = page.get("id", "N/A")
                        url = f"{base_url}/pages/viewpage.action?pageId={page_id}"
                        print(f"  📄 {title} (ID: {page_id})")
                        print(f"      URL: {url}")
                        
                        # Show a snippet of content
                        body = page.get("body", {}).get("storage", {}).get("value", "")
                        if body:
                            import re
                            clean_content = re.sub(r'<[^>]+>', ' ', body)
                            clean_content = re.sub(r'\s+', ' ', clean_content).strip()
                            snippet = clean_content[:200] + "..." if len(clean_content) > 200 else clean_content
                            print(f"      📝 Content preview: {snippet}")
                else:
                    print(f"❌ Failed to fetch content from {space_key}: {response.status_code}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    test_confluence_connection()