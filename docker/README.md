# Simple Docker Setup for RAG-ing

This is a minimal Docker configuration for the RAG-ing application.

## � Quick Start

### Option 1: Fastest (No persistence)
```bash
docker-compose -f docker-compose.minimal.yml up --build
```

### Option 2: With data persistence
```bash
docker-compose up --build
```

### Option 3: Using the deploy script
```bash
# Build and start
./docker/deploy.sh build
./docker/deploy.sh start

# View logs
./docker/deploy.sh logs

# Stop and clean up
./docker/deploy.sh stop
./docker/deploy.sh clean
```

## 📋 Available Commands

```bash
# Build the Docker image
docker-compose build

# Start the application
docker-compose up -d

# View logs
docker-compose logs -f rag-app

# Stop the application
docker-compose down

# Complete cleanup (removes volumes too)
docker-compose down -v
```

## 🌐 Access

Once started, access the application at: **http://localhost:8000**

## 📁 File Structure

- **`Dockerfile`** - Simple single-stage Docker image
- **`docker-compose.yml`** - Main configuration with persistent volumes
- **`docker-compose.minimal.yml`** - Quickest setup, no data persistence
- **`docker/deploy.sh`** - Simple deployment script
- **`.dockerignore`** - Excludes unnecessary files from image

## � Configuration

The Docker setup automatically:
- Installs Python dependencies from `pyproject.toml`
- Mounts your `data/` directory (read-only)
- Mounts your `config.yaml` file
- Creates persistent volumes for logs and vector store
- Exposes port 8000
- Includes health checks

## � Troubleshooting

### Port already in use
```bash
# Check what's using port 8000
lsof -i :8000

# Use a different port
docker-compose up -p 8001:8000
```

### Permission issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER ./data ./logs
```

### Clean restart
```bash
./docker/deploy.sh clean
./docker/deploy.sh build
./docker/deploy.sh start
```

This setup prioritizes simplicity and ease of use over advanced features.