#!/bin/bash
# ============================================================
#  12345agent backend venv launcher (macOS)
#  双击此文件即可在 Terminal 中打开 backend 并启动后端服务。
#  启动后访问：
#      http://127.0.0.1:8000/health
#      http://127.0.0.1:8000/docs
#  停止服务：在 Terminal 中按 Ctrl+C
# ============================================================

# 获取脚本所在目录（兼容双击启动，工作目录可能是用户主目录）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

if [ ! -d "$BACKEND_DIR" ]; then
  echo "❌ 未找到 backend 目录：$BACKEND_DIR"
  echo "   请确认本脚本与 backend/ 处于同一项目根目录。"
  exit 1
fi

# 激活虚拟环境（macOS/Linux 的激活脚本在 venv/bin/activate）
ACTIVATE="$BACKEND_DIR/venv/bin/activate"
if [ -f "$ACTIVATE" ]; then
  # shellcheck disable=SC1090
  source "$ACTIVATE"
else
  echo "⚠️  未找到虚拟环境：$ACTIVATE"
  echo "   当前 venv 是 Windows 创建的不兼容 macOS，请先在 backend 目录重建："
  echo "     cd \"$BACKEND_DIR\""
  echo "     python -m venv venv"
  echo "     source venv/bin/activate"
  echo "     pip install -r requirements.txt"
  echo ""
  echo "   为你打开 backend 目录的交互式终端以便手动处理……"
  cd "$BACKEND_DIR" || exit 1
  exec "$SHELL"
fi

cd "$BACKEND_DIR" || exit 1

# 启动后端（--reload 保持运行，终端会一直显示日志直到 Ctrl+C）
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
