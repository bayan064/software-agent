FROM python:3.11-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# 更换为国内镜像源（清华大学镜像源）
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources \
    && sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources

# 安装 Java 21 和 curl（Debian trixie 默认使用 Java 21）
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-21-jdk \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置 Java 环境变量
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

WORKDIR /app

# 复制并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制项目所有文件
COPY . .

# 创建输出目录
RUN mkdir -p /app/output

EXPOSE 8000

CMD ["python", "server.py"]