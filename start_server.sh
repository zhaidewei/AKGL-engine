#!/bin/bash
# 启动学习路径浏览服务器

# 检查是否安装了依赖
if ! python3 -c "import flask" 2>/dev/null; then
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
fi

# 启动服务器（默认使用 8080 端口）
PORT=${1:-8080}
echo "启动服务器..."
echo "访问 http://localhost:$PORT 查看学习路径"
python3 serving/server.py $PORT

