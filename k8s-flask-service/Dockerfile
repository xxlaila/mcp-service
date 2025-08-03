# 使用官方的 Python 镜像作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

COPY --chmod=755 kubectl /usr/local/bin/kubectl
COPY --chmod=755 dump.sh /app/dump.sh

# 复制 requirements.txt 并安装依赖
COPY requirements.txt .
RUN pip install -r requirements.txt && \
    rm -rf /root/.cache/pip && \
    apt-get update && \
    apt-get install unzip wget curl -y && \
    wget https://github.com/adoptium/temurin8-binaries/releases/download/jdk8u312-b07/OpenJDK8U-jdk_x64_linux_hotspot_8u312b07.tar.gz && \
    tar -zxvf OpenJDK8U-jdk_x64_linux_hotspot_8u312b07.tar.gz && \
    mv jdk8u312-b07 /usr/local/jdk8 && \
    rm -rf OpenJDK8U-jdk_x64_linux_hotspot_8u312b07.tar.gz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/local/jdk8 PYTHONUNBUFFERED=1
ENV PATH=${JAVA_HOME}/bin:/opt/venv/bin:${PATH}

# 复制当前目录下的所有文件到工作目录
COPY . .

# 设置容器启动时执行的命令
CMD ["python", "main.py"]