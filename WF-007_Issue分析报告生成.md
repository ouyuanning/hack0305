# WF-007: Issue分析报告生成

## 📌 工作流基本信息

| 属性 | 内容 |
|------|------|
| **工作流ID** | WF-007 |
| **工作流名称** | Issue分析报告生成 |
| **功能描述** | 从MatrixOne库读取Issue数据，按指定维度用AI生成多类型分析报告（项目推进、横向关联、可扩展分析等） |
| **实现状态** | ✅ 已实现 |
| **云端可用** | ✅ 完全可用 |
| **核心价值** | 为管理层提供决策支持，识别项目风险和优化方向 |

---

## 🔄 流程步骤总览

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  步骤1   │──▶│  步骤2   │──▶│  步骤3   │──▶│  步骤4   │──▶│  步骤5   │
│读取Issue │   │选择分析  │   │执行分析  │   │AI生成    │   │输出报告  │
│  数据    │   │  维度    │   │  逻辑    │   │  洞察    │   │         │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
  从MO读取      项目推进       统计聚合       AI分析        Markdown
  最新快照      横向关联       层级构建       模式识别      JSON
  + 过滤       可扩展分析      关联识别       建议生成      HTML/Email
```

**快速理解**：
1. **步骤1** - 从MO读取Issue数据（最新快照或指定库表）
2. **步骤2** - 根据需求选择分析维度（项目推进/横向关联/可扩展分析）
3. **步骤3** - 执行数据分析逻辑（统计、聚合、关联识别）
4. **步骤4** - AI生成洞察（健康度评分、模式识别、建议）
5. **步骤5** - 格式化输出报告（Markdown/JSON/HTML，可发邮件）

**核心特点**：✅ AI驱动 | ✅ 多维度分析 | ✅ 配置化 | ✅ 支持邮件发送

---

## 📥 整体输入

### 1. 数据源配置

| 输入项 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| **repo_owner** | String | 仓库所有者 | `matrixorigin` |
| **repo_name** | String | 仓库名称 | `matrixone` / `matrixflow` |
| **source_table** | String | 数据源表 | `issues_snapshot`（默认） |
| **use_experimental** | Boolean | 是否使用实验库 | `False` |

### 2. 分析类型配置

| 输入项 | 类型 | 说明 | 适用场景 |
|--------|------|------|---------|
| **analysis_type** | Enum | 分析类型 | 见下表 |

**分析类型（analysis_type）**：

| 类型值 | 名称 | 说明 | 频率建议 | 适用仓库 |
|--------|------|------|---------|---------|
| `project_progress` | 项目推进分析 | 按客户项目分析进度和堵塞点 | 每日/每周 | matrixflow（含customer标签） |
| `cross_customer` | 横向关联分析 | 识别共用Feature和高Bug模块 | 每周/每月 | matrixflow |
| `extensible` | 可扩展分析 | 配置驱动的多维度分析 | 按需 | 所有仓库 |

### 3. AI服务配置

| 输入项 | 类型 | 说明 |
|--------|------|------|
| **AI_PROVIDER** | String | `qwen`（推荐） |
| **DASHSCOPE_API_KEY** | String | 通义千问API密钥 |
| **QWEN_MODEL** | String | `qwen-plus` |

### 4. 可扩展分析配置（analysis_type=extensible时）

| 输入项 | 类型 | 说明 | 位置 |
|--------|------|------|------|
| **analysis_config.yaml** | YAML | 可扩展分析配置文件 | `config/analysis_config.yaml` |

**analysis_config.yaml示例**：
```yaml
global:
  repo_owner: matrixorigin
  repo_name: matrixone

analyzers:
  # 基础统计
  - name: basic_stats
    enabled: true
    config:
      include_closed: true
  
  # 标签分析
  - name: label_analysis
    enabled: true
    config:
      min_count: 5
      prefixes: ["kind/", "area/", "customer/"]
  
  # 模块分析
  - name: module_analysis
    enabled: true
    config:
      group_by: "area"
  
  # 层级分析
  - name: hierarchy_analysis
    enabled: true
    config:
      levels: ["L1", "L2", "L3", "L4"]
  
  # 客户分析
  - name: customer_analysis
    enabled: true
    config:
      top_n: 10
  
  # 关联分析
  - name: relation_analysis
    enabled: true
  
  # 趋势分析
  - name: trend_analysis
    enabled: true
    config:
      time_range_days: 90

output:
  formats: ["json", "markdown", "html"]
  output_dir: "data/reports"
```

### 5. 输出配置

| 输入项 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| **output_format** | Array | 输出格式 | `["json", "markdown"]` |
| **output_dir** | String | 输出目录 | `data/reports` |
| **send_email** | Boolean | 是否发送邮件 | `False` |
| **email_to** | Array | 收件人列表 | `[]` |

---

## 📤 整体输出

### 1. 报告文件

| 输出项 | 格式 | 说明 | 示例文件名 |
|--------|------|------|-----------|
| **JSON报告** | JSON | 结构化数据 | `project_progress_20260304.json` |
| **Markdown报告** | Markdown | 可读性报告 | `project_progress_20260304.md` |
| **HTML报告** | HTML | 网页格式 | `project_progress_20260304.html` |

### 2. 报告内容结构

**项目推进分析报告**：
```json
{
    "analysis_type": "项目推进分析",
    "total_customers": 5,
    "customers": {
        "金盘": {
            "total_issues": 50,
            "hierarchy": {
                "L1_projects": [...],
                "L2_features": [...],
                "L3_tasks": [...],
                "L4_bugs": [...],
                "L1_projects_stats": {
                    "total": 3,
                    "open": 1,
                    "closed": 2,
                    "completion_rate": 0.67
                }
            },
            "blockages": [
                {
                    "issue_number": 8450,
                    "title": "性能优化被阻塞",
                    "blocked_reason": "依赖底层修复"
                }
            ],
            "ai_insights": {
                "health_score": 75,
                "health_level": "一般",
                "key_findings": [
                    "L2 Feature完成率较低（60%）",
                    "有3个高优先级Bug未处理"
                ],
                "blockage_analysis": "主要堵塞在底层依赖...",
                "recommendations": [
                    "优先处理底层依赖Issue",
                    "增加L2 Feature的资源投入"
                ],
                "urgent_actions": [
                    "立即处理Issue #8450"
                ]
            }
        }
    },
    "generated_at": "2026-03-04T10:30:00Z"
}
```

**横向关联分析报告**：
```json
{
    "analysis_type": "横向关联分析",
    "shared_features": [
        {
            "feature_number": 8500,
            "feature_title": "多租户权限管理",
            "customers": ["金盘", "XX银行", "YY公司"],
            "customer_count": 3,
            "state": "open"
        }
    ],
    "high_bug_features": [
        {
            "feature_number": 8400,
            "feature_title": "NL2SQL翻译",
            "bug_count": 12,
            "open_bug_count": 5,
            "affected_customers": ["金盘", "XX银行"],
            "severity": "high"
        }
    ],
    "ai_patterns": {
        "common_needs_pattern": "多个客户都需要权限管理功能...",
        "high_bug_reasons": "NL2SQL模块复杂度高...",
        "strategic_recommendations": [
            "将多租户权限管理作为通用Feature开发",
            "加强NL2SQL模块的测试覆盖"
        ],
        "resource_allocation": {
            "should_prioritize": ["多租户权限管理"],
            "should_stabilize": ["NL2SQL翻译"]
        },
        "customer_impact_analysis": "影响3个核心客户..."
    },
    "generated_at": "2026-03-04T10:30:00Z"
}
```

**可扩展分析报告**：
```json
{
    "analysis_type": "可扩展分析",
    "results": {
        "basic_stats": {
            "total_issues": 5000,
            "open_issues": 1200,
            "closed_issues": 3800,
            "open_rate": 0.24
        },
        "label_analysis": {
            "kind/": {
                "kind/bug": 2000,
                "kind/feature": 1500
            },
            "area/": {
                "area/storage": 800,
                "area/sql": 600
            }
        },
        "customer_analysis": {
            "top_customers": [
                {"name": "金盘", "issue_count": 150},
                {"name": "XX银行", "issue_count": 120}
            ]
        },
        "trend_analysis": {
            "weekly_trend": [
                {"week": "2024-W10", "open": 50, "closed": 45},
                {"week": "2024-W11", "open": 48, "closed": 52}
            ]
        }
    },
    "generated_at": "2026-03-04T10:30:00Z"
}
```

### 3. 邮件输出（可选）

| 输出项 | 类型 | 说明 |
|--------|------|------|
| **邮件正文** | HTML | 格式化的报告内容 |
| **附件** | File | JSON/Markdown报告文件 |

---

## 🔄 详细步骤拆分

### 步骤1: 读取Issue数据

**步骤ID**: WF-007-S01  
**功能**: 从MatrixOne读取最新的Issue数据  
**实现状态**: ✅ 已实现

#### 输入
- `repo_owner`, `repo_name`: 仓库标识
- `source_table`: 数据源表（默认`issues_snapshot`）

#### 处理逻辑

**获取最新快照时间**：
```sql
-- MatrixOne兼容方式：先查最新时间
SELECT snapshot_time
FROM issues_snapshot
WHERE repo_owner = :owner AND repo_name = :repo
GROUP BY snapshot_time
ORDER BY COUNT(*) DESC
LIMIT 1;
```

**读取Issue数据**：
```sql
SELECT *
FROM issues_snapshot
WHERE repo_owner = :owner 
  AND repo_name = :repo
  AND snapshot_time = :latest_time;
```

**数据预处理**：
```python
def load_issues(self, repo_owner: str, repo_name: str) -> List[Dict]:
    """加载Issue数据并预处理"""
    # 获取最新快照时间
    latest_time = self._get_latest_snapshot_time(repo_owner, repo_name)
    
    # 读取数据
    sql = """
    SELECT *
    FROM issues_snapshot
    WHERE repo_owner = :owner 
      AND repo_name = :repo
      AND snapshot_time = :time
    """
    rows = self.storage.execute(sql, {
        "owner": repo_owner,
        "repo": repo_name,
        "time": latest_time
    })
    
    # 转换为字典列表
    issues = [dict(row) for row in rows]
    
    # 解析Labels（从JSON字符串转为列表）
    for issue in issues:
        if 'labels' in issue and isinstance(issue['labels'], str):
            try:
                issue['labels'] = json.loads(issue['labels'])
            except:
                issue['labels'] = []
    
    return issues
```

#### 输出
- **issues** (List[Dict]): Issue数据列表
- **total_count** (Integer): Issue总数

#### 代码模块
- **文件**: `modules/ai_analysis/ai_driven_analysis_engine.py`
- **方法**: `_load_issues(repo_owner, repo_name)`
- **缓存**: `_latest_snapshot_cache`（避免重复查询）

---

### 步骤2: 选择分析维度

**步骤ID**: WF-007-S02  
**功能**: 根据analysis_type选择对应的分析逻辑  
**实现状态**: ✅ 已实现

#### 输入
- **analysis_type**: 分析类型（`project_progress` / `cross_customer` / `extensible`）
- **issues** (步骤1输出): Issue数据

#### 处理逻辑

**路由逻辑**：
```python
def analyze(
    self, 
    repo_owner: str, 
    repo_name: str, 
    analysis_type: str
) -> Dict:
    """根据类型执行分析"""
    
    if analysis_type == "project_progress":
        # 项目推进分析
        return self.analyze_project_progress(repo_owner, repo_name)
    
    elif analysis_type == "cross_customer":
        # 横向关联分析
        return self.analyze_cross_customer_patterns(repo_owner, repo_name)
    
    elif analysis_type == "extensible":
        # 可扩展分析
        engine = ExtensibleAnalysisEngine()
        return engine.run(repo_owner, repo_name)
    
    else:
        raise ValueError(f"不支持的分析类型: {analysis_type}")
```

#### 输出
- **selected_analyzer**: 选中的分析器函数

---

### 步骤3: 执行分析逻辑

**步骤ID**: WF-007-S03  
**功能**: 执行数据统计、聚合、关联识别等分析  
**实现状态**: ✅ 已实现

#### 输入
- **issues** (步骤1输出): Issue数据
- **selected_analyzer** (步骤2输出): 分析器

#### 处理逻辑

**3A. 项目推进分析逻辑**：

**按客户分组**：
```python
def _group_by_customer(self, issues: List[Dict]) -> Dict[str, List[Dict]]:
    """按customer/标签分组"""
    customers = defaultdict(list)
    
    for issue in issues:
        labels = self._parse_labels(issue.get('labels', []))
        
        # 提取customer标签
        customer_labels = [
            label.replace('customer/', '')
            for label in labels
            if 'customer' in label.lower()
        ]
        
        # 归类到各客户
        for customer in customer_labels:
            customers[customer].append(issue)
    
    return dict(customers)
```

**构建层级关系**（L1→L2→L3→L4）：
```python
def _build_hierarchy(self, issues: List[Dict]) -> Dict:
    """构建Issue层级结构"""
    hierarchy = {
        "L1_projects": [],      # Customer Project
        "L2_features": [],      # Feature
        "L3_tasks": [],         # Task
        "L4_bugs": []           # Bug
    }
    
    for issue in issues:
        title = issue.get('title', '')
        labels = self._parse_labels(issue.get('labels', []))
        
        # 判断层级
        if self._is_customer_project(title, labels):
            hierarchy["L1_projects"].append(
                self._format_issue_summary(issue)
            )
        elif self._is_feature(title, labels):
            hierarchy["L2_features"].append(
                self._format_issue_summary(issue)
            )
        elif self._is_task(title, labels):
            hierarchy["L3_tasks"].append(
                self._format_issue_summary(issue)
            )
        elif self._is_bug(title, labels):
            hierarchy["L4_bugs"].append(
                self._format_issue_summary(issue)
            )
    
    # 计算统计信息
    for level in ["L1_projects", "L2_features", "L3_tasks", "L4_bugs"]:
        items = hierarchy[level]
        open_count = sum(1 for i in items if i['state'] == 'open')
        hierarchy[f"{level}_stats"] = {
            "total": len(items),
            "open": open_count,
            "closed": len(items) - open_count,
            "completion_rate": (len(items) - open_count) / len(items) if items else 0
        }
    
    return hierarchy
```

**识别堵塞点**：
```python
def _identify_blockages(self, issues: List[Dict]) -> List[Dict]:
    """识别被阻塞的Issue"""
    blockages = []
    
    for issue in issues:
        # 检查阻塞标记
        if issue.get('is_blocked'):
            blockages.append({
                "issue_number": issue['issue_number'],
                "title": issue['title'],
                "blocked_reason": issue.get('blocked_reason', '未说明'),
                "state": issue['state'],
                "labels": self._parse_labels(issue.get('labels', []))
            })
    
    return blockages
```

---

**3B. 横向关联分析逻辑**：

**识别共用Feature**：
```python
def _find_shared_features(self, issues: List[Dict]) -> List[Dict]:
    """找出被多个客户共用的Feature"""
    feature_customers = defaultdict(set)
    
    for issue in issues:
        labels = self._parse_labels(issue.get('labels', []))
        
        # 判断是否为Feature
        if self._is_feature(issue.get('title'), labels):
            # 提取关联的客户
            customers = [
                label.replace('customer/', '')
                for label in labels
                if 'customer' in label.lower()
            ]
            
            # 记录该Feature被哪些客户使用
            for customer in customers:
                feature_customers[issue['issue_number']].add(customer)
    
    # 筛选出至少被2个客户使用的Feature
    shared = []
    for feature_number, customers in feature_customers.items():
        if len(customers) >= 2:
            feature_issue = next(
                (i for i in issues if i['issue_number'] == feature_number), 
                None
            )
            if feature_issue:
                shared.append({
                    "feature_number": feature_number,
                    "feature_title": feature_issue['title'],
                    "customers": sorted(list(customers)),
                    "customer_count": len(customers),
                    "state": feature_issue['state']
                })
    
    # 按客户数量降序排列
    shared.sort(key=lambda x: x['customer_count'], reverse=True)
    return shared
```

**识别高Bug Feature**：
```python
def _find_high_bug_features(self, issues: List[Dict]) -> List[Dict]:
    """找出Bug最多的Feature"""
    features = [
        i for i in issues 
        if self._is_feature(i.get('title'), self._parse_labels(i.get('labels', [])))
    ]
    
    feature_bugs = []
    for feature in features:
        feature_labels = set(self._parse_labels(feature.get('labels', [])))
        
        # 找到与该Feature相关的Bug（共享标签）
        related_bugs = [
            i for i in issues
            if self._is_bug(i.get('title'), self._parse_labels(i.get('labels', [])))
            and len(set(self._parse_labels(i.get('labels', []))) & feature_labels) > 0
        ]
        
        if related_bugs:
            # 统计受影响的客户
            affected_customers = set()
            for bug in related_bugs:
                for label in self._parse_labels(bug.get('labels', [])):
                    if 'customer' in label.lower():
                        affected_customers.add(label.replace('customer/', ''))
            
            feature_bugs.append({
                "feature_number": feature['issue_number'],
                "feature_title": feature['title'],
                "bug_count": len(related_bugs),
                "open_bug_count": sum(1 for b in related_bugs if b['state'] == 'open'),
                "affected_customers": sorted(list(affected_customers)),
                "severity": "high" if len(related_bugs) > 5 else "medium" if len(related_bugs) > 2 else "low"
            })
    
    # 按Bug数量降序，取Top 10
    feature_bugs.sort(key=lambda x: x['bug_count'], reverse=True)
    return feature_bugs[:10]
```

---

**3C. 可扩展分析逻辑**（配置驱动）：

**基础统计分析器**：
```python
class BasicStatsAnalyzer:
    def analyze(self, issues: List[Dict]) -> Dict:
        """基础统计"""
        total = len(issues)
        open_count = sum(1 for i in issues if i['state'] == 'open')
        closed_count = total - open_count
        
        return {
            "total_issues": total,
            "open_issues": open_count,
            "closed_issues": closed_count,
            "open_rate": open_count / total if total > 0 else 0
        }
```

**标签分析器**：
```python
class LabelAnalyzer:
    def analyze(self, issues: List[Dict], config: Dict) -> Dict:
        """按标签前缀统计"""
        min_count = config.get('min_count', 5)
        prefixes = config.get('prefixes', ['kind/', 'area/'])
        
        label_stats = defaultdict(lambda: defaultdict(int))
        
        for issue in issues:
            for label in self._parse_labels(issue.get('labels', [])):
                for prefix in prefixes:
                    if label.startswith(prefix):
                        label_stats[prefix][label] += 1
        
        # 过滤低频标签
        filtered = {}
        for prefix, labels in label_stats.items():
            filtered[prefix] = {
                k: v for k, v in labels.items() 
                if v >= min_count
            }
        
        return filtered
```

#### 输出
- **analysis_results** (Dict): 分析结果数据

#### 代码模块
- **文件**: `modules/ai_analysis/ai_driven_analysis_engine.py`
- **方法**: 
  - `analyze_project_progress()`
  - `analyze_cross_customer_patterns()`
- **文件**: `modules/analysis_extensible/analysis_engine.py`
- **方法**: `run()`

---

### 步骤4: AI生成洞察

**步骤ID**: WF-007-S04  
**功能**: 使用AI分析数据，生成洞察和建议  
**实现状态**: ✅ 已实现

#### 输入
- **analysis_results** (步骤3输出): 分析结果数据

#### 处理逻辑

**4A. 项目健康度AI分析**：

**构建Prompt**：
```python
def _ai_analyze_project_status(
    self, 
    customer: str, 
    hierarchy: Dict, 
    blockages: List[Dict]
) -> Dict:
    """AI分析项目状态"""
    
    system_prompt = """你是一个项目管理专家。请分析客户项目状态，用中文回答，并以JSON格式返回。"""
    
    user_prompt = f"""
**客户**: {customer}

**层级统计**:
- L1 (Customer Project): {hierarchy['L1_projects_stats']['total']} 个，完成率 {hierarchy['L1_projects_stats']['completion_rate']*100:.1f}%
- L2 (Feature): {hierarchy['L2_features_stats']['total']} 个，完成率 {hierarchy['L2_features_stats']['completion_rate']*100:.1f}%
- L3 (Task): {hierarchy['L3_tasks_stats']['total']} 个，完成率 {hierarchy['L3_tasks_stats']['completion_rate']*100:.1f}%
- L4 (Bug): {hierarchy['L4_bugs_stats']['total']} 个，完成率 {hierarchy['L4_bugs_stats']['completion_rate']*100:.1f}%

**堵塞的Issue** (Top 5):
{json.dumps(blockages[:5], indent=2, ensure_ascii=False)}

请用JSON格式返回:
{{
  "health_score": 0-100,
  "health_level": "健康" | "一般" | "风险" | "严重",
  "key_findings": ["发现1", "发现2", "发现3"],
  "blockage_analysis": "堵塞原因分析",
  "recommendations": ["建议1", "建议2", "建议3"],
  "urgent_actions": ["需要立即处理的问题"]
}}
"""
    
    # 调用AI
    response_text = self.llm._call_ai(system_prompt, user_prompt)
    
    # 解析JSON响应
    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    
    return {"error": "AI返回格式错误"}
```

**健康度评分逻辑**（AI生成）：
- 90-100: 健康（完成率高，无堵塞）
- 70-89: 一般（完成率中等，少量堵塞）
- 50-69: 风险（完成率低，堵塞较多）
- 0-49: 严重（严重滞后，大量堵塞）

---

**4B. 横向模式AI分析**：

```python
def _ai_analyze_patterns(
    self, 
    shared_features: List[Dict], 
    high_bug_features: List[Dict]
) -> Dict:
    """AI分析横向模式"""
    
    system_prompt = """你是产品策略专家。请分析数据，识别产品和开发的关键模式，用中文回答，并以JSON格式返回。"""
    
    user_prompt = f"""
**跨客户共用Feature** (Top 5):
{json.dumps(shared_features[:5], indent=2, ensure_ascii=False)}

**高Bug数Feature** (Top 5):
{json.dumps(high_bug_features[:5], indent=2, ensure_ascii=False)}

请用JSON格式返回:
{{
  "common_needs_pattern": "共性需求的模式总结",
  "high_bug_reasons": "高Bug功能的可能原因",
  "strategic_recommendations": ["战略建议1", "战略建议2"],
  "resource_allocation": {{
    "should_prioritize": ["应该优先投入的功能"],
    "should_stabilize": ["应该稳定的功能"]
  }},
  "customer_impact_analysis": "对客户的影响分析"
}}
"""
    
    response_text = self.llm._call_ai(system_prompt, user_prompt)
    
    # 解析响应
    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group())
    
    return {"error": "AI返回格式错误"}
```

#### 输出
- **ai_insights** (Dict): AI生成的洞察和建议

#### 代码模块
- **方法**: 
  - `_ai_analyze_project_status()`
  - `_ai_analyze_patterns()`

---

### 步骤5: 格式化输出报告

**步骤ID**: WF-007-S05  
**功能**: 将分析结果格式化为Markdown/JSON/HTML  
**实现状态**: ✅ 已实现

#### 输入
- **analysis_results** (步骤3输出): 分析结果
- **ai_insights** (步骤4输出): AI洞察
- **output_format**: 输出格式列表

#### 处理逻辑

**5.1 生成JSON报告**：
```python
def save_json_report(self, data: Dict, filename: str):
    """保存JSON格式报告"""
    output_path = Path("data/reports") / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ JSON报告已保存: {output_path}")
```

**5.2 生成Markdown报告**：
```python
def generate_markdown_report(self, data: Dict) -> str:
    """生成Markdown格式报告"""
    
    if data['analysis_type'] == '项目推进分析':
        return self._generate_project_progress_markdown(data)
    elif data['analysis_type'] == '横向关联分析':
        return self._generate_cross_customer_markdown(data)
    else:
        return self._generate_extensible_markdown(data)

def _generate_project_progress_markdown(self, data: Dict) -> str:
    """生成项目推进分析的Markdown"""
    md = f"""# 项目推进分析报告

**生成时间**: {data['generated_at']}  
**总客户数**: {data['total_customers']}

---

"""
    
    for customer, info in data['customers'].items():
        ai = info.get('ai_insights', {})
        
        md += f"""## {customer}

### 健康度评分
- **分数**: {ai.get('health_score', 'N/A')}/100
- **等级**: {ai.get('health_level', 'N/A')}

### 层级统计
| 层级 | 总数 | Open | Closed | 完成率 |
|------|------|------|--------|--------|
| L1 (Project) | {info['hierarchy']['L1_projects_stats']['total']} | {info['hierarchy']['L1_projects_stats']['open']} | {info['hierarchy']['L1_projects_stats']['closed']} | {info['hierarchy']['L1_projects_stats']['completion_rate']*100:.1f}% |
| L2 (Feature) | {info['hierarchy']['L2_features_stats']['total']} | {info['hierarchy']['L2_features_stats']['open']} | {info['hierarchy']['L2_features_stats']['closed']} | {info['hierarchy']['L2_features_stats']['completion_rate']*100:.1f}% |
| L3 (Task) | {info['hierarchy']['L3_tasks_stats']['total']} | {info['hierarchy']['L3_tasks_stats']['open']} | {info['hierarchy']['L3_tasks_stats']['closed']} | {info['hierarchy']['L3_tasks_stats']['completion_rate']*100:.1f}% |
| L4 (Bug) | {info['hierarchy']['L4_bugs_stats']['total']} | {info['hierarchy']['L4_bugs_stats']['open']} | {info['hierarchy']['L4_bugs_stats']['closed']} | {info['hierarchy']['L4_bugs_stats']['completion_rate']*100:.1f}% |

### 关键发现
"""
        for finding in ai.get('key_findings', []):
            md += f"- {finding}\n"
        
        md += f"""
### 堵塞分析
{ai.get('blockage_analysis', '无')}

### 建议
"""
        for rec in ai.get('recommendations', []):
            md += f"- {rec}\n"
        
        md += "\n---\n\n"
    
    return md
```

**5.3 生成HTML报告**：
```python
def generate_html_report(self, markdown_text: str) -> str:
    """Markdown转HTML"""
    import markdown
    
    html_body = markdown.markdown(
        markdown_text,
        extensions=['tables', 'fenced_code']
    )
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Issue分析报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    {html_body}
</body>
</html>
"""
    return html
```

**5.4 发送邮件（可选）**：
```python
def send_email_report(
    self, 
    subject: str,
    markdown_text: str,
    attachments: List[str],
    to_emails: List[str]
):
    """发送邮件报告"""
    from modules.email_sender.email_sender import EmailSender
    
    sender = EmailSender()
    
    # Markdown转HTML作为邮件正文
    html_body = self.generate_html_report(markdown_text)
    
    # 发送
    sender.send_email(
        subject=subject,
        body=html_body,
        to_emails=to_emails,
        attachments=attachments
    )
    
    print(f"✓ 邮件已发送至: {', '.join(to_emails)}")
```

#### 输出
- **report_files**: 生成的报告文件列表
- **email_sent**: 是否成功发送邮件

#### 代码模块
- **文件**: `modules/ai_analysis/ai_driven_analysis_engine.py`
- **文件**: `modules/analysis_extensible/analysis_engine.py`
- **方法**: 各种格式化和输出方法

---

## 🗄️ 数据库表结构

### 本工作流主要读取以下表

**issues_snapshot**（主数据源）：
- 读取最新快照的所有Issue数据
- 字段：issue_id, title, body, state, labels, created_at等

**可选读取**：
- **experimental_issues**（如果使用实验库）
- **issue_relations**（关联分析时）
- **project_issues**（项目看板数据）

---

## ⚙️ 配置文件说明

### 主配置: `config/config.py`

```python
# AI配置（同WF-001）
AI_PROVIDER = "qwen"
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
QWEN_MODEL = "qwen-plus"
```

### 可扩展分析配置: `config/analysis_config.yaml`

详见"整体输入"部分的配置示例。

---

## 🔧 运行方式

### 方式1：命令行运行

**项目推进分析**：
```bash
python3 scripts/run_ai_analysis.py \
    --repo-owner matrixorigin \
    --repo-name matrixflow \
    --analysis-type project_progress \
    --email user@example.com
```

**横向关联分析**：
```bash
python3 scripts/run_ai_analysis.py \
    --repo-owner matrixorigin \
    --repo-name matrixflow \
    --analysis-type cross_customer \
    --output-format json,markdown
```

**可扩展分析**：
```bash
python3 scripts/run_extensible_analysis.py \
    --repo-owner matrixorigin \
    --repo-name matrixone \
    --email user@example.com
```

### 方式2：Python代码调用

```python
from modules.ai_analysis.ai_driven_analysis_engine import AIAnalysisEngine
from modules.database_storage.mo_client import MOStorage

# 初始化
storage = MOStorage()
engine = AIAnalysisEngine(storage)

# 项目推进分析
result = engine.analyze_project_progress(
    repo_owner="matrixorigin",
    repo_name="matrixflow"
)

# 输出结果
print(f"分析了 {result['total_customers']} 个客户项目")
for customer, info in result['customers'].items():
    ai_insights = info['ai_insights']
    print(f"{customer}: 健康度 {ai_insights['health_score']}/100")
```

### 方式3：自动定时任务

```python
import schedule
import time

def daily_analysis():
    """每日项目推进分析"""
    engine = AIAnalysisEngine(MOStorage())
    result = engine.analyze_project_progress("matrixorigin", "matrixflow")
    
    # 保存报告
    save_json_report(result, f"project_progress_{date.today()}.json")
    
    # 发送邮件
    send_email_report(
        subject=f"项目推进分析 - {date.today()}",
        data=result,
        to_emails=["pm@example.com"]
    )

# 每天早上9点执行
schedule.every().day.at("09:00").do(daily_analysis)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## ✅ 实现验证

### 验证步骤

1. **测试数据读取**：
   ```python
   engine = AIAnalysisEngine(MOStorage())
   issues = engine._load_issues("matrixorigin", "matrixone")
   print(f"读取了 {len(issues)} 个Issue")
   ```

2. **测试项目推进分析**：
   ```bash
   python3 scripts/run_ai_analysis.py \
       --repo-owner matrixorigin \
       --repo-name matrixflow \
       --analysis-type project_progress
   ```

3. **检查输出报告**：
   ```bash
   ls -lh data/reports/
   cat data/reports/project_progress_*.md
   ```

4. **测试邮件发送**：
   ```bash
   python3 scripts/run_ai_analysis.py \
       --repo-owner matrixorigin \
       --repo-name matrixflow \
       --analysis-type project_progress \
       --email your@email.com
   ```

---

## 📊 性能指标

| 指标 | 数值 | 说明 |
|------|------|------|
| **数据读取** | ~2-5秒 | 读取5000个Issue |
| **统计分析** | ~5-10秒 | 层级构建、分组聚合 |
| **AI分析** | ~10-30秒 | 取决于客户数量和AI响应时间 |
| **报告生成** | ~1-2秒 | Markdown/JSON格式化 |
| **总耗时** | ~20-50秒 | 完整分析流程 |

---

## 🔄 云端部署注意事项

### ✅ 完全可用

该工作流在云端部署**无任何限制**：
- ✅ 纯数据库读取
- ✅ AI API调用
- ✅ 文件写入可用云存储

### 优化建议

1. **缓存机制**：缓存最新快照时间，避免重复查询
2. **批量AI调用**：合并多个客户的分析请求
3. **异步执行**：使用任务队列处理大规模分析

---

## 📈 扩展方向

### 1. 更多分析维度
- 时间趋势分析（周/月对比）
- 团队效率分析（人均产出）
- 质量分析（Bug密度、修复时长）

### 2. 可视化增强
- 生成图表（Plotly/ECharts）
- 交互式HTML报告
- 实时Dashboard

### 3. 告警机制
- 健康度低于阈值时自动告警
- 关键堵塞Issue通知
- 趋势异常检测

---

**文档版本**: v1.0  
**最后更新**: 2026-03-04
