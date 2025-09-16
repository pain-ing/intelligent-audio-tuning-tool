"""
内存优化的数据库连接池配置
实现连接池优化、查询缓存和内存管理
"""

import os
import time
import threading
import logging
from typing import Dict, Any, Optional, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, event, pool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool, StaticPool, NullPool
import psutil

logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """数据库连接管理器"""
    
    def __init__(self, database_url: str, **kwargs):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._lock = threading.Lock()
        self._connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "peak_connections": 0,
            "connection_errors": 0
        }
        
        # 根据数据库类型和可用内存优化配置
        self.config = self._get_optimized_config(**kwargs)
        self._setup_engine()
        
        logger.info(f"数据库连接管理器初始化完成: {self.config}")
    
    def _get_optimized_config(self, **kwargs) -> Dict[str, Any]:
        """获取优化的数据库配置"""
        # 检测数据库类型
        is_sqlite = self.database_url.startswith("sqlite")
        is_postgres = self.database_url.startswith("postgresql")
        is_mysql = self.database_url.startswith("mysql")
        
        # 获取可用内存
        try:
            available_memory_gb = psutil.virtual_memory().available / (1024**3)
        except Exception:
            available_memory_gb = 4.0  # 默认假设4GB
        
        # 基础配置
        config = {
            "echo": kwargs.get("echo", False),
            "echo_pool": kwargs.get("echo_pool", False),
            "pool_pre_ping": True,  # 连接前检查
            "pool_recycle": 3600,   # 1小时回收连接
            "query_cache_size": 500,  # 查询缓存大小
        }
        
        if is_sqlite:
            # SQLite优化配置
            config.update({
                "poolclass": StaticPool,
                "connect_args": {
                    "check_same_thread": False,
                    "timeout": 20,
                    "isolation_level": None  # 自动提交模式
                }
            })
            # 移除SQLite不支持的连接池参数
            config.pop("pool_recycle", None)
        else:
            # PostgreSQL/MySQL优化配置
            if available_memory_gb > 8:
                pool_size = 10
                max_overflow = 20
            elif available_memory_gb > 4:
                pool_size = 5
                max_overflow = 10
            else:
                pool_size = 3
                max_overflow = 5
            
            config.update({
                "poolclass": QueuePool,
                "pool_size": pool_size,
                "max_overflow": max_overflow,
                "pool_timeout": 30,
                "pool_recycle": 3600,
            })
            
            if is_postgres:
                config["connect_args"] = {
                    "application_name": "audio_tuner",
                    "connect_timeout": 10,
                    "server_side_cursors": False  # 减少服务器内存使用
                }
            elif is_mysql:
                config["connect_args"] = {
                    "charset": "utf8mb4",
                    "connect_timeout": 10,
                    "autocommit": True
                }
        
        # 合并用户提供的配置
        config.update(kwargs)
        return config
    
    def _setup_engine(self):
        """设置数据库引擎"""
        with self._lock:
            if self.engine is None:
                self.engine = create_engine(self.database_url, **self.config)
                self.SessionLocal = sessionmaker(
                    autocommit=False, 
                    autoflush=False, 
                    bind=self.engine,
                    expire_on_commit=False  # 减少查询次数
                )
                
                # 注册事件监听器
                self._register_event_listeners()
    
    def _register_event_listeners(self):
        """注册数据库事件监听器"""
        @event.listens_for(self.engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            with self._lock:
                self._connection_stats["total_connections"] += 1
                self._connection_stats["active_connections"] += 1
                if self._connection_stats["active_connections"] > self._connection_stats["peak_connections"]:
                    self._connection_stats["peak_connections"] = self._connection_stats["active_connections"]
            
            logger.debug(f"数据库连接建立: {self._connection_stats['active_connections']} 活跃连接")
        
        @event.listens_for(self.engine, "close")
        def on_close(dbapi_conn, connection_record):
            with self._lock:
                self._connection_stats["active_connections"] -= 1
            
            logger.debug(f"数据库连接关闭: {self._connection_stats['active_connections']} 活跃连接")
        
        @event.listens_for(self.engine, "close_detached")
        def on_close_detached(dbapi_conn):
            with self._lock:
                self._connection_stats["active_connections"] -= 1
        
        @event.listens_for(self.engine, "handle_error")
        def on_error(exception_context):
            with self._lock:
                self._connection_stats["connection_errors"] += 1
            
            logger.error(f"数据库连接错误: {exception_context.original_exception}")
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        if self.SessionLocal is None:
            self._setup_engine()
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """数据库会话上下文管理器"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取连接统计信息"""
        with self._lock:
            stats = self._connection_stats.copy()
        
        # 添加连接池统计
        if hasattr(self.engine.pool, 'size'):
            stats.update({
                "pool_size": self.engine.pool.size(),
                "checked_in": self.engine.pool.checkedin(),
                "checked_out": self.engine.pool.checkedout(),
                "overflow": getattr(self.engine.pool, 'overflow', 0),
                "invalid": getattr(self.engine.pool, 'invalid', 0)
            })
        
        return stats
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            with self.session_scope() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"数据库健康检查失败: {e}")
            return False
    
    def cleanup_connections(self):
        """清理连接池"""
        if self.engine and hasattr(self.engine.pool, 'dispose'):
            self.engine.pool.dispose()
            logger.info("数据库连接池已清理")
    
    def shutdown(self):
        """关闭数据库连接管理器"""
        if self.engine:
            self.engine.dispose()
            logger.info("数据库连接管理器已关闭")

class OptimizedSession:
    """优化的数据库会话"""
    
    def __init__(self, session: Session):
        self.session = session
        self._query_count = 0
        self._start_time = time.time()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self._start_time
        if self._query_count > 10 or duration > 5.0:
            logger.warning(f"会话执行了 {self._query_count} 个查询，耗时 {duration:.2f}秒")
        
        if exc_type:
            self.session.rollback()
        else:
            self.session.commit()
        
        self.session.close()
    
    def execute(self, *args, **kwargs):
        """执行查询并计数"""
        self._query_count += 1
        return self.session.execute(*args, **kwargs)
    
    def query(self, *args, **kwargs):
        """查询并计数"""
        self._query_count += 1
        return self.session.query(*args, **kwargs)
    
    def add(self, *args, **kwargs):
        return self.session.add(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        return self.session.delete(*args, **kwargs)
    
    def commit(self):
        return self.session.commit()
    
    def rollback(self):
        return self.session.rollback()
    
    def close(self):
        return self.session.close()

# 全局数据库管理器
_db_manager = None
_manager_lock = threading.Lock()

def get_database_manager() -> DatabaseConnectionManager:
    """获取全局数据库管理器"""
    global _db_manager
    
    if _db_manager is None:
        with _manager_lock:
            if _db_manager is None:
                database_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL", "postgresql://user:pass@localhost:5432/audio")
                _db_manager = DatabaseConnectionManager(database_url)
    
    return _db_manager

def get_optimized_db() -> Generator[OptimizedSession, None, None]:
    """获取优化的数据库会话"""
    manager = get_database_manager()
    session = manager.get_session()
    
    with OptimizedSession(session) as opt_session:
        yield opt_session

def get_db_stats() -> Dict[str, Any]:
    """获取数据库统计信息"""
    try:
        manager = get_database_manager()
        return manager.get_stats()
    except Exception as e:
        logger.error(f"获取数据库统计失败: {e}")
        return {"error": str(e)}

def cleanup_database_connections():
    """清理数据库连接"""
    try:
        manager = get_database_manager()
        manager.cleanup_connections()
    except Exception as e:
        logger.error(f"清理数据库连接失败: {e}")

# 兼容性函数
def get_db() -> Generator[Session, None, None]:
    """获取数据库会话（兼容性函数）"""
    db_mode = os.getenv("DB_MODE", "optimized").lower()
    
    if db_mode == "optimized":
        manager = get_database_manager()
        with manager.session_scope() as session:
            yield session
    else:
        # 传统方式
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        database_url = os.getenv("DATABASE_URL") or os.getenv("DB_URL", "postgresql://user:pass@localhost:5432/audio")
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

# 声明式基类
Base = declarative_base()
