#!/usr/bin/env python3
"""
Configuration Validator for RAG-ing Pipeline

Validates config.yaml and environment variables to ensure all required
settings are present and properly configured.

Usage:
    python debug_tools/01_check_config.py
"""

import sys
import os
from pathlib import Path
import yaml
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# ASCII-safe status indicators
STATUS_OK = "[OK]"
STATUS_ERROR = "[X]"
STATUS_WARNING = "[!]"
STATUS_INFO = "[i]"


def print_header(title):
    """Print section header."""
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}\n")


def check_file_exists(filepath, description):
    """Check if a file exists and is readable."""
    path = Path(filepath)
    if not path.exists():
        print(f"{STATUS_ERROR} {description}: NOT FOUND")
        print(f"    Expected location: {filepath}")
        return False
    
    if not path.is_file():
        print(f"{STATUS_ERROR} {description}: NOT A FILE")
        return False
    
    try:
        with open(path, 'r') as f:
            f.read(1)
        print(f"{STATUS_OK} {description}: Found and readable")
        return True
    except Exception as e:
        print(f"{STATUS_ERROR} {description}: NOT READABLE")
        print(f"    Error: {e}")
        return False


def validate_yaml_syntax(filepath):
    """Validate YAML file syntax."""
    try:
        with open(filepath, 'r') as f:
            yaml.safe_load(f)
        print(f"{STATUS_OK} YAML syntax: Valid")
        return True
    except yaml.YAMLError as e:
        print(f"{STATUS_ERROR} YAML syntax: INVALID")
        print(f"    Error: {e}")
        return False
    except Exception as e:
        print(f"{STATUS_ERROR} YAML parsing: FAILED")
        print(f"    Error: {e}")
        return False


def check_env_variable(var_name, required=True):
    """Check if environment variable is set."""
    value = os.getenv(var_name)
    
    if value:
        # Mask sensitive values
        if any(keyword in var_name.lower() for keyword in ['key', 'token', 'password', 'secret', 'pat']):
            masked = value[:4] + "*" * (len(value) - 4) if len(value) > 4 else "****"
            print(f"{STATUS_OK} {var_name}: Set ({masked})")
        else:
            print(f"{STATUS_OK} {var_name}: {value}")
        return True
    else:
        if required:
            print(f"{STATUS_ERROR} {var_name}: NOT SET (required)")
        else:
            print(f"{STATUS_WARNING} {var_name}: NOT SET (optional)")
        return not required


def load_config_settings():
    """Load configuration using Pydantic Settings."""
    try:
        from rag_ing.config.settings import Settings
        settings = Settings.from_yaml('./config.yaml')
        print(f"{STATUS_OK} Pydantic validation: PASSED")
        return settings, True
    except Exception as e:
        print(f"{STATUS_ERROR} Pydantic validation: FAILED")
        print(f"    Error: {e}")
        return None, False


def validate_data_sources(config_data):
    """Validate data source configuration."""
    print_header("Data Source Configuration")
    
    if 'data_source' not in config_data:
        print(f"{STATUS_ERROR} No data_source section found")
        return False
    
    data_source = config_data['data_source']
    
    # Check for sources array
    if 'sources' not in data_source:
        print(f"{STATUS_WARNING} No 'sources' array - using legacy format")
        return True
    
    sources = data_source['sources']
    enabled_count = 0
    
    for idx, source in enumerate(sources):
        source_type = source.get('type', 'unknown')
        enabled = source.get('enabled', False)
        
        print(f"\n{STATUS_INFO} Source {idx + 1}: {source_type}")
        print(f"    Enabled: {enabled}")
        
        if enabled:
            enabled_count += 1
            
            # Validate source-specific config
            if source_type == 'local_file':
                path = source.get('path', './data/')
                if Path(path).exists():
                    print(f"    {STATUS_OK} Path exists: {path}")
                else:
                    print(f"    {STATUS_WARNING} Path not found: {path}")
            
            elif source_type == 'azure_devops':
                ado_config = source.get('azure_devops', {})
                required = ['organization', 'project', 'pat_token', 'repo_name']
                for key in required:
                    if key in ado_config:
                        print(f"    {STATUS_OK} {key}: configured")
                    else:
                        print(f"    {STATUS_ERROR} {key}: MISSING")
            
            elif source_type == 'confluence':
                conf_config = source.get('confluence', {})
                required = ['base_url', 'username', 'auth_token']
                for key in required:
                    if key in conf_config:
                        print(f"    {STATUS_OK} {key}: configured")
                    else:
                        print(f"    {STATUS_ERROR} {key}: MISSING")
    
    print(f"\n{STATUS_INFO} Total sources: {len(sources)}, Enabled: {enabled_count}")
    
    if enabled_count == 0:
        print(f"{STATUS_WARNING} No data sources enabled - ingestion will not fetch any data")
        return False
    
    return True


def validate_embedding_config(config_data):
    """Validate embedding model configuration."""
    print_header("Embedding Model Configuration")
    
    if 'embedding_model' not in config_data:
        print(f"{STATUS_ERROR} No embedding_model section found")
        return False
    
    emb_config = config_data['embedding_model']
    provider = emb_config.get('provider', 'unknown')
    
    print(f"{STATUS_INFO} Provider: {provider}")
    
    if provider == 'azure_openai':
        required = ['azure_endpoint', 'azure_api_key', 'azure_deployment_name']
        all_present = True
        for key in required:
            if key in emb_config:
                print(f"{STATUS_OK} {key}: configured")
            else:
                print(f"{STATUS_ERROR} {key}: MISSING")
                all_present = False
        return all_present
    elif provider == 'huggingface':
        model = emb_config.get('fallback_model', 'unknown')
        print(f"{STATUS_INFO} HuggingFace model: {model}")
        return True
    else:
        print(f"{STATUS_WARNING} Unknown provider: {provider}")
        return False


def validate_vector_store_config(config_data):
    """Validate vector store configuration."""
    print_header("Vector Store Configuration")
    
    if 'vector_store' not in config_data:
        print(f"{STATUS_ERROR} No vector_store section found")
        return False
    
    vs_config = config_data['vector_store']
    store_type = vs_config.get('type', 'unknown')
    persist_dir = vs_config.get('persist_directory', './vector_store')
    collection = vs_config.get('collection_name', 'rag_documents')
    
    print(f"{STATUS_INFO} Type: {store_type}")
    print(f"{STATUS_INFO} Collection: {collection}")
    print(f"{STATUS_INFO} Persist directory: {persist_dir}")
    
    # Check if directory exists
    vs_path = Path(persist_dir)
    if vs_path.exists():
        print(f"{STATUS_OK} Vector store directory exists")
    else:
        print(f"{STATUS_WARNING} Vector store directory not found (will be created)")
    
    return True


def main():
    """Main validation routine."""
    print_header("RAG-ing Configuration Validator")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }
    
    # Check 1: config.yaml exists
    print_header("File Existence Checks")
    config_exists = check_file_exists('./config.yaml', 'config.yaml')
    results['checks']['config_exists'] = config_exists
    
    env_example_exists = check_file_exists('./env.example', 'env.example')
    results['checks']['env_example_exists'] = env_example_exists
    
    if not config_exists:
        print(f"\n{STATUS_ERROR} CRITICAL: config.yaml not found")
        print(f"\nSolutions:")
        print(f"  1. Copy from template: cp config.example.yaml config.yaml")
        print(f"  2. Check current directory: pwd")
        print(f"  3. Run from project root")
        sys.exit(1)
    
    # Check 2: YAML syntax
    print_header("YAML Syntax Validation")
    yaml_valid = validate_yaml_syntax('./config.yaml')
    results['checks']['yaml_valid'] = yaml_valid
    
    if not yaml_valid:
        print(f"\n{STATUS_ERROR} CRITICAL: config.yaml has syntax errors")
        print(f"\nSolutions:")
        print(f"  1. Use YAML validator: yamllint config.yaml")
        print(f"  2. Check indentation (spaces, not tabs)")
        print(f"  3. Validate online: https://www.yamllint.com/")
        sys.exit(1)
    
    # Check 3: Load with Pydantic
    print_header("Pydantic Schema Validation")
    settings, pydantic_valid = load_config_settings()
    results['checks']['pydantic_valid'] = pydantic_valid
    
    # Check 4: Environment variables
    print_header("Environment Variables")
    
    # Load config to check which env vars are needed
    with open('./config.yaml', 'r') as f:
        config_data = yaml.safe_load(f)
    
    env_vars_ok = True
    
    # Azure OpenAI (if enabled)
    if config_data.get('embedding_model', {}).get('provider') == 'azure_openai':
        print(f"\n{STATUS_INFO} Azure OpenAI Embedding Variables:")
        env_vars_ok &= check_env_variable('AZURE_OPENAI_EMBEDDING_ENDPOINT', required=True)
        env_vars_ok &= check_env_variable('AZURE_OPENAI_EMBEDDING_API_KEY', required=True)
        env_vars_ok &= check_env_variable('AZURE_OPENAI_EMBEDDING_API_VERSION', required=False)
    
    # Azure DevOps (if enabled)
    azure_devops_enabled = any(
        s.get('type') == 'azure_devops' and s.get('enabled')
        for s in config_data.get('data_source', {}).get('sources', [])
    )
    if azure_devops_enabled:
        print(f"\n{STATUS_INFO} Azure DevOps Variables:")
        env_vars_ok &= check_env_variable('AZURE_DEVOPS_ORG', required=True)
        env_vars_ok &= check_env_variable('AZURE_DEVOPS_PROJECT', required=True)
        env_vars_ok &= check_env_variable('AZURE_DEVOPS_PAT', required=True)
        env_vars_ok &= check_env_variable('AZURE_DEVOPS_REPO', required=True)
    
    results['checks']['env_vars_ok'] = env_vars_ok
    
    # Check 5: Data sources
    data_sources_ok = validate_data_sources(config_data)
    results['checks']['data_sources_ok'] = data_sources_ok
    
    # Check 6: Embedding config
    embedding_ok = validate_embedding_config(config_data)
    results['checks']['embedding_ok'] = embedding_ok
    
    # Check 7: Vector store
    vector_store_ok = validate_vector_store_config(config_data)
    results['checks']['vector_store_ok'] = vector_store_ok
    
    # Final summary
    print_header("Validation Summary")
    
    all_checks = [
        ('Configuration file exists', config_exists),
        ('YAML syntax valid', yaml_valid),
        ('Pydantic validation passed', pydantic_valid),
        ('Environment variables set', env_vars_ok),
        ('Data sources configured', data_sources_ok),
        ('Embedding model configured', embedding_ok),
        ('Vector store configured', vector_store_ok)
    ]
    
    passed = sum(1 for _, ok in all_checks if ok)
    total = len(all_checks)
    
    for check_name, ok in all_checks:
        status = STATUS_OK if ok else STATUS_ERROR
        print(f"{status} {check_name}")
    
    print(f"\n{STATUS_INFO} Result: {passed}/{total} checks passed")
    
    results['summary'] = {
        'total_checks': total,
        'passed': passed,
        'failed': total - passed,
        'success_rate': passed / total * 100
    }
    
    # Save results
    output_dir = Path('./debug_tools/reports')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'config_validation.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{STATUS_INFO} Results saved to: {output_file}")
    
    if passed == total:
        print(f"\n{STATUS_OK} All configuration checks passed!")
        return 0
    else:
        print(f"\n{STATUS_WARNING} Some configuration checks failed - review above")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
