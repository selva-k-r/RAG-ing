#!/usr/bin/env python3
"""Alternative approach to access HL7 content - try known public endpoints."""

import requests
import time
from urllib.parse import urljoin

def try_alternative_access():
    """Try accessing HL7 content through different methods."""
    
    print("🔍 Trying alternative access methods to HL7 content...\n")
    
    # Method 1: Try direct access to known HL7 FHIR endpoints
    fhir_endpoints = [
        "https://www.hl7.org/fhir/",
        "https://build.fhir.org/",
        "https://hl7.org/fhir/r4/",
        "https://hl7.org/fhir/r5/"
    ]
    
    print("📚 Method 1: Trying direct FHIR documentation endpoints...")
    for endpoint in fhir_endpoints:
        try:
            print(f"   Testing: {endpoint}")
            response = requests.get(endpoint, timeout=10)
            if response.status_code == 200:
                print(f"   ✅ Accessible! Status: {response.status_code}")
                content_length = len(response.text)
                print(f"   📄 Content length: {content_length} characters")
                
                # Show a snippet
                snippet = response.text[:300].replace('\n', ' ').replace('\r', ' ')
                print(f"   📝 Content preview: {snippet}...")
                print()
                
                # Try to save this content for testing
                if content_length > 1000:  # Only save substantial content
                    filename = f"fhir_content_{endpoint.split('/')[-2] or 'main'}.html"
                    filename = filename.replace(':', '_').replace('/', '_')
                    with open(f"data/{filename}", 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"   💾 Saved content to: data/{filename}")
                    return True
            else:
                print(f"   ❌ Not accessible: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        time.sleep(1)  # Be polite
    
    # Method 2: Try public HL7 GitHub repositories
    print("\n📚 Method 2: Trying HL7 GitHub repositories...")
    github_repos = [
        "https://raw.githubusercontent.com/HL7/fhir/master/README.md",
        "https://raw.githubusercontent.com/HL7/fhir-ig-publisher/master/README.md",
        "https://raw.githubusercontent.com/HL7/davinci-pta/master/README.md"
    ]
    
    for repo_url in github_repos:
        try:
            print(f"   Testing: {repo_url}")
            response = requests.get(repo_url, timeout=10)
            if response.status_code == 200:
                print(f"   ✅ Accessible! Status: {response.status_code}")
                content_length = len(response.text)
                print(f"   📄 Content length: {content_length} characters")
                
                if content_length > 500:
                    # Save this content
                    filename = f"hl7_github_{repo_url.split('/')[-2]}.md"
                    with open(f"data/{filename}", 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"   💾 Saved content to: data/{filename}")
                    
                    # Show snippet
                    snippet = response.text[:200].replace('\n', ' ')
                    print(f"   📝 Content preview: {snippet}...")
                    return True
            else:
                print(f"   ❌ Not accessible: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        time.sleep(1)
    
    # Method 3: Create sample HL7/FHIR content for demonstration
    print("\n📚 Method 3: Creating sample HL7/FHIR content for demonstration...")
    
    sample_content = """
# HL7 FHIR Implementation Guide

## Overview
Fast Healthcare Interoperability Resources (FHIR) is a standard describing data formats and elements and an application programming interface (API) for exchanging electronic health records.

## Key Concepts

### Resources
FHIR is based on the concept of "Resources" - modular components that can be assembled into working systems. Key resources include:

- **Patient**: Demographics and administrative information about a person receiving health-related services
- **Observation**: Measurements and simple assertions made about a patient
- **Medication**: Information about a medication
- **Encounter**: An interaction between a patient and healthcare provider
- **Practitioner**: Information about a healthcare professional

### Data Types
FHIR defines several primitive data types:
- string: A sequence of Unicode characters
- boolean: true | false
- integer: A signed 32-bit integer
- decimal: Rational numbers with decimal representation
- uri: A Uniform Resource Identifier Reference
- date: A date, or partial date (YYYY, YYYY-MM, or YYYY-MM-DD)
- dateTime: A date, date-time or partial date/date-time

### RESTful API
FHIR uses RESTful principles for API interactions:
- GET: Read operations
- POST: Create operations  
- PUT: Update operations
- DELETE: Delete operations

## Implementation Guidelines

### Security Considerations
- OAuth 2.0 for authorization
- TLS encryption for data in transit
- Audit logging for access tracking
- Data validation and sanitization

### Interoperability
FHIR promotes interoperability through:
- Standardized resource definitions
- Common terminologies (SNOMED CT, LOINC, RxNorm)
- Conformance statements
- Implementation guides

## Clinical Decision Support
FHIR supports clinical decision support through:
- Clinical Quality Language (CQL)
- Decision support service modules
- Knowledge artifacts as FHIR resources
- Integration with clinical workflows

This is sample content for testing the RAG system with healthcare interoperability standards.
"""
    
    with open("data/hl7_fhir_sample.md", 'w', encoding='utf-8') as f:
        f.write(sample_content)
    
    print("   💾 Created sample HL7/FHIR content: data/hl7_fhir_sample.md")
    print("   📄 Content includes FHIR resources, data types, and implementation guidelines")
    
    return True

if __name__ == "__main__":
    success = try_alternative_access()
    if success:
        print("\n✅ Successfully obtained HL7/FHIR content for RAG system testing!")
    else:
        print("\n❌ Could not access HL7 content through automated methods.")
        print("💡 Consider manually downloading content or using sample data.")