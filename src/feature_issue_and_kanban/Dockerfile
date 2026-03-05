# feature_issue_and_kanban 云端部署 Dockerfile
FROM python:3.9-slim

WORKDIR /app

# 复制项目
COPY . /app

# 安装主项目依赖
RUN pip install -r requirements.txt -q 2>/dev/null || true

# 安装本模块依赖（按环境）
RUN CLOUD_DEPLOYMENT=true python feature_issue_and_kanban/scripts/setup_dependencies.py

EXPOSE 8767

ENV CLOUD_DEPLOYMENT=true

# 需在项目根目录构建
CMD ["python", "feature_issue_and_kanban/services/unified_interface.py"]
