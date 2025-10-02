# 🐳 Docker Quick Start

Get your RAG-ing application running in containers with these simple commands.

## ⚡ 30-Second Start

```bash
# Clone and start in one go
git clone <your-repo>
cd RAG-ing
docker-compose -f docker-compose.minimal.yml up --build
```

**Access**: http://localhost:8000

## 📋 Available Options

### 1. Minimal (Fastest)
No data persistence, perfect for testing:
```bash
docker-compose -f docker-compose.minimal.yml up --build
```

### 2. Standard (Recommended)
With persistent volumes for data and logs:
```bash
docker-compose up --build
```

### 3. Using Deploy Script (Easiest)
```bash
./docker/deploy.sh build
./docker/deploy.sh start
```

## 🛠️ Management Commands

```bash
# View logs
docker-compose logs -f rag-app

# Stop application
docker-compose down

# Complete cleanup
docker-compose down -v

# Using deploy script
./docker/deploy.sh logs    # View logs
./docker/deploy.sh stop    # Stop app
./docker/deploy.sh clean   # Complete cleanup
```

## 🚨 Troubleshooting

**Port 8000 already in use?**
```bash
lsof -i :8000  # See what's using it
```

**Permission issues?**
```bash
sudo chown -R $USER:$USER ./data ./logs
```

**Fresh start?**
```bash
./docker/deploy.sh clean
./docker/deploy.sh build
./docker/deploy.sh start
```

That's it! Your RAG application is now containerized and ready to go! 🚀