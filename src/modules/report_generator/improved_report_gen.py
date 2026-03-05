#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的报告生成模块
功能：生成多维度分析报告（总报告 + 各客户独立报告）
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from config.config import REPORT_OUTPUT_DIR
from modules.database_storage.mo_client import MOStorage
from modules.analysis_engine.multi_dimensional_analyzer import MultiDimensionalAnalyzer


class ImprovedReportGenerator:
    """改进的报告生成器"""
    
    def __init__(self, storage: MOStorage, output_dir: Path = None):
        self.storage = storage
        self.analyzer = MultiDimensionalAnalyzer(storage)
        self.output_dir = Path(output_dir) if output_dir else REPORT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 客户报告子目录
        self.customer_dir = self.output_dir / "customer_reports"
        self.customer_dir.mkdir(exist_ok=True)
    
    def generate_all_reports(self, repo_owner: str, repo_name: str):
        """
        生成所有报告
        
        包括:
        1. 总体综合报告
        2. 各客户独立报告
        3. 共用Feature报告
        4. 风险分析报告
        """
        print("🚀 开始生成多维度分析报告...")
        print("=" * 70)
        
        # 1. 生成综合报告
        print("\n📊 正在生成综合报告...")
        comprehensive = self.analyzer.generate_comprehensive_report(repo_owner, repo_name)
        
        report_file = self.output_dir / f"comprehensive_report_{datetime.now().strftime('%Y%m%d')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(comprehensive, f, indent=2, ensure_ascii=False)
        print(f"✅ 综合报告: {report_file}")
        
        # 2. 生成各客户独立报告
        customers = comprehensive.get('customers', [])
        print(f"\n📂 正在生成 {len(customers)} 个客户的独立报告...")
        
        for customer in customers:
            self._generate_customer_report(
                repo_owner, repo_name, customer,
                comprehensive['customer_reports'][customer]
            )
        
        # 3. 生成共用Feature报告
        print("\n🔗 正在生成共用Feature报告...")
        self._generate_shared_features_report(
            comprehensive.get('shared_features', [])
        )
        
        # 4. 生成风险分析报告
        print("\n⚠️  正在生成风险分析报告...")
        self._generate_risk_report(comprehensive)
        
        # 5. 生成Markdown格式的可读报告
        print("\n📝 正在生成Markdown格式报告...")
        self._generate_markdown_report(comprehensive)
        
        print("\n" + "=" * 70)
        print("✅ 所有报告生成完成！")
        print(f"📁 报告目录: {self.output_dir.absolute()}")
    
    def _generate_customer_report(self, repo_owner: str, repo_name: str, 
                                  customer: str, report_data: Dict):
        """生成单个客户的独立报告"""
        # 补充层级分析
        hierarchy = self.analyzer.analyze_hierarchy_progress(repo_owner, repo_name, customer)
        report_data['hierarchy_progress'] = hierarchy
        
        # 保存JSON
        filename = f"{customer}_report_{datetime.now().strftime('%Y%m%d')}.json"
        filepath = self.customer_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"  ✓ {customer}: {filepath}")
        
        # 同时生成Markdown版本
        self._generate_customer_markdown(customer, report_data)
    
    def _generate_customer_markdown(self, customer: str, data: Dict):
        """生成客户报告的Markdown版本"""
        md_content = f"""# {customer} 项目分析报告

**生成时间**: {data.get('analyzed_at', datetime.now().isoformat())}

---

## 📊 项目概览

- **总Issue数**: {data.get('total_issues', 0)}
- **完成率**: {data.get('completion_rate', 0) * 100:.1f}%

### 状态分布

| 状态 | 数量 |
|------|------|
"""
        
        for state, count in data.get('by_state', {}).items():
            md_content += f"| {state} | {count} |\n"
        
        md_content += "\n### 类型分布\n\n| 类型 | 数量 |\n|------|------|\n"
        for type_, count in data.get('by_type', {}).items():
            md_content += f"| {type_} | {count} |\n"
        
        md_content += "\n### 优先级分布\n\n| 优先级 | 数量 |\n|--------|------|\n"
        for priority, count in data.get('by_priority', {}).items():
            md_content += f"| {priority} | {count} |\n"
        
        # 层级进度
        hierarchy = data.get('hierarchy_progress', {})
        if hierarchy:
            md_content += "\n## 📈 层级进度\n\n| 层级 | 总数 | 已完成 | 完成率 |\n|------|------|--------|--------|\n"
            for level in ['L1', 'L2', 'L3', 'L4']:
                if level in hierarchy:
                    h = hierarchy[level]
                    md_content += f"| {level} | {h['total']} | {h['closed']} | {h['rate']*100:.1f}% |\n"
        
        # 风险提示
        risks = data.get('risks', {})
        if any(risks.values()):
            md_content += "\n## ⚠️ 风险提示\n\n"
            
            if risks.get('high_priority_open'):
                md_content += "### 高优先级未关闭Issue\n\n"
                for risk in risks['high_priority_open'][:5]:
                    md_content += f"- **#{risk['issue_number']}**: {risk['title']} ({risk['priority']}, 已开{risk['days_open']}天)\n"
            
            if risks.get('blocked_chain'):
                md_content += "\n### 被阻塞的Issue\n\n"
                for risk in risks['blocked_chain'][:5]:
                    md_content += f"- **#{risk['issue_number']}**: {risk['title']} - {risk['reason']}\n"
            
            if risks.get('long_time_open'):
                md_content += "\n### 长时间未关闭Issue\n\n"
                for risk in risks['long_time_open'][:5]:
                    md_content += f"- **#{risk['issue_number']}**: {risk['title']} (已开{risk['days_open']}天)\n"
        
        # 保存Markdown
        md_file = self.customer_dir / f"{customer}_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
    
    def _generate_shared_features_report(self, shared_features: List[Dict]):
        """生成共用Feature报告"""
        report = {
            "title": "跨项目共用Feature分析",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_shared_features": len(shared_features),
                "high_risk": sum(1 for f in shared_features if f.get('risk_level') == 'high'),
                "medium_risk": sum(1 for f in shared_features if f.get('risk_level') == 'medium')
            },
            "features": shared_features
        }
        
        # JSON版本
        json_file = self.output_dir / f"shared_features_{datetime.now().strftime('%Y%m%d')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Markdown版本
        md_content = f"""# 跨项目共用Feature分析报告

**生成时间**: {report['generated_at']}

---

## 📊 总体情况

- **共用Feature总数**: {report['summary']['total_shared_features']}
- **高风险（3+客户）**: {report['summary']['high_risk']}
- **中风险（2客户）**: {report['summary']['medium_risk']}

---

## 📋 详细列表

"""
        
        for i, feature in enumerate(shared_features, 1):
            risk_emoji = "🔴" if feature['risk_level'] == 'high' else "🟡"
            md_content += f"""### {i}. {risk_emoji} Feature #{feature['feature_number']}

**标题**: {feature['feature_title']}  
**涉及客户**: {', '.join(feature['customers'])}  
**客户数量**: {feature['customer_count']}  
**风险等级**: {feature['risk_level']}

**风险说明**: 此Feature被{feature['customer_count']}个客户项目依赖，需求可能存在差异，建议：
- 明确各客户的具体需求差异
- 评估是否需要拆分为多个Feature
- 协调开发优先级

---

"""
        
        md_file = self.output_dir / f"shared_features_{datetime.now().strftime('%Y%m%d')}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✅ 共用Feature报告: {json_file}")
    
    def _generate_risk_report(self, comprehensive: Dict):
        """生成风险汇总报告"""
        all_risks = {
            'high_priority_open': [],
            'long_time_open': [],
            'blocked_chain': [],
            'shared_features': comprehensive.get('shared_features', [])
        }
        
        # 汇总各客户的风险
        for customer, report in comprehensive.get('customer_reports', {}).items():
            risks = report.get('risks', {})
            
            for risk_type in ['high_priority_open', 'long_time_open', 'blocked_chain']:
                for risk in risks.get(risk_type, []):
                    risk['customer'] = customer
                    all_risks[risk_type].append(risk)
        
        # 按严重程度排序
        all_risks['high_priority_open'].sort(key=lambda x: x.get('days_open', 0), reverse=True)
        all_risks['long_time_open'].sort(key=lambda x: x.get('days_open', 0), reverse=True)
        
        risk_report = {
            "title": "风险汇总分析",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_high_priority_open": len(all_risks['high_priority_open']),
                "total_long_time_open": len(all_risks['long_time_open']),
                "total_blocked": len(all_risks['blocked_chain']),
                "total_shared_features": len(all_risks['shared_features'])
            },
            "risks": all_risks
        }
        
        # 保存JSON
        json_file = self.output_dir / f"risk_analysis_{datetime.now().strftime('%Y%m%d')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(risk_report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 风险分析报告: {json_file}")
    
    def _generate_markdown_report(self, comprehensive: Dict):
        """生成总体Markdown报告"""
        md_content = f"""# GitHub Issue 综合分析报告

**仓库**: {comprehensive['repo']}  
**生成时间**: {comprehensive['generated_at']}

---

## 📊 总体概览

- **总Issue数**: {comprehensive['summary']['total_issues']}
- **Open**: {comprehensive['summary']['open_issues']}
- **Closed**: {comprehensive['summary']['closed_issues']}
- **被阻塞**: {comprehensive['summary']['blocked_issues']}
- **客户项目数**: {comprehensive['summary']['customer_count']}

---

## 👥 各客户项目情况

| 客户 | 总Issue | 完成率 | Open | Closed | 被阻塞 |
|------|---------|--------|------|--------|--------|
"""
        
        for customer, report in comprehensive.get('customer_reports', {}).items():
            total = report.get('total_issues', 0)
            rate = report.get('completion_rate', 0)
            open_count = report.get('by_state', {}).get('open', 0)
            closed_count = report.get('by_state', {}).get('closed', 0)
            blocked_count = len(report.get('blocked_issues', []))
            
            md_content += f"| {customer} | {total} | {rate*100:.1f}% | {open_count} | {closed_count} | {blocked_count} |\n"
        
        # 共用Feature
        shared = comprehensive.get('shared_features', [])
        if shared:
            md_content += f"\n---\n\n## 🔗 跨项目共用Feature ({len(shared)}个)\n\n"
            for feature in shared[:10]:  # 只显示前10个
                md_content += f"- **#{feature['feature_number']}**: {feature['feature_title']}\n"
                md_content += f"  - 涉及客户: {', '.join(feature['customers'])}\n"
        
        # 阻塞链
        chains = comprehensive.get('blocking_chains', [])
        if chains:
            md_content += f"\n---\n\n## ⛓️ 阻塞链分析 ({len(chains)}条)\n\n"
            for chain in chains[:10]:
                md_content += f"- {chain['description']} (长度: {chain['length']})\n"
        
        md_content += "\n---\n\n## 📝 说明\n\n"
        md_content += "详细的客户报告请查看 `customer_reports/` 目录。\n"
        
        # 保存
        md_file = self.output_dir / f"comprehensive_report_{datetime.now().strftime('%Y%m%d')}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"✅ Markdown总报告: {md_file}")


# ============================================================================
# 主函数
# ============================================================================

def main():
    """主函数"""
    from modules.database_storage.mo_client import MOStorage
    
    storage = MOStorage()
    generator = ImprovedReportGenerator(storage)
    
    # 生成所有报告
    generator.generate_all_reports("matrixorigin", "matrixflow")


if __name__ == "__main__":
    main()
