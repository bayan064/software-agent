#!/bin/bash
# docker/scripts/entrypoint.sh

set -e

echo "=========================================="
echo "Software Engineering Agent Starting..."
echo "=========================================="

# 检查 Java 环境
echo "Checking Java environment..."
java -version

# 检查 Python 环境
echo "Checking Python environment..."
python --version

# 检查 API Key
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠️  Warning: DEEPSEEK_API_KEY is not set!"
    echo "   Please set it in .env file or environment variable"
fi

# 运行环境检查
python check_java_env.py

# 启动服务
echo "Starting FastAPI server..."
exec "$@"