# 千问API配置更新总结

**更新日期**：2025-02-21  
**参考文档**：[首次调用千问API](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen#f0577378e8sz4)

---

## ✅ 已完成的更新

### 1. 配置文件更新 (`config/config.py`)

**更新内容**：
- ✅ 支持 `DASHSCOPE_API_KEY` 环境变量（官方推荐）
- ✅ 保持向后兼容 `QWEN_API_KEY` 环境变量
- ✅ API地址更新为兼容模式：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- ✅ 默认模型更新为 `qwen-plus`（推荐）
- ✅ 更新配置验证函数，支持 `DASHSCOPE_API_KEY` 检查

**配置优先级**：
1. `DASHSCOPE_API_KEY` 环境变量（优先）
2. `QWEN_API_KEY` 环境变量（向后兼容）
3. `config/config.py` 中的默认值

### 2. LLM解析模块更新 (`modules/llm_parser/llm_parser.py`)

**更新内容**：
- ✅ 支持OpenAI兼容接口（兼容模式，推荐）
- ✅ 保留DashScope SDK支持（标准API，备用）
- ✅ 自动检测API地址类型，选择最合适的调用方式
- ✅ 改进错误处理和提示信息

**调用方式**：
- **兼容模式**（`/compatible-mode/v1`）：使用OpenAI兼容接口
- **标准API**（`/api/v1`）：使用DashScope SDK

### 3. 文档更新

**更新的文档**：
- ✅ `README.md` - 添加通义千问配置说明
- ✅ `千问API配置说明.md` - 新建，详细配置指南
- ✅ 更新常见问题部分，添加千问API相关问题

---

## 🔧 配置方式

### 推荐方式：环境变量

**macOS/Linux (Zsh)**：
```bash
export DASHSCOPE_API_KEY="your_api_key_here"
echo "export DASHSCOPE_API_KEY='your_api_key_here'" >> ~/.zshrc
source ~/.zshrc
```

**macOS/Linux (Bash)**：
```bash
export DASHSCOPE_API_KEY="your_api_key_here"
echo "export DASHSCOPE_API_KEY='your_api_key_here'" >> ~/.bash_profile
source ~/.bash_profile
```

**验证配置**：
```bash
echo $DASHSCOPE_API_KEY
```

### 获取API Key

1. 访问 [阿里云百炼控制台](https://bailian.console.aliyun.com/)
2. 前往 [密钥管理页面](https://bailian.console.aliyun.com/#/api-key)
3. 创建API Key
4. 详细步骤：参考 [千问API配置说明.md](千问API配置说明.md)

---

## 📊 当前配置状态

**测试结果**：
```
✅ DASHSCOPE_API_KEY: 已配置
✅ QWEN_API_KEY: 已配置（向后兼容）
✅ QWEN_BASE_URL: https://dashscope.aliyuncs.com/compatible-mode/v1
✅ QWEN_MODEL: qwen-plus
```

---

## 🎯 主要改进

### 1. 符合官方推荐

- ✅ 使用 `DASHSCOPE_API_KEY` 环境变量（官方推荐）
- ✅ 使用兼容模式API地址（支持OpenAI兼容接口）
- ✅ 提供详细的配置文档

### 2. 向后兼容

- ✅ 仍然支持 `QWEN_API_KEY` 环境变量
- ✅ 仍然支持DashScope SDK调用方式
- ✅ 现有配置无需修改即可继续使用

### 3. 更好的用户体验

- ✅ 自动选择最合适的API调用方式
- ✅ 改进的错误提示和诊断信息
- ✅ 详细的配置文档和常见问题解答

---

## 📚 相关文档

- [千问API配置说明.md](千问API配置说明.md) - 详细配置指南
- [README.md](README.md) - 项目总览和快速开始
- [阿里云官方文档](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen#f0577378e8sz4) - 首次调用千问API

---

## 🧪 测试建议

1. **验证配置**：
   ```bash
   python3 check_config.py
   ```

2. **测试AI调用**：
   ```bash
   python3 -c "from modules.llm_parser.llm_parser import LLMParser; p = LLMParser(); print(p.classify_issue('测试', '这是一个测试Issue'))"
   ```

3. **运行完整系统**：
   ```bash
   python3 run.py
   ```

---

## ⚠️ 注意事项

1. **API Key安全**：
   - ✅ 推荐使用环境变量配置（更安全）
   - ❌ 避免在代码中硬编码API Key

2. **费用管理**：
   - 新用户通常有免费额度
   - 免费额度用完后需要充值
   - 查看消费明细：访问 [账单详情](https://bailian.console.aliyun.com/#/bill)

3. **模型选择**：
   - `qwen-max-latest` - 最强性能（推荐）
   - `qwen-plus` - 平衡性能和成本（默认）
   - `qwen-turbo` - 快速响应

---

## ✅ 更新完成

所有配置已按照 [阿里云官方文档](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen#f0577378e8sz4) 更新完成，系统可以正常使用通义千问API。

**下一步**：
1. 确保已设置 `DASHSCOPE_API_KEY` 环境变量
2. 运行 `python3 check_config.py` 验证配置
3. 开始使用系统！

---

**最后更新**：2025-02-21
