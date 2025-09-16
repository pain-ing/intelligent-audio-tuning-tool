from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# 导入优化的数据库管理器
try:
    from .database_optimized import (
        get_database_manager,
        get_optimized_db,
        get_db_stats,
        cleanup_database_connections,
        Base as OptimizedBase
    )
    OPTIMIZED_DB_AVAILABLE = True
except ImportError:
    OPTIMIZED_DB_AVAILABLE = False

# Prefer DATABASE_URL for consistency; fallback to DB_URL for backward compatibility
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("DB_URL", "postgresql://user:pass@localhost:5432/audio")

# 数据库模式选择
DB_MODE = os.getenv("DB_MODE", "optimized" if OPTIMIZED_DB_AVAILABLE else "traditional").lower()

if DB_MODE == "optimized" and OPTIMIZED_DB_AVAILABLE:
    # 使用优化的数据库管理器
    Base = OptimizedBase

    def get_db():
        """获取数据库会话（优化版本）"""
        manager = get_database_manager()
        with manager.session_scope() as session:
            yield session

    def get_db_statistics():
        """获取数据库统计信息"""
        return get_db_stats()

    def cleanup_db_connections():
        """清理数据库连接"""
        cleanup_database_connections()

else:
    # 传统数据库配置
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()

    def get_db():
        """获取数据库会话（传统版本）"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def get_db_statistics():
        """获取数据库统计信息（简化版）"""
        return {
            "backend": "traditional",
            "pool_size": getattr(engine.pool, 'size', lambda: 0)(),
            "checked_out": getattr(engine.pool, 'checkedout', lambda: 0)()
        }

    def cleanup_db_connections():
        """清理数据库连接（传统版本）"""
        if 'engine' in globals():
            engine.dispose()
