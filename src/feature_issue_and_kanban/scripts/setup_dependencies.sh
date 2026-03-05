#!/bin/bash
# 自动检测系统并选择 python 命令
# macOS/Linux：优先用 python3（macOS 通常无 python 命令）
# Windows Git Bash：尝试 python3 或 python

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "❌ 未找到 python 或 python3，请先安装 Python 3"
    exit 1
fi

echo "🔍 使用: $PYTHON ($($PYTHON --version 2>&1))"
echo ""
exec "$PYTHON" "$SCRIPT_DIR/setup_dependencies.py"
