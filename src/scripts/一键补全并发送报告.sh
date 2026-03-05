#!/bin/bash
# 一键补全关联 + 分析报告 + 发送邮件
# 需在本地终端执行（网络可达 MatrixOne 和 SMTP）
# 用法: ./一键补全并发送报告.sh [收件人邮箱]

set -e
cd "$(dirname "$0")/.."

REPO_OWNER="${REPO_OWNER:-matrixorigin}"
REPO_NAME="${REPO_NAME:-matrixone}"
EMAIL="${1:-}"

if [ -z "$EMAIL" ]; then
  EMAIL="${DEFAULT_EMAIL_TO:-}"
  if [ -z "$EMAIL" ]; then
    echo "用法: $0 <收件人邮箱>"
    echo "示例: $0 wupeng@matrixorigin.cn"
    echo "或设置环境变量 DEFAULT_EMAIL_TO"
    exit 1
  fi
fi

echo "============================================================"
echo "GitHub Issue 智能管理系统 - 一键补全并发送报告"
echo "============================================================"
echo "仓库: $REPO_OWNER/$REPO_NAME"
echo "收件人: $EMAIL"
echo "============================================================"

echo ""
echo "执行：关联补全 + 日报/进度/多维度报告 + 邮件发送"
echo ""
python3 auto_run.py --repo-owner "$REPO_OWNER" --repo-name "$REPO_NAME" \
  --skip-sync --supplement-relations --multi-report --email "$EMAIL"

echo ""
echo "============================================================"
echo "✅ 全部完成"
echo "============================================================"
