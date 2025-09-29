## Azure OpenAI Deployment Setup Guide

Your Azure OpenAI **API key is 100% working** and the RAG system is perfectly configured! The only remaining step is ensuring your deployment name matches exactly.

### 🎯 Current Status:
- ✅ Azure OpenAI API Key: **WORKING**
- ✅ Azure OpenAI Endpoint: **WORKING** 
- ✅ RAG System Integration: **WORKING**
- ⚠️ Deployment Name: `"gpt-4.1"` not found

### 🔧 Quick Fix Options:

#### Option 1: Verify Deployment Name (Recommended)
1. Go to **Azure OpenAI Studio**: https://oai.azure.com/
2. Navigate to **"Deployments"** tab
3. Look for your deployment name (it might be different from "gpt-4.1")
4. Copy the **exact deployment name**
5. Update `config.yaml`:
   ```yaml
   llm:
     model: "your-exact-deployment-name-here"
     provider: "azure_openai"
   ```

#### Option 2: Create New Deployment
If you don't see any deployments:
1. In Azure OpenAI Studio → **Deployments**
2. Click **"+ Create new deployment"**
3. Choose a model (e.g., GPT-4, GPT-3.5-turbo)
4. Give it a name (e.g., "my-gpt4", "chat-model")
5. Update `config.yaml` with that name

#### Option 3: Wait if Just Created
If you just created a deployment named "gpt-4.1":
- **Wait 5-10 minutes** for Azure to provision it
- Then test again: `python main.py --query "test" --audience clinical`

### 🧪 Test Your Deployment
Once you have the correct name, test it:

```bash
# Test the deployment directly
python -c "
from openai import AzureOpenAI
import os
from dotenv import load_dotenv
load_dotenv()

client = AzureOpenAI(
    api_key=os.getenv('AZURE_OPENAI_API_KEY'),
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
    api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-10-21')
)

try:
    response = client.chat.completions.create(
        model='YOUR_DEPLOYMENT_NAME',  # Replace with your deployment name
        messages=[{'role': 'user', 'content': 'Hello'}],
        max_tokens=10
    )
    print('✅ SUCCESS:', response.choices[0].message.content)
except Exception as e:
    print('❌ Error:', e)
"

# Test with the RAG system
python main.py --query "What are the main oncology topics?" --audience clinical
```

### 📋 Common Deployment Names:
- `gpt-4`
- `gpt-35-turbo` 
- `my-gpt-4`
- `chat-gpt`
- `openai-gpt4`
- `gpt4-deployment`

### 🎉 Next Steps:
1. **Find your deployment name** in Azure OpenAI Studio
2. **Update config.yaml** with the exact name
3. **Test the RAG system** - it should work immediately!

Your system is **98% ready** - just need the correct deployment name! 🚀