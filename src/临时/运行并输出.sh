#!/bin/bash
# GitHub Issue 智能管理系统 - 本地运行脚本
# 使用 MatrixOne 存储，在您本机执行（IP 已加入白名单）

cd "$(dirname "$0")"

echo "============================================================"
echo "GitHub Issue 智能管理系统 - 开始运行"
echo "============================================================"

python3 auto_run.py --repo-owner matrixorigin --repo-name matrixone --skip-email

echo ""
echo "按任意键关闭..."
read -n 1
