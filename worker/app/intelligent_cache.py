"""
智能缓存系统
"""

import os
import json
import hashlib
import logging
import sqlite3
import time
import shutil
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class CacheType(Enum):
    """缓存类型"""
    AUDIO_PROCESSING = "audio_processing"
    FORMAT_CONVERSION = "format_conversion"
    QUALITY_ANALYSIS = "quality_analysis"
    BATCH_PROCESSING = "batch_processing"
    AUDITION_RENDERING = "audition_rendering"


class CacheStatus(Enum):
    """缓存状态"""
    VALID = "valid"
    EXPIRED = "expired"
    CORRUPTED = "corrupted"
    MISSING = "missing"


@dataclass
class CacheEntry:
    """缓存条目"""
    cache_key: str
    cache_type: CacheType
    input_hash: str
    params_hash: str
    file_path: str
    metadata: Dict[str, Any]
    created_at: float
    last_accessed: float
    access_count: int
    file_size: int
    ttl: Optional[float] = None  # 生存时间（秒）
    
    @property
    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    @property
    def age(self) -> float:
        """获取缓存年龄（秒）"""
        return time.time() - self.created_at
    
    @property
    def last_access_age(self) -> float:
        """获取最后访问时间（秒）"""
        return time.time() - self.last_accessed


@dataclass
class CacheStats:
    """缓存统计"""
    total_entries: int = 0
    total_size: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    
    @property
    def hit_rate(self) -> float:
        """命中率"""
        total = self.hit_count + self.miss_count
        return self.hit_count / total if total > 0 else 0.0
    
    @property
    def average_size(self) -> float:
        """平均文件大小"""
        return self.total_size / self.total_entries if self.total_entries > 0 else 0.0


class IntelligentCache:
    """智能缓存系统"""
    
    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 1024, 
                 max_entries: int = 10000, default_ttl: float = 86400):
        """
        初始化智能缓存
        
        Args:
            cache_dir: 缓存目录
            max_size_mb: 最大缓存大小（MB）
            max_entries: 最大缓存条目数
            default_ttl: 默认生存时间（秒）
        """
        self.cache_dir = Path(cache_dir)
        self.max_size = max_size_mb * 1024 * 1024  # 转换为字节
        self.max_entries = max_entries
        self.default_ttl = default_ttl
        
        # 创建缓存目录
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 数据库文件
        self.db_path = self.cache_dir / "cache.db"
        
        # 线程锁
        self._lock = threading.RLock()
        
        # 统计信息
        self.stats = CacheStats()
        
        # 初始化数据库
        self._init_database()
        
        # 加载统计信息
        self._load_stats()
        
        logger.info(f"智能缓存系统初始化完成: {cache_dir}, 最大大小: {max_size_mb}MB")
    
    def _init_database(self):
        """初始化数据库"""
        with self._db_transaction() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    cache_type TEXT NOT NULL,
                    input_hash TEXT NOT NULL,
                    params_hash TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_accessed REAL NOT NULL,
                    access_count INTEGER NOT NULL DEFAULT 0,
                    file_size INTEGER NOT NULL,
                    ttl REAL
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_type ON cache_entries(cache_type)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_input_hash ON cache_entries(input_hash)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_last_accessed ON cache_entries(last_accessed)
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_stats (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                )
            """)
    
    def _load_stats(self):
        """加载统计信息"""
        try:
            with self._db_transaction() as conn:
                cursor = conn.execute("SELECT key, value FROM cache_stats")
                stats_data = dict(cursor.fetchall())

                self.stats.hit_count = stats_data.get("hit_count", 0)
                self.stats.miss_count = stats_data.get("miss_count", 0)
                self.stats.eviction_count = stats_data.get("eviction_count", 0)

                # 计算当前条目数和大小
                cursor = conn.execute("SELECT COUNT(*), COALESCE(SUM(file_size), 0) FROM cache_entries")
                count, size = cursor.fetchone()
                self.stats.total_entries = count
                self.stats.total_size = size
        except Exception as e:
            logger.warning(f"加载统计信息失败: {e}")

    def _save_stats(self):
        """保存统计信息"""
        try:
            with self._db_transaction() as conn:
                stats_data = [
                    ("hit_count", self.stats.hit_count),
                    ("miss_count", self.stats.miss_count),
                    ("eviction_count", self.stats.eviction_count)
                ]

                conn.executemany(
                    "INSERT OR REPLACE INTO cache_stats (key, value) VALUES (?, ?)",
                    stats_data
                )
        except Exception as e:
            logger.warning(f"保存统计信息失败: {e}")
    
    def _generate_cache_key(self, input_data: str, params: Dict[str, Any], 
                          cache_type: CacheType) -> str:
        """生成缓存键"""
        # 计算输入数据哈希
        input_hash = hashlib.sha256(input_data.encode()).hexdigest()
        
        # 计算参数哈希
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()
        
        # 组合缓存键
        cache_key = f"{cache_type.value}_{input_hash[:16]}_{params_hash[:16]}"
        return cache_key
    
    def _get_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        hasher = hashlib.sha256()
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"计算文件哈希失败: {file_path}, 错误: {e}")
            # 回退到文件大小和修改时间
            stat = os.stat(file_path)
            return hashlib.sha256(f"{stat.st_size}_{stat.st_mtime}".encode()).hexdigest()
    
    @contextmanager
    def _db_transaction(self):
        """数据库事务上下文管理器"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")  # 启用WAL模式提高并发性
        conn.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全性
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get(self, input_file: str, params: Dict[str, Any], 
           cache_type: CacheType) -> Optional[str]:
        """获取缓存"""
        with self._lock:
            try:
                # 检查输入文件是否存在
                if not os.path.exists(input_file):
                    return None
                
                # 计算输入文件哈希
                input_hash = self._get_file_hash(input_file)
                
                # 生成缓存键
                cache_key = self._generate_cache_key(input_file, params, cache_type)
                
                # 查询缓存条目
                with self._db_transaction() as conn:
                    cursor = conn.execute("""
                        SELECT * FROM cache_entries WHERE cache_key = ?
                    """, (cache_key,))
                    
                    row = cursor.fetchone()
                    if not row:
                        self.stats.miss_count += 1
                        self._save_stats()
                        return None
                    
                    # 构建缓存条目
                    entry = CacheEntry(
                        cache_key=row[0],
                        cache_type=CacheType(row[1]),
                        input_hash=row[2],
                        params_hash=row[3],
                        file_path=row[4],
                        metadata=json.loads(row[5]),
                        created_at=row[6],
                        last_accessed=row[7],
                        access_count=row[8],
                        file_size=row[9],
                        ttl=row[10]
                    )
                    
                    # 检查缓存状态
                    status = self._check_cache_status(entry, input_hash)
                    
                    if status != CacheStatus.VALID:
                        # 删除无效缓存
                        self._remove_entry(cache_key)
                        self.stats.miss_count += 1
                        self._save_stats()
                        return None
                    
                    # 更新访问信息
                    current_time = time.time()
                    conn.execute("""
                        UPDATE cache_entries 
                        SET last_accessed = ?, access_count = access_count + 1
                        WHERE cache_key = ?
                    """, (current_time, cache_key))
                    
                    self.stats.hit_count += 1
                    self._save_stats()
                    
                    logger.debug(f"缓存命中: {cache_key}")
                    return entry.file_path
                    
            except Exception as e:
                logger.error(f"获取缓存失败: {e}")
                self.stats.miss_count += 1
                return None
    
    def put(self, input_file: str, params: Dict[str, Any], 
           cache_type: CacheType, output_file: str, 
           metadata: Optional[Dict[str, Any]] = None,
           ttl: Optional[float] = None) -> bool:
        """存储缓存"""
        with self._lock:
            try:
                # 检查文件是否存在
                if not os.path.exists(input_file) or not os.path.exists(output_file):
                    return False
                
                # 计算哈希
                input_hash = self._get_file_hash(input_file)
                cache_key = self._generate_cache_key(input_file, params, cache_type)
                
                # 计算参数哈希
                params_str = json.dumps(params, sort_keys=True)
                params_hash = hashlib.sha256(params_str.encode()).hexdigest()
                
                # 获取文件大小
                file_size = os.path.getsize(output_file)
                
                # 创建缓存文件路径
                cache_file_dir = self.cache_dir / cache_type.value
                cache_file_dir.mkdir(exist_ok=True)
                
                cache_file_path = cache_file_dir / f"{cache_key}{Path(output_file).suffix}"
                
                # 复制文件到缓存目录
                shutil.copy2(output_file, cache_file_path)
                
                # 创建缓存条目
                current_time = time.time()
                entry = CacheEntry(
                    cache_key=cache_key,
                    cache_type=cache_type,
                    input_hash=input_hash,
                    params_hash=params_hash,
                    file_path=str(cache_file_path),
                    metadata=metadata or {},
                    created_at=current_time,
                    last_accessed=current_time,
                    access_count=0,
                    file_size=file_size,
                    ttl=ttl or self.default_ttl
                )
                
                # 存储到数据库
                with self._db_transaction() as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO cache_entries 
                        (cache_key, cache_type, input_hash, params_hash, file_path,
                         metadata, created_at, last_accessed, access_count, file_size, ttl)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.cache_key, entry.cache_type.value, entry.input_hash,
                        entry.params_hash, entry.file_path, json.dumps(entry.metadata),
                        entry.created_at, entry.last_accessed, entry.access_count,
                        entry.file_size, entry.ttl
                    ))
                
                # 更新统计
                self.stats.total_entries += 1
                self.stats.total_size += file_size
                self._save_stats()
                
                # 检查是否需要清理
                self._cleanup_if_needed()
                
                logger.debug(f"缓存存储成功: {cache_key}")
                return True
                
            except Exception as e:
                logger.error(f"存储缓存失败: {e}")
                return False
    
    def _check_cache_status(self, entry: CacheEntry, current_input_hash: str) -> CacheStatus:
        """检查缓存状态"""
        # 检查文件是否存在
        if not os.path.exists(entry.file_path):
            return CacheStatus.MISSING
        
        # 检查输入文件是否变化
        if entry.input_hash != current_input_hash:
            return CacheStatus.CORRUPTED
        
        # 检查是否过期
        if entry.is_expired:
            return CacheStatus.EXPIRED
        
        return CacheStatus.VALID
    
    def _remove_entry(self, cache_key: str):
        """删除缓存条目"""
        try:
            with self._db_transaction() as conn:
                # 获取文件路径
                cursor = conn.execute("SELECT file_path, file_size FROM cache_entries WHERE cache_key = ?", (cache_key,))
                row = cursor.fetchone()
                
                if row:
                    file_path, file_size = row
                    
                    # 删除文件
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                    # 删除数据库记录
                    conn.execute("DELETE FROM cache_entries WHERE cache_key = ?", (cache_key,))
                    
                    # 更新统计
                    self.stats.total_entries -= 1
                    self.stats.total_size -= file_size
                    
        except Exception as e:
            logger.error(f"删除缓存条目失败: {cache_key}, 错误: {e}")
    
    def _cleanup_if_needed(self):
        """根据需要清理缓存"""
        # 检查大小限制
        if self.stats.total_size > self.max_size:
            self._cleanup_by_size()
        
        # 检查条目数限制
        if self.stats.total_entries > self.max_entries:
            self._cleanup_by_count()
        
        # 清理过期条目
        self._cleanup_expired()
    
    def _cleanup_by_size(self):
        """按大小清理缓存"""
        target_size = self.max_size * 0.8  # 清理到80%
        
        with self._db_transaction() as conn:
            # 按LRU策略选择要删除的条目
            cursor = conn.execute("""
                SELECT cache_key, file_size FROM cache_entries 
                ORDER BY last_accessed ASC
            """)
            
            current_size = self.stats.total_size
            for cache_key, file_size in cursor:
                if current_size <= target_size:
                    break
                
                self._remove_entry(cache_key)
                current_size -= file_size
                self.stats.eviction_count += 1
        
        logger.info(f"按大小清理缓存完成，当前大小: {self.stats.total_size / 1024 / 1024:.1f}MB")
    
    def _cleanup_by_count(self):
        """按条目数清理缓存"""
        target_count = int(self.max_entries * 0.8)  # 清理到80%
        
        with self._db_transaction() as conn:
            # 按LRU策略选择要删除的条目
            cursor = conn.execute("""
                SELECT cache_key FROM cache_entries 
                ORDER BY last_accessed ASC
                LIMIT ?
            """, (self.stats.total_entries - target_count,))
            
            for (cache_key,) in cursor:
                self._remove_entry(cache_key)
                self.stats.eviction_count += 1
        
        logger.info(f"按条目数清理缓存完成，当前条目数: {self.stats.total_entries}")
    
    def _cleanup_expired(self):
        """清理过期条目"""
        current_time = time.time()
        
        with self._db_transaction() as conn:
            cursor = conn.execute("""
                SELECT cache_key FROM cache_entries 
                WHERE ttl IS NOT NULL AND (created_at + ttl) < ?
            """, (current_time,))
            
            expired_count = 0
            for (cache_key,) in cursor:
                self._remove_entry(cache_key)
                expired_count += 1
        
        if expired_count > 0:
            logger.info(f"清理过期缓存完成，删除 {expired_count} 个条目")


    def clear_cache(self, cache_type: Optional[CacheType] = None) -> int:
        """清理缓存"""
        with self._lock:
            try:
                with self._db_transaction() as conn:
                    if cache_type:
                        # 清理特定类型的缓存
                        cursor = conn.execute("""
                            SELECT cache_key FROM cache_entries WHERE cache_type = ?
                        """, (cache_type.value,))
                    else:
                        # 清理所有缓存
                        cursor = conn.execute("SELECT cache_key FROM cache_entries")

                    deleted_count = 0
                    for (cache_key,) in cursor:
                        self._remove_entry(cache_key)
                        deleted_count += 1

                    self._save_stats()

                logger.info(f"缓存清理完成，删除 {deleted_count} 个条目")
                return deleted_count

            except Exception as e:
                logger.error(f"清理缓存失败: {e}")
                return 0

    def get_stats(self) -> CacheStats:
        """获取缓存统计信息"""
        return self.stats

    def get_cache_info(self, cache_type: Optional[CacheType] = None) -> List[Dict[str, Any]]:
        """获取缓存信息"""
        try:
            with self._db_transaction() as conn:
                if cache_type:
                    cursor = conn.execute("""
                        SELECT cache_key, cache_type, created_at, last_accessed,
                               access_count, file_size, ttl FROM cache_entries
                        WHERE cache_type = ?
                        ORDER BY last_accessed DESC
                    """, (cache_type.value,))
                else:
                    cursor = conn.execute("""
                        SELECT cache_key, cache_type, created_at, last_accessed,
                               access_count, file_size, ttl FROM cache_entries
                        ORDER BY last_accessed DESC
                    """)

                entries = []
                for row in cursor:
                    entry_info = {
                        "cache_key": row[0],
                        "cache_type": row[1],
                        "created_at": row[2],
                        "last_accessed": row[3],
                        "access_count": row[4],
                        "file_size": row[5],
                        "ttl": row[6],
                        "age": time.time() - row[2],
                        "last_access_age": time.time() - row[3]
                    }
                    entries.append(entry_info)

                return entries

        except Exception as e:
            logger.error(f"获取缓存信息失败: {e}")
            return []


class CacheManager:
    """缓存管理器 - 用于集成到音频处理流程"""

    def __init__(self, cache: IntelligentCache):
        self.cache = cache
        logger.info("缓存管理器初始化完成")

    def get_or_process_audio(self, input_file: str, params: Dict[str, Any],
                           processor_func, cache_type: CacheType,
                           output_extension: str = ".wav",
                           ttl: Optional[float] = None) -> Tuple[str, bool]:
        """
        获取缓存或处理音频

        Returns:
            Tuple[str, bool]: (输出文件路径, 是否来自缓存)
        """
        # 尝试从缓存获取
        cached_file = self.cache.get(input_file, params, cache_type)
        if cached_file and os.path.exists(cached_file):
            logger.info(f"使用缓存文件: {cached_file}")
            return cached_file, True

        # 缓存未命中，执行处理
        logger.info(f"缓存未命中，开始处理: {input_file}")

        # 生成临时输出文件名
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=output_extension, delete=False) as tmp_file:
            temp_output = tmp_file.name

        try:
            # 执行处理函数
            result = processor_func(input_file, temp_output, params)

            # 检查处理是否成功
            if result and os.path.exists(temp_output):
                # 存储到缓存
                metadata = {
                    "processor": processor_func.__name__ if hasattr(processor_func, '__name__') else str(processor_func),
                    "input_file": input_file,
                    "processing_time": time.time()
                }

                success = self.cache.put(
                    input_file, params, cache_type, temp_output,
                    metadata, ttl
                )

                if success:
                    # 获取缓存文件路径
                    cached_file = self.cache.get(input_file, params, cache_type)
                    if cached_file:
                        # 删除临时文件
                        os.remove(temp_output)
                        return cached_file, False

                # 缓存失败，返回临时文件
                return temp_output, False
            else:
                # 处理失败
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                raise RuntimeError("音频处理失败")

        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_output):
                os.remove(temp_output)
            raise e

    def invalidate_cache(self, input_file: str, params: Dict[str, Any],
                        cache_type: CacheType):
        """使特定缓存失效"""
        cache_key = self.cache._generate_cache_key(input_file, params, cache_type)
        self.cache._remove_entry(cache_key)
        logger.info(f"缓存已失效: {cache_key}")

    def warm_cache(self, input_files: List[str], params_list: List[Dict[str, Any]],
                  processor_func, cache_type: CacheType,
                  output_extension: str = ".wav"):
        """预热缓存"""
        logger.info(f"开始预热缓存，文件数: {len(input_files)}")

        for i, (input_file, params) in enumerate(zip(input_files, params_list)):
            try:
                logger.info(f"预热进度: {i+1}/{len(input_files)} - {input_file}")
                self.get_or_process_audio(
                    input_file, params, processor_func, cache_type, output_extension
                )
            except Exception as e:
                logger.error(f"预热缓存失败: {input_file}, 错误: {e}")

        logger.info("缓存预热完成")


# 全局缓存实例
global_cache = IntelligentCache()
global_cache_manager = CacheManager(global_cache)
