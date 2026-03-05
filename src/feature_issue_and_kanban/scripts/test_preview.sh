#!/bin/bash
# 测试：模拟到生成预览网页，不创建 GitHub Issue
# 用法：
#   1. 纯预览（不调用 AI/DB）：./test_preview.sh --demo
#   2. AI 生成 + 预览：./test_preview.sh --input "描述"
#   3. 指定标题/类型/标签：./test_preview.sh --title "xxx" --type "Doc Request" --labels "kind/docs"

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

PYTHON=python3
command -v python3 &>/dev/null || PYTHON=python

OUTPUT_HTML="${ROOT}/feature_issue_and_kanban/preview.html"
REPO="matrixorigin/matrixflow"

if [[ "$1" == "--demo" ]]; then
    echo "📄 模式：纯预览（不调用 AI/DB，使用示例数据）"
    $PYTHON feature_issue_and_kanban/scripts/generate_preview_only.py \
        --repo "$REPO" \
        --title "【测试】示例 Issue - 单据检索 PRD" \
        --type "Doc Request" \
        --labels "kind/docs,area/问数,project/问数深化" \
        --assignees "wupeng" \
        --output-html "$OUTPUT_HTML" \
        --success-msg
else
    echo "📄 模式：AI 生成 + 预览（不创建 GitHub Issue）"
    INPUT=""
    if [[ "$1" == "--input" && -n "$2" ]]; then
        INPUT="$2"
    elif [[ -n "$1" && "$1" != --* ]]; then
        INPUT="$1"
    fi
    if [[ -z "$INPUT" ]]; then
        INPUT="单据检索 PRD 需要补充字段说明"
        echo "未提供 --input，使用示例：$INPUT"
    fi
    $PYTHON feature_issue_and_kanban/scripts/create_issue_interactive.py \
        --input "$INPUT" \
        --repo "$REPO" \
        --preview \
        --output-html "$OUTPUT_HTML"
fi

echo ""
echo "✅ 预览已生成：$OUTPUT_HTML"
echo "请在浏览器中打开查看和调整，确认后请使用 create_issue_interactive.py（不加 --preview）手动创建。"
echo ""
echo "打开预览："
echo "  open $OUTPUT_HTML"
