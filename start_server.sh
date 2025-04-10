#!/bin/bash

# 检查并终止占用 8000 端口的进程
PORT=8000
PID=$(lsof -ti:$PORT)
if [ ! -z "$PID" ]; then
    echo "Port $PORT is in use by process $PID. Killing it..."
    kill -9 $PID
    sleep 1
    echo "Process killed."
fi

# 切换到项目目录
cd ~/ai_voice_demo

# 初始化conda并激活环境
eval "$(conda shell.bash hook)"
conda activate cosyvoice

# 设置Python路径，确保能找到所有需要的模块
export PYTHONPATH=$PYTHONPATH:~/ai_voice_demo:~/CosyVoice:~/CosyVoice/third_party/Matcha-TTS

# 添加环境变量来控制是否预加载模型(可选)
export PRELOAD_MODEL=${PRELOAD_MODEL:-1}

# 设置更详细的日志记录以便追踪分段合成过程
export LOG_LEVEL=${LOG_LEVEL:-debug}

# 设置环境变量以优化课件处理
# 提高MoviePy处理视频时的同步精度
export MOVIEPY_SYNC_PRECISION=0.01
# 增加音频分析的精确度
export FFMPEG_EXTRA_ARGS="-af aresample=async=1000"

# 使用--noinit选项避免在脚本中加载模型

# 如果需要重置数据库，取消下面两行的注释
# echo "重置数据库并导入预置声音..."
# python reset_database.py --confirm && python import_preset_voices.py --noinit

echo "导入预置声音..."
python import_preset_voices.py --noinit

echo "启动服务器..."
# 启用更详细的日志以便调试合成问题
uvicorn ai_voice_server.main:app --host 0.0.0.0 --port 8000 --log-level $LOG_LEVEL