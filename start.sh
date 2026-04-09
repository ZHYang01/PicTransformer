#!/bin/bash

# PicTransformer 启动脚本

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting PicTransformer..."

# 检查端口是否已被占用
if lsof -i :5000 > /dev/null 2>&1; then
    echo "Port 5000 is already in use. PicTransformer might already be running."
    echo "Open http://127.0.0.1:5000 in your browser."
    exit 1
fi

# 启动应用
python3 app.py
