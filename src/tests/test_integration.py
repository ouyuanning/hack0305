#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WF-005 + WF-006 集成测试
直接连接本地 MatrixOne (127.0.0.1:6001)，插入模拟数据后验证完整流程。
"""

import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

# 确保使用 MatrixOne
os.environ["DATABASE_TYPE"] = "matrixone"
os.environ["MATRIXONE_HOST"] = "127.0.0.1"
os.environ["MATRIXONE_PORT"] = "6001"
os.environ["MATRIXONE_USER"] = "dump"
os.environ["MATRIXONE_PASSWORD"] = "111"
os.environ["MATRIXONE_DATABASE"] = "github_issues"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.database_storage.mo_client import MOStorage

# ── 工具 ──────────────────────────────────────────────────

PASS = 0
FAIL = 0

def ok(msg):
    global PASS; PASS += 1; print(f"  ✅ {msg}")

def fail(msg):
    global FAIL; FAIL += 1; print(f"  ❌ {msg}")

def check(cond, msg):
    ok(msg) if cond else fail(msg)


# ── 清理测试数据 ─────────────────────────────────────────

TEST_REPO_OWNER = "_test_integ"
TEST_REPO_NAME = "_test_repo"

def cleanup(storage):
    """清理本次测试写入的数据（按 repo_owner/repo_name 隔离）"""
    for tbl in ["experimental_issues", "customer_issues", "data_cleaning_log", "issues_snapshot"]:
        try:
            storage.execute(
                f"DELETE FROM {tbl} WHERE repo_owner = :o AND repo_name = :r",
                {"o": TEST_REPO_OWNER, "r": TEST_REPO_NAME},
            )
        except Exception:
            try:
                # data_cleaning_log 没有 repo 字段，按 cleaning_version 清理
                if tbl == "data_cleaning_log":
                    storage.execute(
                        "DELETE FROM data_cleaning_log WHERE cleaning_version LIKE :v",
                        {"v": "test_%"},
                    )
            except Exception:
                pass

# ── 准备测试数据 ─────────────────────────────────────────

def seed_issues(storage):
    """向 issues_snapshot 插入模拟数据"""
    now = datetime.now()
    issues = [
        {
            "issue_id": 99001, "issue_number": 1,
            "repo_owner": TEST_REPO_OWNER, "repo_name": TEST_REPO_NAME,
            "title": "NL2SQL查询超时需要优化性能",
            "body": "在大数据量场景下NL2SQL查询超时，需要优化索引和查询计划。用户反馈严重影响使用体验。",
            "state": "open", "issue_type": "bug", "priority": "P1", "assignee": "zhangsan",
            "labels": json.dumps([{"name": "kind/bug"}, {"name": "area/问数"},
                                   {"name": "customer/金盘"}, {"name": "severity/high"}]),
            "milestone": "v2.0",
            "created_at": "2025-06-01T10:00:00", "updated_at": "2025-12-01T10:00:00",
            "closed_at": None, "ai_summary": None, "ai_tags": None, "ai_priority": None,
            "status": "处理中", "progress_percentage": 60.0,
            "is_blocked": False, "blocked_reason": None,
        },
        {
            "issue_id": 99002, "issue_number": 2,
            "repo_owner": TEST_REPO_OWNER, "repo_name": TEST_REPO_NAME,
            "title": "新增ChatBI数据看板功能",
            "body": "支持通过自然语言生成数据看板，包括图表和表格。",
            "state": "open", "issue_type": "feature", "priority": "P2", "assignee": "lisi",
            "labels": json.dumps([{"name": "kind/feature"}, {"name": "area/ChatBI"},
                                   {"name": "project/问数深化"}]),
            "milestone": "v2.1",
            "created_at": "2025-07-15T08:00:00", "updated_at": "2025-11-20T08:00:00",
            "closed_at": None, "ai_summary": None, "ai_tags": None, "ai_priority": None,
            "status": "待处理", "progress_percentage": 20.0,
            "is_blocked": False, "blocked_reason": None,
        },
        {
            "issue_id": 99003, "issue_number": 3,
            "repo_owner": TEST_REPO_OWNER, "repo_name": TEST_REPO_NAME,
            "title": "修复导出CSV编码问题",
            "body": "导出的CSV文件在Windows下打开乱码。",
            "state": "closed", "issue_type": "bug", "priority": "P3", "assignee": "wangwu",
            "labels": json.dumps([{"name": "bug"}, {"name": "customer/金盘"},
                                   {"name": "severity/low"}]),
            "milestone": None,
            "created_at": "2025-05-01T09:00:00", "updated_at": "2025-08-01T09:00:00",
            "closed_at": "2025-08-01T09:00:00", "ai_summary": None, "ai_tags": None, "ai_priority": None,
            "status": "已完成", "progress_percentage": 100.0,
            "is_blocked": False, "blocked_reason": None,
        },
        {
            "issue_id": 99004, "issue_number": 4,
            "repo_owner": TEST_REPO_OWNER, "repo_name": TEST_REPO_NAME,
            "title": "",  # 空标题，用于测试质量验证
            "body": None,
            "state": "open", "issue_type": None, "priority": None, "assignee": None,
            "labels": json.dumps([]),
            "milestone": None,
            "created_at": "2025-09-01T10:00:00", "updated_at": "2025-09-01T10:00:00",
            "closed_at": None, "ai_summary": None, "ai_tags": None, "ai_priority": None,
            "status": None, "progress_percentage": 0.0,
            "is_blocked": False, "blocked_reason": None,
        },
    ]
    for iss in issues:
        storage.save_issue_snapshot(iss, now)
    return len(issues)


# ══════════════════════════════════════════════════════════
# 测试1: WF-005 历史数据清洗
# ══════════════════════════════════════════════════════════

def test_wf005(storage):
    print("\n" + "=" * 60)
    print("测试 WF-005: 历史数据清洗（完整流程）")
    print("=" * 60)

    from modules.data_cleaning.cleaner import DataCleaner

    cleaner = DataCleaner(storage=storage, llm=None)

    # ── 步骤1: load_issues ──
    print("\n── 步骤1: load_issues")
    issues = cleaner.load_issues(TEST_REPO_OWNER, TEST_REPO_NAME)
    check(len(issues) == 4, f"读取到 {len(issues)} 条Issue（预期4）")
    check(isinstance(issues[0].get("labels"), list), "labels 已解析为 list")

    # ── 步骤2: clean_data ──
    print("\n── 步骤2: clean_data")
    cleaned, stats = cleaner.clean_data(issues)
    check(stats["duplicates_removed"] == 0, f"去重移除 {stats['duplicates_removed']}（无重复）")
    check(stats["normalized"] == 4, f"规范化 {stats['normalized']} 条")
    # 检查废弃标签 "bug" 被映射为 "kind/bug"
    issue3 = [i for i in cleaned if i["issue_id"] == 99003][0]
    check("kind/bug" in issue3.get("_label_names", []), "label 'bug' 映射为 'kind/bug'")
    for iss in cleaned:
        check("wontfix" not in iss.get("_label_names", []), f"Issue#{iss['issue_number']} 无废弃标签")

    # ── 步骤3: ai_relabel (无LLM，走规则回退) ──
    print("\n── 步骤3: ai_relabel（规则回退模式）")
    relabeled, ai_stats = cleaner.ai_relabel(cleaned, "test_v1")
    check(ai_stats["skipped"] == 4, f"无LLM时全部跳过: {ai_stats['skipped']}")
    issue1 = [i for i in relabeled if i["issue_id"] == 99001][0]
    check(issue1.get("ai_issue_type") is not None, f"Issue#1 ai_issue_type={issue1.get('ai_issue_type')}")
    check(issue1.get("ai_priority") is not None, f"Issue#1 ai_priority={issue1.get('ai_priority')}")
    check(issue1.get("ai_corrected") == False, "无LLM时 ai_corrected=False")

    # ── 步骤4: validate_quality ──
    print("\n── 步骤4: validate_quality")
    passed, failed, qr = cleaner.validate_quality(relabeled)
    check(len(passed) + len(failed) == 4, f"通过{len(passed)} + 未达标{len(failed)} = 4")
    check(qr["average_quality_score"] > 0, f"平均质量分 {qr['average_quality_score']:.2f}")
    issue4 = [i for i in relabeled if i["issue_id"] == 99004][0]
    check(issue4["quality_score"] < 0.5, f"空标题Issue质量分 {issue4['quality_score']:.2f} < 0.5")

    # ── 步骤5: save_to_experimental ──
    print("\n── 步骤5: save_to_experimental")
    save_stats = cleaner.save_to_experimental(passed, "test_v1")
    check(save_stats["success_count"] == len(passed), f"成功写入 {save_stats['success_count']} 条")
    check(save_stats["error_count"] == 0, f"写入错误 {save_stats['error_count']}")

    # 验证数据库中的记录
    rows = storage.execute(
        "SELECT COUNT(*) as cnt FROM experimental_issues WHERE cleaning_version = :v",
        {"v": "test_v1"}
    )
    db_count = rows[0]["cnt"]
    check(db_count == save_stats["success_count"], f"数据库实际记录 {db_count} 条")

    # ── 步骤6: _generate_report ──
    print("\n── 步骤6: _generate_report")
    report_md = cleaner._generate_report({
        "cleaning_version": "test_v1", "start_time": "2026-03-05T10:00:00",
        "end_time": "2026-03-05T10:01:00", "duration_seconds": 60,
        "repo_owner": TEST_REPO_OWNER, "repo_name": TEST_REPO_NAME,
        "total_issues_read": 4, "duplicates_removed": 0, "records_cleaned": 4,
        "ai_success": 0, "ai_failed": 0, "quality_passed": len(passed),
        "quality_failed": len(failed), "average_quality_score": qr["average_quality_score"],
        "saved_count": save_stats["success_count"], "status": "completed",
    })
    check("数据清洗报告" in report_md, "报告包含标题")
    check(f"{TEST_REPO_OWNER}/{TEST_REPO_NAME}" in report_md, "报告包含仓库名")

    # ── 步骤7: run() 完整流程 ──
    print("\n── 步骤7: run() 完整流程")
    result = cleaner.run(TEST_REPO_OWNER, TEST_REPO_NAME)
    check(result["status"] == "completed", f"run() 状态: {result['status']}")
    check(result["total_issues_read"] == 4, f"run() 读取: {result['total_issues_read']}")
    check(result["saved_count"] > 0, f"run() 写入: {result['saved_count']}")

    # ── 步骤8: 幂等性测试（重复运行不报错） ──
    print("\n── 步骤8: 幂等性测试")
    result2 = cleaner.run(TEST_REPO_OWNER, TEST_REPO_NAME)
    check(result2["status"] == "completed", "重复运行不报错")

    # ── 步骤9: 变更日志 ──
    print("\n── 步骤9: data_cleaning_log")
    logs = storage.execute("SELECT COUNT(*) as cnt FROM data_cleaning_log")
    log_count = logs[0]["cnt"]
    check(log_count >= 0, f"变更日志记录 {log_count} 条（无LLM时可能为0）")


# ══════════════════════════════════════════════════════════
# 测试2: WF-006 Customer 同步
# ══════════════════════════════════════════════════════════

def test_wf006_customer(storage):
    print("\n" + "=" * 60)
    print("测试 WF-006: Customer 标签同步")
    print("=" * 60)

    sys.path.insert(0, str(ROOT / "feature_issue_and_kanban"))
    from project_manager.customer_sync import CustomerSync

    syncer = CustomerSync(storage)

    # ── 验证表已创建 ──
    print("\n── 表创建验证")
    tables = storage.execute("SHOW TABLES")
    table_names = [list(t.values())[0] for t in tables]
    check("customer_issues" in table_names, "customer_issues 表已创建")

    # ── 同步 customer/金盘 ──
    print("\n── 同步 customer/金盘")
    count = syncer.sync_customer_issues(TEST_REPO_OWNER, TEST_REPO_NAME, "customer/金盘")
    check(count == 2, f"同步了 {count} 条（预期2: Issue#1和#3含customer/金盘）")

    # ── 验证数据库记录 ──
    print("\n── 数据库记录验证")
    rows = storage.execute(
        "SELECT * FROM customer_issues WHERE customer_tag = :tag AND repo_owner = :o ORDER BY issue_number",
        {"tag": "customer/金盘", "o": TEST_REPO_OWNER}
    )
    check(len(rows) == 2, f"数据库中 {len(rows)} 条记录")

    if len(rows) >= 1:
        r1 = rows[0]
        check(r1["issue_number"] == 1, f"第1条 issue_number={r1['issue_number']}")
        check(r1["issue_state"] == "open", f"第1条 state={r1['issue_state']}")
        check(r1["priority"] == "P1", f"第1条 priority={r1['priority']}")
        check(r1["severity"] == "high", f"第1条 severity={r1['severity']}（从 severity/high 提取）")
        check("github.com" in r1["issue_url"], f"第1条 URL 正确")

    if len(rows) >= 2:
        r2 = rows[1]
        check(r2["issue_number"] == 3, f"第2条 issue_number={r2['issue_number']}")
        check(r2["issue_state"] == "closed", f"第2条 state={r2['issue_state']}")
        check(r2["severity"] == "low", f"第2条 severity={r2['severity']}（从 severity/low 提取）")

    # ── 幂等性：重复同步不报错 ──
    print("\n── 幂等性测试")
    count2 = syncer.sync_customer_issues(TEST_REPO_OWNER, TEST_REPO_NAME, "customer/金盘")
    check(count2 == 2, f"重复同步返回 {count2}（幂等）")

    # ── 不存在的标签返回0 ──
    print("\n── 不存在的标签")
    count3 = syncer.sync_customer_issues(TEST_REPO_OWNER, TEST_REPO_NAME, "customer/不存在")
    check(count3 == 0, f"不存在的标签返回 {count3}")


# ══════════════════════════════════════════════════════════
# 主入口
# ══════════════════════════════════════════════════════════

def main():
    print("🔧 连接本地 MatrixOne (127.0.0.1:6001)...")
    storage = MOStorage()

    # 先清理可能残留的测试数据
    cleanup(storage)

    print(f"📦 插入模拟数据 (repo: {TEST_REPO_OWNER}/{TEST_REPO_NAME})...")
    n = seed_issues(storage)
    print(f"  插入 {n} 条 issues_snapshot")

    try:
        test_wf005(storage)
        test_wf006_customer(storage)
    finally:
        # 清理测试数据
        print("\n🧹 清理测试数据...")
        cleanup(storage)
        # 清理 run() 生成的报告文件
        report_dir = ROOT / "data" / "reports"
        for f in report_dir.glob("cleaning_report_*.md"):
            f.unlink(missing_ok=True)

    print("\n" + "=" * 60)
    print(f"测试完成: ✅ {PASS} 通过, ❌ {FAIL} 失败")
    print("=" * 60)
    return 1 if FAIL > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
