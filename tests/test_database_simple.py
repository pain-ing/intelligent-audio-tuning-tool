#!/usr/bin/env python3
"""
数据库连接池优化简化测试
验证连接池配置和内存优化效果
"""

import sys
import os
import gc
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# 添加项目路径
sys.path.insert(0, str(Path("..").absolute()))
sys.path.insert(0, str(Path("../api/app").absolute()))
sys.path.insert(0, str(Path(".").absolute()))

# 导入测试模块
from test_memory_optimization import MemoryProfiler, memory_profiler

logger = logging.getLogger(__name__)

class SimpleDatabaseOptimizationTest:
    """简化的数据库优化测试类"""
    
    def __init__(self):
        self.results = {}
        self.test_db_path = None
    
    def setup_test_database(self) -> str:
        """设置测试数据库"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_file.close()
        
        self.test_db_path = temp_file.name
        database_url = f"sqlite:///{self.test_db_path}"
        
        print(f"测试数据库: {database_url}")
        return database_url
    
    def cleanup_test_database(self):
        """清理测试数据库"""
        if self.test_db_path and os.path.exists(self.test_db_path):
            try:
                os.unlink(self.test_db_path)
            except Exception as e:
                logger.warning(f"清理测试数据库失败: {e}")
    
    def test_traditional_database_memory(self) -> Dict:
        """测试传统数据库内存使用"""
        print("\n🔍 测试传统数据库内存使用...")
        
        results = {}
        
        try:
            with memory_profiler("traditional_db") as profiler:
                profiler.start_monitoring()
                
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                
                database_url = self.setup_test_database()
                
                # 创建传统引擎（无优化）
                engine = create_engine(database_url)
                SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
                
                profiler.take_snapshot("after_engine_creation")
                
                # 模拟大量会话使用
                sessions = []
                for i in range(50):
                    session = SessionLocal()
                    sessions.append(session)
                    
                    # 执行查询
                    try:
                        session.execute("SELECT 1")
                    except Exception:
                        pass
                    
                    if i % 10 == 0:
                        profiler.take_snapshot(f"after_{i}_sessions")
                
                profiler.take_snapshot("after_all_sessions")
                
                # 清理
                for session in sessions:
                    session.close()
                
                engine.dispose()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "sessions_created": 50,
                "success": True
            }
            
            print(f"    传统数据库峰值内存: {peak.rss_mb:.1f}MB")
            print(f"    内存增长率: {growth:.2f}")
            
        except Exception as e:
            print(f"    ❌ 传统数据库测试失败: {e}")
            results = {"success": False, "error": str(e)}
        finally:
            self.cleanup_test_database()
        
        return results
    
    def test_optimized_database_memory(self) -> Dict:
        """测试优化数据库内存使用"""
        print("\n🚀 测试优化数据库内存使用...")
        
        results = {}
        
        try:
            with memory_profiler("optimized_db") as profiler:
                profiler.start_monitoring()
                
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                from sqlalchemy.pool import StaticPool
                
                database_url = self.setup_test_database()
                
                # 创建优化引擎
                engine = create_engine(
                    database_url,
                    poolclass=StaticPool,
                    pool_pre_ping=True,
                    connect_args={
                        "check_same_thread": False,
                        "timeout": 20
                    },
                    echo=False
                )
                
                SessionLocal = sessionmaker(
                    autocommit=False, 
                    autoflush=False, 
                    bind=engine,
                    expire_on_commit=False  # 减少查询
                )
                
                profiler.take_snapshot("after_optimized_engine")
                
                # 模拟大量会话使用（使用上下文管理器）
                for i in range(50):
                    session = SessionLocal()
                    try:
                        # 执行查询
                        session.execute("SELECT 1")
                        session.commit()
                    except Exception:
                        session.rollback()
                    finally:
                        session.close()
                    
                    if i % 10 == 0:
                        profiler.take_snapshot(f"after_{i}_sessions")
                
                profiler.take_snapshot("after_all_sessions")
                
                # 清理
                engine.dispose()
                profiler.take_snapshot("after_cleanup")
            
            peak = profiler.get_peak_memory()
            growth = profiler.get_memory_growth()
            
            results = {
                "peak_memory_mb": peak.rss_mb,
                "memory_growth_rate": growth,
                "sessions_created": 50,
                "success": True
            }
            
            print(f"    优化数据库峰值内存: {peak.rss_mb:.1f}MB")
            print(f"    内存增长率: {growth:.2f}")
            
        except Exception as e:
            print(f"    ❌ 优化数据库测试失败: {e}")
            results = {"success": False, "error": str(e)}
        finally:
            self.cleanup_test_database()
        
        return results
    
    def test_session_management(self) -> Dict:
        """测试会话管理优化"""
        print("\n📋 测试会话管理优化...")
        
        results = {}
        
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            from sqlalchemy.pool import StaticPool
            
            database_url = self.setup_test_database()
            
            # 创建优化引擎
            engine = create_engine(
                database_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False}
            )
            
            SessionLocal = sessionmaker(
                autocommit=False, 
                autoflush=False, 
                bind=engine,
                expire_on_commit=False
            )
            
            # 测试会话重用 vs 新建
            start_time = time.time()
            
            from sqlalchemy import text

            # 方法1：每次新建会话
            for i in range(100):
                session = SessionLocal()
                try:
                    session.execute(text("SELECT 1"))
                    session.commit()
                finally:
                    session.close()

            method1_time = time.time() - start_time

            # 方法2：重用会话（模拟连接池效果）
            start_time = time.time()
            session = SessionLocal()

            try:
                for i in range(100):
                    session.execute(text("SELECT 1"))
                    if i % 10 == 0:  # 定期提交
                        session.commit()
                session.commit()
            finally:
                session.close()
            
            method2_time = time.time() - start_time
            
            # 计算性能提升
            performance_improvement = (method1_time - method2_time) / method1_time * 100
            
            results = {
                "method1_time_sec": method1_time,
                "method2_time_sec": method2_time,
                "performance_improvement_percent": performance_improvement,
                "queries_executed": 100,
                "success": True
            }
            
            print(f"    每次新建会话: {method1_time:.3f}秒")
            print(f"    重用会话: {method2_time:.3f}秒")
            print(f"    性能提升: {performance_improvement:.1f}%")
            
            engine.dispose()
            
        except Exception as e:
            print(f"    ❌ 会话管理测试失败: {e}")
            results = {"success": False, "error": str(e)}
        finally:
            self.cleanup_test_database()
        
        return results
    
    def test_query_optimization(self) -> Dict:
        """测试查询优化"""
        print("\n⚡ 测试查询优化...")
        
        results = {}
        
        try:
            from sqlalchemy import create_engine, text
            from sqlalchemy.orm import sessionmaker
            
            database_url = self.setup_test_database()
            
            # 创建优化引擎
            engine = create_engine(
                database_url,
                pool_pre_ping=True,
                query_cache_size=1000,  # 查询缓存
                connect_args={"check_same_thread": False}
            )
            
            SessionLocal = sessionmaker(bind=engine)
            
            # 创建测试表
            with engine.connect() as conn:
                conn.execute(text("CREATE TABLE IF NOT EXISTS test_table (id INTEGER, value TEXT)"))
                conn.execute(text("INSERT INTO test_table VALUES (1, 'test1'), (2, 'test2'), (3, 'test3')"))
                conn.commit()
            
            # 测试查询缓存效果
            session = SessionLocal()
            
            # 第一次查询（无缓存）
            start_time = time.time()
            for i in range(100):
                result = session.execute(text("SELECT * FROM test_table WHERE id = :id"), {"id": 1})
                list(result)  # 消费结果
            first_run_time = time.time() - start_time
            
            # 第二次查询（可能有缓存）
            start_time = time.time()
            for i in range(100):
                result = session.execute(text("SELECT * FROM test_table WHERE id = :id"), {"id": 1})
                list(result)  # 消费结果
            second_run_time = time.time() - start_time
            
            session.close()
            
            # 计算缓存效果
            cache_improvement = (first_run_time - second_run_time) / first_run_time * 100 if first_run_time > 0 else 0
            
            results = {
                "first_run_time_sec": first_run_time,
                "second_run_time_sec": second_run_time,
                "cache_improvement_percent": cache_improvement,
                "queries_executed": 200,
                "success": True
            }
            
            print(f"    第一次运行: {first_run_time:.3f}秒")
            print(f"    第二次运行: {second_run_time:.3f}秒")
            print(f"    缓存效果: {cache_improvement:.1f}%")
            
            engine.dispose()
            
        except Exception as e:
            print(f"    ❌ 查询优化测试失败: {e}")
            results = {"success": False, "error": str(e)}
        finally:
            self.cleanup_test_database()
        
        return results
    
    def run_database_optimization_tests(self) -> Dict:
        """运行所有数据库优化测试"""
        print("🔍 数据库连接池优化测试")
        print("=" * 60)
        
        # 运行各项测试
        traditional_results = self.test_traditional_database_memory()
        optimized_results = self.test_optimized_database_memory()
        session_results = self.test_session_management()
        query_results = self.test_query_optimization()
        
        self.results = {
            "traditional_database": traditional_results,
            "optimized_database": optimized_results,
            "session_management": session_results,
            "query_optimization": query_results
        }
        
        self.print_optimization_summary()
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
        
        session_results = self.results.get("session_management", {})
        if session_results.get("success"):
            print(f"会话管理优化:")
            print(f"  性能提升: {session_results['performance_improvement_percent']:.1f}%")
        
        query_results = self.results.get("query_optimization", {})
        if query_results.get("success"):
            print(f"查询优化:")
            print(f"  缓存效果: {query_results['cache_improvement_percent']:.1f}%")
        
        print("\n🎯 优化建议:")
        print("1. 使用连接池和会话重用")
        print("2. 启用查询缓存")
        print("3. 配置连接预检查")
        print("4. 优化会话生命周期管理")

def main():
    """主函数"""
    print("🔍 数据库连接池优化测试工具")
    print("=" * 60)
    
    # 运行优化测试
    test = SimpleDatabaseOptimizationTest()
    results = test.run_database_optimization_tests()
    
    # 保存结果
    import json
    with open("database_simple_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n💾 测试结果已保存到: database_simple_results.json")

if __name__ == "__main__":
    main()
