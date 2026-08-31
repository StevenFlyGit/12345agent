#!/bin/bash
# ============================================================
#  12345agent frontend dev server launcher (macOS)
#  双击此文件即可在 Terminal 中打开 frontend 并启动前端开发服务器。
#  启动后访问（Vite 默认地址）：
#      http://localhost:5173
#  停止服务：在 Terminal 中按 Ctrl+C
#  前置要求：已安装 Node.js，并已执行过 npm install。
# ============================================================

# 获取脚本所在目录（兼容双击启动，工作目录可能是用户主目录）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

if [ ! -d "$FRONTEND_DIR" ]; then
  echo "❌ 未找到 frontend 目录：$FRONTEND_DIR"
  echo "   请确认本脚本与 frontend/ 处于同一项目根目录。"
  exit 1
fi

cd "$FRONTEND_DIR" || exit 1

# 启动前端开发服务器（npm run dev 保持运行，终端会一直显示日志直到 Ctrl+C）
exec npm run dev
