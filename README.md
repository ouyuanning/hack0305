# GitHub Issue 智能管理系统 (Go + moi-core)

本项目已基于 moi-core 重写为 Go 版本，通过 moi-core Go SDK 使用 Catalog/Mowl/LLM/Volume/KB 等能力。

## 目录结构

- `cmd/issuectl` CLI 工具
- `cmd/issue-worker` Worker 进程，注册自定义 WorkItem
- `internal/` 业务实现

## 快速开始

1. 准备配置

```bash
cp config.example.yaml config.yaml
```

2. 运行 worker

```bash
go run ./go/cmd/issue-worker -config config.yaml
```

3. 安装工作流

```bash
go run ./go/cmd/issuectl -config config.yaml workflow install
```

4. 触发运行

```bash
go run ./go/cmd/issuectl -config config.yaml run wf-001-issue-sync --repo matrixorigin/matrixone
```

生成草稿示例：

```bash
go run ./go/cmd/issuectl -config config.yaml run wf-003-issue-draft --repo matrixorigin/matrixflow --user-input "查询超时，需要优化性能" --images "/tmp/a.png,/tmp/b.png"
```

## 说明

- 数据存储在 Volume，按 `repos/{owner}/{repo}` 路径组织
- `latest/manifest.json` 记录最新快照引用
- 报告输出兼容原 Python 版本命名
