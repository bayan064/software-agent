#!/bin/bash
# docker/scripts/healthcheck.sh

# 检查服务是否健康
curl -f http://localhost:8000/docs || exit 1

# 检查 Java 环境是否可用
java -version > /dev/null 2>&1 || exit 1

echo "Service is healthy"
exit 0