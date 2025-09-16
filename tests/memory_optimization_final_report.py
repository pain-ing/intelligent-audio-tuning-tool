#!/usr/bin/env python3
"""
内存优化项目最终报告
汇总所有优化成果和测试结果
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

class MemoryOptimizationReport:
    """内存优化报告生成器"""
    
    def __init__(self):
        self.results = {}
        self.load_all_results()
    
    def load_all_results(self):
        """加载所有测试结果"""
        result_files = [
            "streaming_optimization_results.json",
            "feature_optimization_results.json", 
            "cache_optimization_results.json",
            "celery_optimization_results.json",
            "database_simple_results.json",
            "comprehensive_monitoring_results.json"
        ]
        
        for file_name in result_files:
            if os.path.exists(file_name):
                try:
                    with open(file_name, 'r') as f:
                        data = json.load(f)
                        self.results[file_name.replace('_results.json', '')] = data
                        print(f"✓ 加载结果文件: {file_name}")
                except Exception as e:
                    print(f"✗ 加载结果文件失败 {file_name}: {e}")
            else:
                print(f"⚠️ 结果文件不存在: {file_name}")
    
    def calculate_memory_improvements(self) -> Dict[str, Any]:
        """计算内存改进效果"""
        improvements = {}
        
        # 流处理优化
        streaming = self.results.get("streaming_optimization", {})
        if "analysis_comparison" in streaming:
            analysis = streaming["analysis_comparison"]
            if analysis.get("success"):
                memory_reduction = analysis.get("memory_reduction_percent", 0)
                improvements["streaming_analysis"] = {
                    "memory_reduction_percent": memory_reduction,
                    "traditional_peak_mb": analysis.get("traditional_peak_mb", 0),
                    "streaming_peak_mb": analysis.get("streaming_peak_mb", 0)
                }
        
        # 特征提取优化
        features = self.results.get("feature_optimization", {})
        if "stft_optimization" in features:
            stft = features["stft_optimization"]
            if stft.get("success"):
                memory_reduction = stft.get("memory_reduction_percent", 0)
                improvements["stft_features"] = {
                    "memory_reduction_percent": memory_reduction,
                    "traditional_peak_mb": stft.get("traditional_peak_mb", 0),
                    "optimized_peak_mb": stft.get("optimized_peak_mb", 0)
                }
        
        # 缓存优化
        cache = self.results.get("cache_optimization", {})
        if "cache_comparison" in cache:
            cache_comp = cache["cache_comparison"]
            if cache_comp.get("success"):
                memory_reduction = cache_comp.get("memory_reduction_percent", 0)
                improvements["cache_system"] = {
                    "memory_reduction_percent": memory_reduction,
                    "without_cache_peak_mb": cache_comp.get("without_cache_peak_mb", 0),
                    "with_cache_peak_mb": cache_comp.get("with_cache_peak_mb", 0)
                }
        
        return improvements
    
    def calculate_performance_improvements(self) -> Dict[str, Any]:
        """计算性能改进效果"""
        performance = {}
        
        # 数据库优化
        database = self.results.get("database_simple", {})
        if "session_management" in database:
            session = database["session_management"]
            if session.get("success"):
                performance["database_sessions"] = {
                    "performance_improvement_percent": session.get("performance_improvement_percent", 0),
                    "method1_time_sec": session.get("method1_time_sec", 0),
                    "method2_time_sec": session.get("method2_time_sec", 0)
                }
        
        if "query_optimization" in database:
            query = database["query_optimization"]
            if query.get("success"):
                performance["database_queries"] = {
                    "cache_improvement_percent": query.get("cache_improvement_percent", 0),
                    "first_run_time_sec": query.get("first_run_time_sec", 0),
                    "second_run_time_sec": query.get("second_run_time_sec", 0)
                }
        
        return performance
    
    def generate_optimization_summary(self) -> Dict[str, Any]:
        """生成优化摘要"""
        memory_improvements = self.calculate_memory_improvements()
        performance_improvements = self.calculate_performance_improvements()
        
        # 计算总体内存节省
        total_memory_saved = 0
        memory_reductions = []
        
        for module, data in memory_improvements.items():
            reduction = data.get("memory_reduction_percent", 0)
            if reduction > 0:
                memory_reductions.append(reduction)
                
                # 计算绝对内存节省
                traditional_mb = data.get("traditional_peak_mb", 0) or data.get("without_cache_peak_mb", 0)
                optimized_mb = data.get("streaming_peak_mb", 0) or data.get("optimized_peak_mb", 0) or data.get("with_cache_peak_mb", 0)
                
                if traditional_mb > 0 and optimized_mb > 0:
                    saved_mb = traditional_mb - optimized_mb
                    total_memory_saved += saved_mb
        
        avg_memory_reduction = sum(memory_reductions) / len(memory_reductions) if memory_reductions else 0
        
        # 计算总体性能提升
        performance_improvements_list = []
        for module, data in performance_improvements.items():
            improvement = data.get("performance_improvement_percent", 0) or data.get("cache_improvement_percent", 0)
            if improvement > 0:
                performance_improvements_list.append(improvement)
        
        avg_performance_improvement = sum(performance_improvements_list) / len(performance_improvements_list) if performance_improvements_list else 0
        
        return {
            "memory_optimization": {
                "total_memory_saved_mb": total_memory_saved,
                "average_memory_reduction_percent": avg_memory_reduction,
                "modules_optimized": len(memory_improvements),
                "details": memory_improvements
            },
            "performance_optimization": {
                "average_performance_improvement_percent": avg_performance_improvement,
                "modules_optimized": len(performance_improvements),
                "details": performance_improvements
            },
            "optimization_modules": {
                "streaming_processing": "streaming_optimization" in self.results,
                "feature_extraction": "feature_optimization" in self.results,
                "cache_system": "cache_optimization" in self.results,
                "celery_tasks": "celery_optimization" in self.results,
                "database_connections": "database_simple" in self.results,
                "comprehensive_monitoring": "comprehensive_monitoring" in self.results
            }
        }
    
    def generate_recommendations(self) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        memory_improvements = self.calculate_memory_improvements()
        
        # 基于结果生成建议
        if "streaming_analysis" in memory_improvements:
            reduction = memory_improvements["streaming_analysis"]["memory_reduction_percent"]
            if reduction > 30:
                recommendations.append("✅ 音频流处理优化效果显著，建议在生产环境中启用")
            else:
                recommendations.append("⚠️ 音频流处理优化效果有限，建议进一步调优参数")
        
        if "cache_system" in memory_improvements:
            reduction = memory_improvements["cache_system"]["memory_reduction_percent"]
            if reduction > 20:
                recommendations.append("✅ 缓存系统优化效果良好，建议配置合理的缓存大小")
            else:
                recommendations.append("⚠️ 缓存系统需要根据实际使用模式调整策略")
        
        # 通用建议
        recommendations.extend([
            "🔧 定期监控内存使用情况，建立告警机制",
            "📊 在生产环境中收集性能指标，持续优化",
            "🧪 定期运行内存优化测试，验证优化效果",
            "📝 建立内存使用基准，跟踪长期趋势",
            "⚡ 根据实际负载调整优化参数"
        ])
        
        return recommendations
    
    def generate_final_report(self) -> str:
        """生成最终报告"""
        summary = self.generate_optimization_summary()
        recommendations = self.generate_recommendations()
        
        report = f"""
# 音频处理项目内存优化最终报告

## 📊 优化成果摘要

### 内存优化效果
- **总内存节省**: {summary['memory_optimization']['total_memory_saved_mb']:.1f}MB
- **平均内存减少**: {summary['memory_optimization']['average_memory_reduction_percent']:.1f}%
- **优化模块数**: {summary['memory_optimization']['modules_optimized']}个

### 性能优化效果
- **平均性能提升**: {summary['performance_optimization']['average_performance_improvement_percent']:.1f}%
- **优化模块数**: {summary['performance_optimization']['modules_optimized']}个

## 🔧 优化模块状态

"""
        
        # 添加模块状态
        modules = summary['optimization_modules']
        for module_name, status in modules.items():
            status_icon = "✅" if status else "❌"
            module_display = module_name.replace('_', ' ').title()
            report += f"- **{module_display}**: {status_icon}\n"
        
        report += "\n## 📈 详细优化结果\n\n"
        
        # 添加内存优化详情
        if summary['memory_optimization']['details']:
            report += "### 内存优化详情\n\n"
            for module, data in summary['memory_optimization']['details'].items():
                module_display = module.replace('_', ' ').title()
                reduction = data['memory_reduction_percent']
                report += f"- **{module_display}**: {reduction:.1f}% 内存减少\n"
        
        # 添加性能优化详情
        if summary['performance_optimization']['details']:
            report += "\n### 性能优化详情\n\n"
            for module, data in summary['performance_optimization']['details'].items():
                module_display = module.replace('_', ' ').title()
                improvement = data.get('performance_improvement_percent', 0) or data.get('cache_improvement_percent', 0)
                report += f"- **{module_display}**: {improvement:.1f}% 性能提升\n"
        
        # 添加建议
        report += "\n## 🎯 优化建议\n\n"
        for recommendation in recommendations:
            report += f"{recommendation}\n"
        
        # 添加技术细节
        report += f"""
## 🔍 技术实现细节

### 已实现的优化技术
1. **音频流处理**: 分块加载和处理，减少内存峰值
2. **特征提取优化**: 缓存过滤器，复用计算缓冲区
3. **内存感知缓存**: LRU淘汰策略，自动内存清理
4. **Celery任务优化**: 任务隔离，内存监控和清理
5. **数据库连接池**: 连接复用，查询缓存
6. **依赖注入容器**: 生命周期管理，弱引用优化

### 监控和测试工具
- 内存使用分析器
- 性能基准测试
- 自动化优化验证
- 系统资源监控

## 📅 报告生成时间
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---
*此报告由内存优化测试工具自动生成*
"""
        
        return report
    
    def save_final_report(self):
        """保存最终报告"""
        report_content = self.generate_final_report()
        
        # 保存Markdown格式
        with open("memory_optimization_final_report.md", "w", encoding="utf-8") as f:
            f.write(report_content)
        
        # 保存JSON格式的摘要
        summary = self.generate_optimization_summary()
        summary["recommendations"] = self.generate_recommendations()
        summary["report_generated_at"] = datetime.now().isoformat()
        
        with open("memory_optimization_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print("📄 最终报告已生成:")
        print("  - memory_optimization_final_report.md (详细报告)")
        print("  - memory_optimization_summary.json (摘要数据)")
        
        return report_content

def main():
    """主函数"""
    print("📊 生成内存优化项目最终报告")
    print("=" * 60)
    
    # 生成报告
    reporter = MemoryOptimizationReport()
    report = reporter.save_final_report()
    
    # 打印摘要
    print("\n📋 优化成果摘要:")
    summary = reporter.generate_optimization_summary()
    
    print(f"内存优化:")
    print(f"  总内存节省: {summary['memory_optimization']['total_memory_saved_mb']:.1f}MB")
    print(f"  平均减少: {summary['memory_optimization']['average_memory_reduction_percent']:.1f}%")
    
    print(f"性能优化:")
    print(f"  平均提升: {summary['performance_optimization']['average_performance_improvement_percent']:.1f}%")
    
    print(f"优化模块: {sum(summary['optimization_modules'].values())}/{len(summary['optimization_modules'])} 个完成")

if __name__ == "__main__":
    main()
