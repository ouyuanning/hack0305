# 通义千问API配置说明

本文档说明如何配置阿里云百炼（通义千问）API。

## 📚 参考文档

- [首次调用千问API - 阿里云官方文档](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen#f0577378e8sz4)

## 🔑 获取API Key

1. **注册/登录阿里云账号**
   - 访问 [阿里云官网](https://www.aliyun.com/)
   - 如果没有账号，需要先注册

2. **开通阿里云百炼**
   - 使用**阿里云主账号**前往 [阿里云百炼大模型服务平台](https://bailian.console.aliyun.com/)
   - 阅读并同意协议后，将自动开通阿里云百炼
   - 如果提示"您尚未进行实名认证"，请先进行实名认证

3. **创建API Key**
   - 前往 [密钥管理页面](https://bailian.console.aliyun.com/#/api-key)
   - 单击**创建API Key**
   - 复制生成的API Key（注意保存，只显示一次）

## ⚙️ 配置方式

### 方式一：环境变量（推荐）

**macOS/Linux (Zsh)**：

```bash
# 临时设置（当前会话有效）
export DASHSCOPE_API_KEY="your_api_key_here"

# 永久设置（推荐）
echo "export DASHSCOPE_API_KEY='your_api_key_here'" >> ~/.zshrc
source ~/.zshrc
```

**macOS/Linux (Bash)**：

```bash
# 临时设置（当前会话有效）
export DASHSCOPE_API_KEY="your_api_key_here"

# 永久设置（推荐）
echo "export DASHSCOPE_API_KEY='your_api_key_here'" >> ~/.bash_profile
source ~/.bash_profile
```

**Windows**：

```powershell
# 临时设置（当前会话有效）
setx DASHSCOPE_API_KEY "your_api_key_here"

# 或在系统环境变量中手动添加
# 控制面板 → 系统 → 高级系统设置 → 环境变量
```

**验证配置**：

```bash
echo $DASHSCOPE_API_KEY  # macOS/Linux
echo %DASHSCOPE_API_KEY%  # Windows
```

### 方式二：配置文件（不推荐，安全性较低）

编辑 `config/config.py` 文件：

```python
# 不推荐：直接在代码中写API Key
QWEN_API_KEY = "your_api_key_here"
```

⚠️ **注意**：这种方式会将API Key暴露在代码中，存在安全风险。

## 🔧 系统配置说明

### 配置优先级

系统按以下优先级读取API Key：

1. **`DASHSCOPE_API_KEY`** 环境变量（官方推荐，优先使用）
2. **`QWEN_API_KEY`** 环境变量（向后兼容）
3. `config/config.py` 中的 `QWEN_API_KEY`（不推荐）

### API地址配置

系统默认使用**兼容模式**API地址：

```
https://dashscope.aliyuncs.com/compatible-mode/v1
```

兼容模式支持：
- ✅ OpenAI兼容接口（推荐）
- ✅ DashScope SDK（备用）

如需使用标准API，可在 `config/config.py` 中修改：

```python
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
```

### 模型选择

系统默认使用 `qwen-plus` 模型，可在 `config/config.py` 中修改：

```python
QWEN_MODEL = "qwen-plus"  # 或 "qwen-max-latest", "qwen-turbo" 等
```

**推荐模型**：
- `qwen-max-latest` - 最强性能（推荐）
- `qwen-plus` - 平衡性能和成本（默认）
- `qwen-turbo` - 快速响应

更多模型请参考：[模型列表](https://help.aliyun.com/zh/model-studio/models)

## 🧪 测试配置

运行配置检查脚本：

```bash
python3 check_config.py
```

如果配置正确，应该看到：

```
✅ Python包        : 通过
✅ GitHub配置       : 通过
✅ AI配置          : 通过
✅ MatrixOne连接   : 成功
```

## 💰 费用说明

### 免费额度

- 新用户通常有免费额度
- 免费额度用完后需要充值才能继续使用

### 计费方式

- 按Token计费（输入+输出）
- 出账周期：每小时
- 消费明细：前往 [账单详情](https://bailian.console.aliyun.com/#/bill) 查看

### 充值方式

1. 访问 [费用与成本中心](https://bailian.console.aliyun.com/#/bill)
2. 确保账户没有欠费
3. 充值后即可继续调用

## ❓ 常见问题

### Q: 调用API后报错 `Model.AccessDenied`，如何处理？

A: 该报错是因为您使用子业务空间的API Key，子业务空间无法访问**主账号空间**的应用或模型。

**解决方法**：
- 使用主账号的API Key
- 或由主账号管理员为对应子空间开通模型授权

详细操作步骤请参见：[设置模型调用权限](https://help.aliyun.com/zh/model-studio/set-model-call-permissions)

### Q: 如何查看API调用日志？

A: 访问 [阿里云百炼控制台](https://bailian.console.aliyun.com/) → 查看调用记录和日志。

### Q: 支持哪些接入方式？

A: 系统支持两种方式：
1. **OpenAI兼容接口**（推荐）- 使用兼容模式API地址
2. **DashScope SDK** - 使用标准API地址

系统会自动选择最合适的方式。

### Q: 如何切换模型？

A: 在 `config/config.py` 中修改 `QWEN_MODEL` 配置：

```python
QWEN_MODEL = "qwen-max-latest"  # 切换到最强模型
```

## 📖 更多资源

- [阿里云百炼官方文档](https://help.aliyun.com/zh/model-studio/)
- [千问API参考](https://help.aliyun.com/zh/model-studio/api-reference/qwen)
- [模型列表](https://help.aliyun.com/zh/model-studio/models)
- [流式输出](https://help.aliyun.com/zh/model-studio/stream)
- [结构化输出](https://help.aliyun.com/zh/model-studio/qwen-structured-output)

---

**最后更新**：2025-02-21  
**参考文档**：[首次调用千问API](https://help.aliyun.com/zh/model-studio/first-api-call-to-qwen#f0577378e8sz4)
