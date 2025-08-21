# 第一阶段：安装依赖（利用缓存）
FROM python:3.12.7-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir -r requirements.txt

# 第二阶段：运行环境
FROM python:3.12.7-slim
WORKDIR /app

# 从builder复制已安装的依赖
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# 复制应用代码和证书文件
COPY . .
COPY deepspring-tech.com.key .
COPY deepspring-tech.com.pem .

EXPOSE 5000
# 设置 Gunicorn 启动命令
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "script:app", \
     "--keyfile", "deepspring-tech.com.key", \
     "--certfile", "deepspring-tech.com.pem"]
