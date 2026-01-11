"""
缓存管理模块

提供多种缓存策略，减少API调用次数，提升分析效率
"""

import os
import json
import hashlib
import pickle
import time
from typing import Any, Optional, Dict, Callable
from datetime import datetime, timedelta
from functools import wraps
from abc import ABC, abstractmethod
from pathlib import Path
import threading

from rich.console import Console

console = Console()


class CacheStrategy(ABC):
    """缓存策略基类"""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存"""
        pass
    
    @abstractmethod
    def clear(self) -> bool:
        """清空缓存"""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        pass


class MemoryCache(CacheStrategy):
    """内存缓存策略"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._cache = {}
                    cls._instance._expiry = {}
        return cls._instance
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if key not in self._cache:
            return None
        
        # 检查是否过期
        if key in self._expiry:
            if datetime.now() > self._expiry[key]:
                self.delete(key)
                return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存，ttl为秒数"""
        try:
            self._cache[key] = value
            if ttl:
                self._expiry[key] = datetime.now() + timedelta(seconds=ttl)
            return True
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if key in self._cache:
            del self._cache[key]
        if key in self._expiry:
            del self._expiry[key]
        return True
    
    def clear(self) -> bool:
        """清空缓存"""
        self._cache.clear()
        self._expiry.clear()
        return True
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if key not in self._cache:
            return False
        if key in self._expiry and datetime.now() > self._expiry[key]:
            self.delete(key)
            return False
        return True
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        return {
            'total_keys': len(self._cache),
            'memory_size': sum(len(pickle.dumps(v)) for v in self._cache.values()),
            'expired_keys': sum(1 for k in self._expiry if datetime.now() > self._expiry[k])
        }


class FileCache(CacheStrategy):
    """文件缓存策略"""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.meta_file = self.cache_dir / "cache_meta.json"
        self._load_meta()
    
    def _load_meta(self):
        """加载元数据"""
        if self.meta_file.exists():
            try:
                with open(self.meta_file, 'r') as f:
                    self._meta = json.load(f)
            except:
                self._meta = {}
        else:
            self._meta = {}
    
    def _save_meta(self):
        """保存元数据"""
        with open(self.meta_file, 'w') as f:
            json.dump(self._meta, f)
    
    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        # 检查是否过期
        if key in self._meta:
            expiry = self._meta[key].get('expiry')
            if expiry and datetime.fromisoformat(expiry) < datetime.now():
                self.delete(key)
                return None
        
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        cache_path = self._get_cache_path(key)
        
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
            
            self._meta[key] = {
                'created': datetime.now().isoformat(),
                'expiry': (datetime.now() + timedelta(seconds=ttl)).isoformat() if ttl else None,
                'size': cache_path.stat().st_size
            }
            self._save_meta()
            return True
        except Exception as e:
            console.print(f"[red]缓存写入失败: {e}[/red]")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        cache_path = self._get_cache_path(key)
        
        if cache_path.exists():
            cache_path.unlink()
        
        if key in self._meta:
            del self._meta[key]
            self._save_meta()
        
        return True
    
    def clear(self) -> bool:
        """清空缓存"""
        import shutil
        try:
            for f in self.cache_dir.glob("*.cache"):
                f.unlink()
            self._meta.clear()
            self._save_meta()
            return True
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return self.get(key) is not None
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.cache"))
        return {
            'total_keys': len(self._meta),
            'total_size_bytes': total_size,
            'total_size_mb': total_size / (1024 * 1024),
            'cache_dir': str(self.cache_dir)
        }
    
    def cleanup_expired(self) -> int:
        """清理过期缓存"""
        expired_count = 0
        for key, meta in list(self._meta.items()):
            expiry = meta.get('expiry')
            if expiry and datetime.fromisoformat(expiry) < datetime.now():
                self.delete(key)
                expired_count += 1
        return expired_count


class RedisCache(CacheStrategy):
    """Redis缓存策略（可选）"""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 db: int = 0, prefix: str = 'github_analyzer:'):
        self.prefix = prefix
        try:
            import redis
            self.redis = redis.Redis(host=host, port=port, db=db)
            self.redis.ping()
            self.available = True
        except Exception as e:
            console.print(f"[yellow]Redis不可用，将使用内存缓存: {e}[/yellow]")
            self.available = False
            self._fallback = MemoryCache()
    
    def _key(self, key: str) -> str:
        return f"{self.prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        if not self.available:
            return self._fallback.get(key)
        
        try:
            data = self.redis.get(self._key(key))
            if data:
                return pickle.loads(data)
            return None
        except Exception:
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if not self.available:
            return self._fallback.set(key, value, ttl)
        
        try:
            data = pickle.dumps(value)
            if ttl:
                self.redis.setex(self._key(key), ttl, data)
            else:
                self.redis.set(self._key(key), data)
            return True
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        if not self.available:
            return self._fallback.delete(key)
        
        try:
            self.redis.delete(self._key(key))
            return True
        except Exception:
            return False
    
    def clear(self) -> bool:
        if not self.available:
            return self._fallback.clear()
        
        try:
            keys = self.redis.keys(f"{self.prefix}*")
            if keys:
                self.redis.delete(*keys)
            return True
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        if not self.available:
            return self._fallback.exists(key)
        
        try:
            return self.redis.exists(self._key(key)) > 0
        except Exception:
            return False


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, strategy: str = 'memory', **kwargs):
        """
        初始化缓存管理器
        
        Args:
            strategy: 缓存策略 ('memory', 'file', 'redis')
            **kwargs: 策略特定参数
        """
        self.strategy_name = strategy
        
        if strategy == 'memory':
            self.cache = MemoryCache()
        elif strategy == 'file':
            cache_dir = kwargs.get('cache_dir', '.cache')
            self.cache = FileCache(cache_dir)
        elif strategy == 'redis':
            self.cache = RedisCache(**kwargs)
        else:
            raise ValueError(f"不支持的缓存策略: {strategy}")
        
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        value = self.cache.get(key)
        if value is not None:
            self._hits += 1
        else:
            self._misses += 1
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        return self.cache.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        return self.cache.delete(key)
    
    def clear(self) -> bool:
        """清空缓存"""
        self._hits = 0
        self._misses = 0
        return self.cache.clear()
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        return self.cache.exists(key)
    
    def get_or_set(self, key: str, factory: Callable, ttl: Optional[int] = None) -> Any:
        """获取缓存，不存在则创建"""
        value = self.get(key)
        if value is None:
            value = factory()
            self.set(key, value, ttl)
        return value
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        stats = {
            'strategy': self.strategy_name,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': f"{hit_rate:.2f}%"
        }
        
        if hasattr(self.cache, 'get_stats'):
            stats.update(self.cache.get_stats())
        
        return stats


def cached(cache_manager: CacheManager = None, ttl: int = 3600, 
           key_prefix: str = ''):
    """
    缓存装饰器
    
    Args:
        cache_manager: 缓存管理器实例
        ttl: 缓存过期时间（秒）
        key_prefix: 缓存键前缀
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key_parts = [key_prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ':'.join(key_parts)
            
            # 获取或使用缓存管理器
            cm = cache_manager or getattr(wrapper, '_cache_manager', None)
            if cm is None:
                cm = MemoryCache()
            
            # 尝试从缓存获取
            cached_value = cm.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cm.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator


class CachedGitHubClient:
    """带缓存的GitHub客户端包装器"""
    
    def __init__(self, client, cache_manager: CacheManager = None,
                 default_ttl: int = 3600):
        """
        初始化带缓存的客户端
        
        Args:
            client: GitHubClient实例
            cache_manager: 缓存管理器
            default_ttl: 默认缓存过期时间（秒）
        """
        self.client = client
        self.cache = cache_manager or CacheManager(strategy='file')
        self.default_ttl = default_ttl
    
    def _make_key(self, method: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [method]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return hashlib.md5(':'.join(key_parts).encode()).hexdigest()
    
    def get_repo_info(self, repo_name: str, ttl: int = None) -> dict:
        """获取仓库信息（带缓存）"""
        cache_key = self._make_key('repo_info', repo_name)
        
        cached = self.cache.get(cache_key)
        if cached:
            console.print(f"[dim]从缓存获取仓库信息: {repo_name}[/dim]")
            return cached
        
        result = self.client.get_repo_info(repo_name)
        # 转换datetime对象为字符串以便缓存
        result = self._serialize_result(result)
        self.cache.set(cache_key, result, ttl or self.default_ttl)
        return result
    
    def get_commits_cached(self, repo_name: str, since=None, until=None,
                           max_count: int = None, ttl: int = None) -> list:
        """获取提交记录（带缓存）"""
        cache_key = self._make_key('commits', repo_name, 
                                   since=str(since), until=str(until),
                                   max_count=max_count)
        
        cached = self.cache.get(cache_key)
        if cached:
            console.print(f"[dim]从缓存获取commit记录: {repo_name}[/dim]")
            return cached
        
        commits = []
        for commit in self.client.get_commits(repo_name, since, until, max_count):
            commits.append({
                'sha': commit.sha,
                'message': commit.commit.message,
                'author': commit.commit.author.name if commit.commit.author else None,
                'author_email': commit.commit.author.email if commit.commit.author else None,
                'date': commit.commit.author.date.isoformat() if commit.commit.author else None,
                'additions': commit.stats.additions if commit.stats else 0,
                'deletions': commit.stats.deletions if commit.stats else 0
            })
        
        self.cache.set(cache_key, commits, ttl or self.default_ttl)
        return commits
    
    def get_contributors_cached(self, repo_name: str, 
                                max_count: int = None, ttl: int = None) -> list:
        """获取贡献者（带缓存）"""
        cache_key = self._make_key('contributors', repo_name, max_count=max_count)
        
        cached = self.cache.get(cache_key)
        if cached:
            console.print(f"[dim]从缓存获取贡献者: {repo_name}[/dim]")
            return cached
        
        contributors = []
        for contrib in self.client.get_contributors(repo_name, max_count):
            contributors.append({
                'login': contrib.login,
                'name': contrib.name,
                'contributions': contrib.contributions,
                'avatar_url': contrib.avatar_url
            })
        
        self.cache.set(cache_key, contributors, ttl or self.default_ttl)
        return contributors
    
    def _serialize_result(self, result: Any) -> Any:
        """序列化结果，处理datetime等不可序列化的对象"""
        if isinstance(result, dict):
            return {k: self._serialize_result(v) for k, v in result.items()}
        elif isinstance(result, list):
            return [self._serialize_result(item) for item in result]
        elif isinstance(result, datetime):
            return result.isoformat()
        else:
            return result
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计"""
        return self.cache.get_stats()
    
    def clear_cache(self) -> bool:
        """清空缓存"""
        return self.cache.clear()


# 全局缓存管理器
_global_cache = None

def get_cache_manager(strategy: str = 'file', **kwargs) -> CacheManager:
    """获取全局缓存管理器"""
    global _global_cache
    if _global_cache is None:
        _global_cache = CacheManager(strategy, **kwargs)
    return _global_cache
