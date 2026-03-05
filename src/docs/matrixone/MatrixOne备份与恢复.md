# MatrixOne 备份与恢复要点

本文档提炼自 [MatrixOne 官方备份与恢复概述](https://docs.matrixorigin.cn/v26.3.0.6/MatrixOne/Maintain/backup-restore/backup-restore-overview/) 及项目内《MatrixOne 备份方法总结》，便于日常操作与误删/故障恢复。

---

## 一、备份策略原则（官方建议）

- **备份频率**：全量备份 + 增量备份结合；全量占用空间大但恢复快。
- **备份存储**：备份数据放在安全位置（离线或云存储），避免与生产同故障域。
- **保留期**：按合规与业务定保留策略，便于历史回溯。
- **恢复顺序**：停止数据库（如需）→ 选择备份类型 → 还原备份 → 应用重做日志（若有）→ 启动并测试。

---

## 二、备份方法概览

MatrixOne 提供 **逻辑备份** 与 **物理备份** 两类，本系统使用 MatrixOne（含 Serverless）时以 **SQL 快照** 为主。

| 方式 | 适用场景 | 说明 |
|------|----------|------|
| **SELECT INTO OUTFILE** | 单表、小规模 | 导出为文件，仅服务端路径；恢复用 LOAD DATA。 |
| **mo-dump** | 自建实例、整库逻辑备份 | 类似 mysqldump，生成可回放 SQL；Serverless 无法在控制台执行命令行。 |
| **mo_br / mo-backup** | 自建实例、物理备份 | 快照 + PITR，需企业版/联系客户经理获取工具。 |
| **SQL 快照（CREATE SNAPSHOT）** | **本系统推荐** | 控制台/SQL 即可，适合 Serverless 与日常定时备份。 |

---

## 三、本系统推荐：SQL 快照备份与恢复

使用 **MatrixOne Intelligence Serverless** 时，无法直接使用 `mo-dump`、`mo_br`，应使用 **SQL 快照** 作为定时备份手段，并在大操作前手动打快照以防误删。

### 3.1 创建快照（推荐：只为当前账户）

与官方推荐一致，**只为当前账户创建快照**：

```sql
CREATE SNAPSHOT snap_20260224 FOR ACCOUNT;
```

同步前防误删的标准流程：**每次跑同步脚本前先打一个快照**，例如：

```sql
CREATE SNAPSHOT snap_20260224_before_sync FOR ACCOUNT;
```

本系统会在每次执行同步前自动创建带 `_before_sync` 后缀的快照（仅当使用 MatrixOne 时）；也可用脚本手动创建：`python3 scripts/backup_matrixone.py --before-sync`。快照名建议带日期时间，便于识别与保留策略。

### 3.2 查看快照

```sql
SHOW SNAPSHOTS;
```

可查看当前账号下所有快照及时间、级别等。

### 3.3 从快照恢复

- **恢复整个数据库**：
  ```sql
  RESTORE DATABASE github_issues FROM SNAPSHOT snap_YYYYMMDD_HHMM;
  ```
- **仅恢复某张表**：
  ```sql
  RESTORE TABLE github_issues.issues_snapshot FROM SNAPSHOT snap_YYYYMMDD_HHMM;
  ```

恢复前请确认业务已停止写入或可接受数据回滚，避免二次覆盖。

### 3.4 删除快照

```sql
 DROP SNAPSHOT snap_YYYYMMDD_HHMM;
```

按保留策略定期清理旧快照，控制存储与列表可读性。

---

## 四、逻辑备份（可选，自建实例）

- **SELECT INTO OUTFILE**：单表导出到服务端路径，恢复用 `LOAD DATA INFILE`。适合小规模、临时备份。
- **mo-dump**：在**自建 MatrixOne 服务器**上执行，导出整库为 SQL 文件，恢复用 `mysql`/客户端执行该 SQL。云端 Serverless 无法直接使用。

---

## 五、物理备份（自建 + 企业版）

- **mo_br**：常规物理备份、快照备份、PITR。需在自建环境使用。
- **mo-backup**：企业级物理备份与恢复工具，需联系 MatrixOne 客户经理获取。

---

## 六、误删/故障时的建议流程

1. **立刻在 SQL 编辑器打一个当前快照**（防止继续丢数据）：
   ```sql
   CREATE SNAPSHOT snap_emergency_YYYYMMDD FOR DATABASE github_issues;
   SHOW SNAPSHOTS;
   ```
2. 确认 Serverless 是否支持 `CREATE SNAPSHOT`（若不支持，需依赖控制台/企业版其他备份能力）。
3. 如需回滚：使用 `RESTORE DATABASE` 或 `RESTORE TABLE` 从最近可用快照恢复。
4. 今后：**每次大操作前先打快照**，并把 **数据库备份作为定时事项** 单独执行（见项目内「定时事项」说明）。

---

## 七、与本系统的配合

- **存储方式**：与官方一致，**只为当前账户创建快照**：`CREATE SNAPSHOT snap_xxx FOR ACCOUNT;`（脚本与 main 同步前快照均采用此方式）。
- **防误删**：每次执行同步前会自动打快照（名称带 `_before_sync`），若同步出问题可执行：
  `RESTORE DATABASE github_issues FROM SNAPSHOT snap_YYYYMMDD_HHMM_before_sync;` 或按表恢复。
- **独立备份脚本** `scripts/backup_matrixone.py`：可单独定时执行；支持 `--before-sync` 手动打同步前快照。
- **备份保留**：`config/config.py` 中 `BACKUP_SNAPSHOT_RETENTION_DAYS`（默认 7 天），创建新快照后会自动 DROP 超过该天数的快照；设为 0 表示不自动删除。
- 可选在自动运行流程中加 `--run-backup`，在同步/报告之后再执行一次快照（详见 [自动运行脚本说明](../自动运行脚本说明.md)）。

---

## 八、参考链接

- [备份与恢复概述](https://docs.matrixorigin.cn/v26.3.0.6/MatrixOne/Maintain/backup-restore/backup-restore-overview/)
- [CREATE SNAPSHOT](https://docs.matrixorigin.cn/v26.3.0.6/MatrixOne/Reference/SQL-Reference/Data-Definition-Language/create-snapshot/)
- [RESTORE FROM SNAPSHOT](https://docs.matrixorigin.cn/v26.3.0.6/MatrixOne/Reference/SQL-Reference/Data-Definition-Language/restore-snapshot/)
- [mo-dump 导出](https://docs.matrixorigin.cn/v26.3.0.6/MatrixOne/Develop/export-data/modump/)
- [mo_br 使用指南](https://docs.matrixorigin.cn/v26.3.0.6/MatrixOne/Maintain/backup-restore/mobr-backup-restore/mobr/)

---

**最后更新**：2026-02-24
