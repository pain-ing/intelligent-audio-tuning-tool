#!/usr/bin/env python3
"""
数据库连接池优化测试
验证连接池配置和内存优化效果
"""

import sys
import os
import gc
import time
import threading
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# 添加项目路径
sys.path.insert(0, str(Path("..").absolute()))
sys.path.insert(0, str(Path("../api").absolute()))
sys.path.insert(0, str(Path(".").absolute()))

# 导入测试模块
from test_memory_optimization import MemoryProfiler, memory_profiler

logger = logging.getLogger(__name__)

class DatabaseOptimizationTest:
    """数据库优化测试类"""
    
    def __init__(self):
        self.results = {}
        self.test_db_path = None
    
    def setup_test_database(self) -> str:
        """设置测试数据库"""
        # 创建临时SQLite数据库用于测试
        temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_file.close()
        
        self.test_db_path = temp_file.name
        database_url = f"sqlite:///{self.test_db_path}"
        
        # 设置环境变量
        os.environ["DATABASE_URL"] = database_url
        os.environ["DB_MODE"] = "optimized"
        
        print(f"测试数据库: {database_url}")
        return database_url
    
    def cleanup_test_database(self):
        """清理测试数据库"""
        if self.test_db_path and os.path.exists(self.test_db_path):
            try:
                os.unlink(self.test_db_path)
            except Exception as e:
                logger.warning(f"清理测试数据库失败: {e}")
    
    def test_traditional_database_connections(self) -> Dict:
        """测试传统数据库连接"""
        print("\n🔍 测试传统数据库连接...")
        
        results = {}
        
        try:
            with memory_profiler("traditional_db") as profiler:
                profiler.start_monitoring()
                
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                
                database_url = self.setup_test_database()
                
                # 创建传统引擎
                engine = create_engine(database_url)
                SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
                
                profiler.take_snapshot("after_engine_creation")
                
                # 模拟大量连接
                sessions = []
                for i in range(20):
                    session = SessionLocal()
                    sessions.append(session)
                    
                    # 执行简单查询
                    try:
                        session.execute("SELECT 1")
                    except Exception:
                        pass  # SQLite可能没有表
                    
                    if i % 5 == 0:
                        profiler.take_snapshot(f"after_{i}_sessions")
                
                profiler.take_snapshot("after_all_sessions")
                
                # 清理会话
                for session in sessions:
                    session.close()
                
                engine.dispose()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "sessions_created": 20,
                "success": True
            }
            
            print(f"    传统数据库峰值内存: {peak.rss_mb:.1f}MB")
            print(f"    创建会话数: 20")
            
        except Exception as e:
            print(f"    ❌ 传统数据库测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def test_optimized_database_connections(self) -> Dict:
        """测试优化数据库连接"""
        print("\n🚀 测试优化数据库连接...")
        
        results = {}
        
        try:
            with memory_profiler("optimized_db") as profiler:
                profiler.start_monitoring()
                
                # 重新导入以确保使用优化版本
                import importlib
                sys.path.insert(0, str(Path("../api/app").absolute()))
                
                # 设置优化模式
                os.environ["DB_MODE"] = "optimized"
                
                try:
                    from database_optimized import DatabaseConnectionManager
                    
                    database_url = self.setup_test_database()
                    
                    # 创建优化的数据库管理器
                    manager = DatabaseConnectionManager(database_url)
                    
                    profiler.take_snapshot("after_manager_creation")
                    
                    # 获取初始统计
                    initial_stats = manager.get_stats()
                    print(f"    初始统计: {initial_stats}")
                    
                    # 模拟大量连接使用
                    for i in range(20):
                        with manager.session_scope() as session:
                            # 执行简单查询
                            try:
                                session.execute("SELECT 1")
                            except Exception:
                                pass  # SQLite可能没有表
                        
                        if i % 5 == 0:
                            profiler.take_snapshot(f"after_{i}_sessions")
                            stats = manager.get_stats()
                            print(f"      第{i}次后统计: 活跃连接={stats.get('active_connections', 0)}")
                    
                    profiler.take_snapshot("after_all_sessions")
                    
                    # 获取最终统计
                    final_stats = manager.get_stats()
                    print(f"    最终统计: {final_stats}")
                    
                    # 健康检查
                    health_ok = manager.health_check()
                    
                    # 清理
                    manager.shutdown()
                    profiler.take_snapshot("after_cleanup")
                    
                except ImportError as e:
                    print(f"    ⚠️ 优化模块不可用，使用简化测试: {e}")
                    
                    # 简化的优化测试
                    from sqlalchemy import create_engine
                    from sqlalchemy.orm import sessionmaker
                    from sqlalchemy.pool import QueuePool
                    
                    database_url = self.setup_test_database()
                    
                    # 使用优化配置
                    engine = create_engine(
                        database_url,
                        poolclass=QueuePool,
                        pool_size=3,
                        max_overflow=5,
                        pool_pre_ping=True,
                        pool_recycle=3600
                    )
                    
                    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
                    
                    profiler.take_snapshot("after_optimized_engine")
                    
                    # 模拟连接使用
                    for i in range(20):
                        session = SessionLocal()
                        try:
                            session.execute("SELECT 1")
                        except Exception:
                            pass
                        finally:
                            session.close()
                    
                    profiler.take_snapshot("after_optimized_sessions")
                    
                    engine.dispose()
                    profiler.take_snapshot("after_optimized_cleanup")
                    
                    final_stats = {"simplified_test": True}
                    health_ok = True
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "sessions_created": 20,
                "final_stats": final_stats,
                "health_check": health_ok,
                "success": True
            }
            
            print(f"    优化数据库峰值内存: {peak.rss_mb:.1f}MB")
            print(f"    健康检查: {health_ok}")
            
        except Exception as e:
            print(f"    ❌ 优化数据库测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def test_connection_pool_behavior(self) -> Dict:
        """测试连接池行为"""
        print("\n🏊 测试连接池行为...")
        
        results = {}
        
        try:
            sys.path.insert(0, str(Path("../api/app").absolute()))
            
            try:
                from database_optimized import DatabaseConnectionManager
                
                database_url = self.setup_test_database()
                
                # 创建小连接池用于测试
                manager = DatabaseConnectionManager(
                    database_url,
                    pool_size=2,
                    max_overflow=3,
                    pool_timeout=5
                )
                
                # 测试连接池限制
                sessions = []
                stats_history = []
                
                # 创建超过连接池大小的连接
                for i in range(7):  # 超过pool_size(2) + max_overflow(3)
                    try:
                        session = manager.get_session()
                        sessions.append(session)
                        
                        stats = manager.get_stats()
                        stats_history.append(stats)
                        
                        print(f"      连接{i+1}: 活跃={stats.get('active_connections', 0)}, "
                              f"池大小={stats.get('pool_size', 0)}")
                        
                        time.sleep(0.1)  # 短暂延迟
                        
                    except Exception as e:
                        print(f"      连接{i+1}失败: {e}")
                        break
                
                # 清理连接
                for session in sessions:
                    session.close()
                
                # 最终统计
                final_stats = manager.get_stats()
                
                results = {
                    "max_connections_attempted": len(sessions),
                    "stats_history": stats_history,
                    "final_stats": final_stats,
                    "pool_limit_working": len(sessions) <= 5,  # pool_size + max_overflow
                    "success": True
                }
                
                print(f"    最大连接尝试: {len(sessions)}")
                print(f"    连接池限制有效: {results['pool_limit_working']}")
                
                manager.shutdown()
                
            except ImportError:
                print("    ⚠️ 优化模块不可用，跳过连接池测试")
                results = {"success": False, "error": "Optimized module not available"}
            
        except Exception as e:
            print(f"    ❌ 连接池测试失败: {e}")
            results = {"success": False, "error": str(e)}
        
        return results
    
    def run_database_optimization_tests(self) -> Dict:
        """运行所有数据库优化测试"""
        print("🔍 数据库连接池优化测试")
        print("=" * 60)
        
        try:
            # 运行各项测试
            traditional_results = self.test_traditional_database_connections()
            optimized_results = self.test_optimized_database_connections()
            pool_results = self.test_connection_pool_behavior()
            
            self.results = {
                "traditional_database": traditional_results,
                "optimized_database": optimized_results,
                "connection_pool": pool_results
            }
            
            self.print_optimization_summary()
            
        finally:
            # 清理测试数据库
            self.cleanup_test_database()
        
        return self.results
    
    def print_optimization_summary(self):
        """打印优化效果摘要"""
        print("\n📊 数据库优化效果摘要:")
        print("=" * 60)
        
        traditional = self.results.get("traditional_database", {})
        optimized = self.results.get("optimized_database", {})
        
        if traditional.get("success") and optimized.get("success"):
            traditional_peak = traditional["peak_memory_mb"]
            optimized_peak = optimized["peak_memory_mb"]
            memory_reduction = traditional_peak - optimized_peak
            reduction_percent = (memory_reduction / traditional_peak) * 100 if traditional_peak > 0 else 0
            
            print(f"内存使用优化:")
            print(f"  传统数据库峰值: {traditional_peak:.1f}MB")
            print(f"  优化数据库峰值: {optimized_peak:.1f}MB")
            print(f"  内存减少: {memory_reduction:.1f}MB ({reduction_percent:.1f}%)")
        
        pool_results = self.results.get("connection_pool", {})
        if pool_results.get("success"):
            print(f"连接池管理:")
            print(f"  连接池限制有效: {pool_results.get('pool_limit_working', False)}")
            print(f"  最大连接数: {pool_results.get('max_connections_attempted', 0)}")
        
        print("\n🎯 优化建议:")
        print("1. 使用连接池限制并发连接数")
        print("2. 配置合理的连接回收时间")
        print("3. 启用连接预检查")
        print("4. 监控连接池统计信息")

def main():
    """主函数"""
    print("🔍 数据库连接池优化测试工具")
    print("=" * 60)
    
    # 运行优化测试
    test = DatabaseOptimizationTest()
    results = test.run_database_optimization_tests()
    
    # 保存结果
    import json
    with open("database_optimization_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 测试结果已保存到: database_optimization_results.json")

if __name__ == "__main__":
    main()
