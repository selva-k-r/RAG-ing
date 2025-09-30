# Azure OpenAI Configuration Guide

The RAG-ing system supports Azure OpenAI for enterprise-grade LLM integration. This guide shows you how to configure your Azure OpenAI credentials.

## Quick Setup

### 1. Configure Azure OpenAI in config.yaml

```yaml
# Module 3: LLM Orchestration Configuration
llm:
  model: "gpt-4"  # Use your Azure OpenAI deployment name
  provider: "azure_openai"  # Changed from "koboldcpp"
  prompt_template: "./prompts/oncology.txt"
  system_instruction: "You are a biomedical assistant specializing in oncology."
```

### 2. Set Environment Variables

Create a `.env` file in the project root with your Azure OpenAI credentials:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_azure_openai_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-01
```

**Where to find these values:**
- **API Key**: Azure Portal → Your OpenAI Resource → Keys and Endpoint
- **Endpoint**: Azure Portal → Your OpenAI Resource → Keys and Endpoint  
- **API Version**: Use "2024-02-01" (recommended) or latest available

### 3. Test the Configuration

```bash
# Test with a simple query
python main.py --query "What are the main oncology treatments?" --audience clinical

# Or launch the web UI
python main.py --ui
```

## Model Deployment Names

In Azure OpenAI, use your **deployment name** (not the model name) in the config:

```yaml
llm:
  model: "my-gpt4-deployment"  # Your deployment name in Azure
  provider: "azure_openai"
```

Common deployment names:
- `gpt-4` 
- `gpt-35-turbo`
- `gpt-4-turbo`

## Alternative Provider Options

The system supports multiple LLM providers:

```yaml
llm:
  provider: "azure_openai"    # Azure OpenAI (recommended)
  # provider: "openai"        # Standard OpenAI
  # provider: "anthropic"     # Claude models  
  # provider: "koboldcpp"     # Local deployment
```

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use .env files** for local development
3. **Use Azure Key Vault** for production deployments
4. **Rotate API keys** regularly

## Troubleshooting

### Common Issues

**"Azure OpenAI API key not found"**
- Check your `.env` file exists and has `AZURE_OPENAI_API_KEY=...`
- Verify the file is in the project root directory

**"Azure OpenAI endpoint not found"** 
- Ensure `AZURE_OPENAI_ENDPOINT` is set in `.env`
- Format should be: `https://your-resource-name.openai.azure.com/`

**"Invalid deployment name"**
- Use your Azure deployment name, not the base model name
- Check Azure Portal → OpenAI → Model deployments

### Debug Mode

Run with debug mode to see detailed error messages:

```bash
python main.py --debug --query "test query"
```

## Production Deployment

For production environments:

1. **Use Azure Key Vault** instead of `.env` files
2. **Configure managed identity** for secure access
3. **Set up monitoring** for API usage and costs
4. **Implement rate limiting** to control usage

## Cost Management

Azure OpenAI charges per token. Monitor usage:

- Check the system logs for token consumption
- Set up billing alerts in Azure Portal
- Use shorter `max_tokens` values to control response length

```yaml
llm:
  model: "gpt-4"
  provider: "azure_openai"
  temperature: 0.1
  max_tokens: 512  # Adjust based on your needs
```

## Support

For issues with Azure OpenAI integration:

1. Check Azure OpenAI service status
2. Verify your subscription has access to the deployment
3. Review Azure OpenAI documentation
4. Check system logs: `./logs/` directory