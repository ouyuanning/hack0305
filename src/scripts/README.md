# 辅助脚本目录

本目录存放各类辅助脚本，按用途分类说明如下。

## 数据补全与报告

| 脚本 | 用途 |
|------|------|
| `supplement_relations.py` | 关联关系补全：从已入库 Issue 重新提取关联关系并保存 |
| `repair_ai_parse.py` | AI 解析补全：针对解析失败/空的 Issue 重新解析 |
| `run_full_repair_and_analysis.py` | 补全 + 报告一体化：关联补全 → AI 补全 → 日报/进度/多维度报告 → 邮件发送 |
| `run_analysis.py` | 分析运行：同步完成后生成报告、可发邮件 |
| `run_extensible_analysis.py` | 可扩展分析独立运行：标签/模块/趋势等，配置驱动 |
| `run_ai_analysis.py` | AI 驱动分析：项目推进 + 横向关联（使用配置的 AI 如千问，适用 matrixflow） |
| `一键补全并发送报告.sh` | 一键执行关联补全 + 多维度报告 + 邮件发送 |

## 检查与诊断

| 脚本 | 用途 |
|------|------|
| `check_config.py` | 配置检查：检查所有配置项、数据库连接、GitHub/AI 可用性 |
| `check_and_send.py` | 配置检查与邮件发送：检查通过后可选发送报告 |
| `test_analysis.py` | 可扩展分析诊断：5 步测试，验证分析是否正常 |
| `test_db_connection.py` | 数据库连接测试：MatrixOne/MySQL 连接诊断 |

## 查询与维护

| 脚本 | 用途 |
|------|------|
| `query_labels_sample.py` | Labels 查询样例：按客户等条件查询标签存储 |
| `migrate_issue_id_to_bigint.py` | 数据库迁移：将 issue_id 字段迁移为 BIGINT |

## 运行方式

所有脚本均需在**项目根目录**下执行，例如：

```bash
cd /path/to/GitHub_Issue_智能管理系统
python3 scripts/check_config.py
python3 scripts/supplement_relations.py --repo-owner matrixorigin --repo-name matrixone
python3 scripts/run_ai_analysis.py --repo-owner matrixorigin --repo-name matrixflow  # 使用配置的 AI
./scripts/一键补全并发送报告.sh user@example.com
```

或在任意目录通过模块方式运行：

```bash
python3 -m scripts.check_config
python3 -m scripts.supplement_relations --repo-owner matrixorigin --repo-name matrixone
```
