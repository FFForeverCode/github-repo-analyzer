"""
GitHub API客户端模块

封装PyGithub，提供统一的API访问接口
"""

import time
import json
import hashlib
from typing import Optional, List, Iterator, Any
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from github import Github, GithubException
from github.Repository import Repository
from github.Commit import Commit
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.NamedUser import NamedUser
from rich.console import Console

from .config import get_config

console = Console()


def rate_limit_handler(func):
    """速率限制处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        base_wait_time = 60
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except GithubException as e:
                if e.status == 403 and 'rate limit' in str(e).lower():
                    # 计算等待时间（指数退避）
                    wait_time = base_wait_time * (2 ** attempt)
                    console.print(f"[yellow]⚠️ 触发API速率限制，等待 {wait_time} 秒后重试 ({attempt + 1}/{max_retries})...[/yellow]")
                    time.sleep(wait_time)
                elif e.status == 404:
                    console.print(f"[red]❌ 资源未找到: {e.data.get('message', str(e))}[/red]")
                    raise
                elif e.status == 429:
                    console.print(f"[yellow]⚠️ 请求过多，等待30秒后重试...[/yellow]")
                    time.sleep(30)
                elif e.status >= 500:
                    console.print(f"[yellow]⚠️ GitHub服务器错误，等待10秒后重试...[/yellow]")
                    time.sleep(10)
                else:
                    console.print(f"[red]❌ GitHub API错误: {e.status} - {e.data.get('message', str(e))}[/red]")
                    raise
            except Exception as e:
                if attempt == max_retries - 1:
                    console.print(f"[red]❌ 达到最大重试次数: {e}[/red]")
                    raise
                console.print(f"[yellow]⚠️ 发生错误，等待5秒后重试: {e}[/yellow]")
                time.sleep(5)
        
        raise Exception("达到最大重试次数，请稍后再试")
    return wrapper


class CacheManager:
    """缓存管理器"""
    
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self._init_cache_cleanup()
    
    def _init_cache_cleanup(self):
        """初始化缓存清理机制"""
        # 创建缓存统计文件
        self.stats_file = self.cache_dir / "cache_stats.json"
        if not self.stats_file.exists():
            self._save_stats({
                'total_requests': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'total_size_kb': 0,
                'last_cleanup': datetime.now().isoformat()
            })
    
    def _get_cache_key(self, func_name: str, *args, **kwargs) -> str:
        """生成缓存键"""
        # 简化参数，避免过长的缓存键
        args_str = str(args)[:100]  # 限制长度
        kwargs_str = str(sorted(kwargs.items()))[:100]
        key_data = f"{func_name}:{args_str}:{kwargs_str}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str, ttl: int = 3600) -> Optional[Any]:
        """获取缓存"""
        cache_file = self.cache_dir / f"{key}.json"
        
        # 更新统计
        stats = self._load_stats()
        stats['total_requests'] = stats.get('total_requests', 0) + 1
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查是否过期
                if datetime.now().timestamp() - data['timestamp'] < ttl:
                    stats['cache_hits'] = stats.get('cache_hits', 0) + 1
                    self._save_stats(stats)
                    return data['value']
                else:
                    # 删除过期缓存
                    cache_file.unlink(missing_ok=True)
                    stats['cache_misses'] = stats.get('cache_misses', 0) + 1
                    self._save_stats(stats)
            except:
                stats['cache_misses'] = stats.get('cache_misses', 0) + 1
                self._save_stats(stats)
                return None
        else:
            stats['cache_misses'] = stats.get('cache_misses', 0) + 1
            self._save_stats(stats)
        
        return None
    
    def set(self, key: str, value: Any, compress: bool = True):
        """设置缓存"""
        cache_file = self.cache_dir / f"{key}.json"
        
        try:
            # 序列化数据
            cache_data = {
                'timestamp': datetime.now().timestamp(),
                'value': value
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, default=str, separators=(',', ':'))
            
            # 更新缓存大小统计
            self._update_size_stats()
            
            # 检查是否需要清理
            self._check_and_cleanup()
            
        except Exception as e:
            console.print(f"[yellow]⚠️ 缓存写入失败: {e}[/yellow]")
    
    def _update_size_stats(self):
        """更新缓存大小统计"""
        total_size = 0
        for cache_file in self.cache_dir.glob("*.json"):
            total_size += cache_file.stat().st_size
        
        stats = self._load_stats()
        stats['total_size_kb'] = total_size / 1024
        self._save_stats(stats)
    
    def _check_and_cleanup(self, max_size_mb: int = 100):
        """检查并清理缓存"""
        stats = self._load_stats()
        current_size_mb = stats.get('total_size_kb', 0) / 1024
        
        if current_size_mb > max_size_mb:
            console.print(f"[yellow]⚠️ 缓存大小超过 {max_size_mb}MB，正在清理...[/yellow]")
            self.cleanup_oldest(max_size_mb // 2)
    
    def cleanup_oldest(self, target_size_mb: int = 50):
        """清理最旧的缓存文件"""
        cache_files = []
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cache_files.append({
                    'file': cache_file,
                    'timestamp': data['timestamp'],
                    'size': cache_file.stat().st_size
                })
            except:
                continue
        
        # 按时间排序（从旧到新）
        cache_files.sort(key=lambda x: x['timestamp'])
        
        current_size_mb = sum(f['size'] for f in cache_files) / (1024 * 1024)
        deleted_size = 0
        
        for cache_info in cache_files:
            if current_size_mb - deleted_size/(1024*1024) <= target_size_mb:
                break
            
            try:
                cache_info['file'].unlink()
                deleted_size += cache_info['size']
            except:
                continue
        
        if deleted_size > 0:
            console.print(f"[green]✓ 清理缓存: 删除 {deleted_size/1024:.1f}KB[/green]")
            self._update_size_stats()
            
            stats = self._load_stats()
            stats['last_cleanup'] = datetime.now().isoformat()
            self._save_stats(stats)
    
    def clear(self):
        """清空所有缓存"""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except:
                continue
        
        stats = self._load_stats()
        stats.update({
            'total_size_kb': 0,
            'last_cleanup': datetime.now().isoformat()
        })
        self._save_stats(stats)
        
        console.print("[green]✓ 缓存已清空[/green]")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = self._load_stats()
        
        # 计算命中率
        total_requests = stats.get('total_requests', 0)
        cache_hits = stats.get('cache_hits', 0)
        hit_rate = (cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        stats['hit_rate'] = f"{hit_rate:.1f}%"
        stats['cache_files_count'] = len(list(self.cache_dir.glob("*.json")))
        
        return stats
    
    def _load_stats(self) -> Dict[str, Any]:
        """加载统计信息"""
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_stats(self, stats: Dict[str, Any]):
        """保存统计信息"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, default=str, indent=2)
        except:
            pass


class GitHubClient:
    """GitHub API客户端"""
    
    def __init__(self, token: Optional[str] = None):
        """
        初始化GitHub客户端
        
        Args:
            token: GitHub Personal Access Token，如果不提供则从配置读取
        """
        config = get_config()
        self.token = token or config.get_github_config().token
        
        if not self.token:
            raise ValueError("GitHub Token未配置，请设置GITHUB_TOKEN环境变量或使用--token参数")
        
        self.github = Github(self.token, timeout=30)
        self._repo_cache = {}
        self.cache = CacheManager()
    
    def get_rate_limit(self) -> dict:
        """获取API速率限制信息"""
        rate_limit = self.github.get_rate_limit()
        
        # 计算重置时间倒计时
        reset_time = rate_limit.core.reset
        time_until_reset = max(0, (reset_time - datetime.now()).total_seconds())
        
        return {
            'core': {
                'limit': rate_limit.core.limit,
                'remaining': rate_limit.core.remaining,
                'reset_time': reset_time.strftime('%Y-%m-%d %H:%M:%S'),
                'reset_in_seconds': int(time_until_reset)
            },
            'search': {
                'limit': rate_limit.search.limit,
                'remaining': rate_limit.search.remaining,
                'reset_time': rate_limit.search.reset.strftime('%Y-%m-%d %H:%M:%S'),
                'reset_in_seconds': int(time_until_reset)
            }
        }
    
    @rate_limit_handler
    def get_repository(self, repo_name: str) -> Repository:
        """
        获取仓库对象
        
        Args:
            repo_name: 仓库全名，格式为 "owner/repo"
            
        Returns:
            Repository对象
        """
        if repo_name not in self._repo_cache:
            console.print(f"[dim]获取仓库信息: {repo_name}[/dim]")
            self._repo_cache[repo_name] = self.github.get_repo(repo_name)
        return self._repo_cache[repo_name]
    
    @rate_limit_handler
    def get_repo_info(self, repo_name: str) -> dict:
        """
        获取仓库基本信息
        
        Args:
            repo_name: 仓库全名
            
        Returns:
            仓库信息字典
        """
        cache_key = self.cache._get_cache_key('get_repo_info', repo_name)
        cached = self.cache.get(cache_key, ttl=3600)  # 缓存1小时
        
        if cached:
            return cached
        
        repo = self.get_repository(repo_name)
        
        # 获取更详细的信息
        try:
            # 获取README内容长度
            readme_length = 0
            try:
                readme = repo.get_readme()
                readme_length = len(readme.decoded_content)
            except:
                pass
            
            info = {
                'name': repo.name,
                'full_name': repo.full_name,
                'description': repo.description,
                'language': repo.language,
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'watchers': repo.watchers_count,
                'open_issues': repo.open_issues_count,
                'created_at': repo.created_at,
                'updated_at': repo.updated_at,
                'pushed_at': repo.pushed_at,
                'size': repo.size,
                'default_branch': repo.default_branch,
                'license': repo.license.name if repo.license else None,
                'topics': repo.get_topics(),
                'url': repo.html_url,
                'has_wiki': repo.has_wiki,
                'has_projects': repo.has_projects,
                'has_downloads': repo.has_downloads,
                'readme_size': readme_length,
                'is_fork': repo.fork,
                'parent': repo.parent.full_name if repo.parent else None
            }
        except Exception as e:
            console.print(f"[yellow]⚠️ 获取仓库详细信息时出错: {e}[/yellow]")
            info = {
                'name': repo.name,
                'full_name': repo.full_name,
                'description': repo.description,
                'language': repo.language,
                'stars': repo.stargazers_count,
                'forks': repo.forks_count,
                'watchers': repo.watchers_count,
                'open_issues': repo.open_issues_count,
                'url': repo.html_url
            }
        
        self.cache.set(cache_key, info)
        return info
    
    @rate_limit_handler
    def get_commits(self, repo_name: str, since: Optional[datetime] = None,
                    until: Optional[datetime] = None, 
                    max_count: Optional[int] = None) -> Iterator[Commit]:
        """
        获取仓库提交记录
        
        Args:
            repo_name: 仓库全名
            since: 起始时间
            until: 结束时间
            max_count: 最大获取数量
            
        Yields:
            Commit对象
        """
        repo = self.get_repository(repo_name)
        
        kwargs = {}
        if since:
            kwargs['since'] = since
        if until:
            kwargs['until'] = until
        
        commits = repo.get_commits(**kwargs)
        
        count = 0
        with console.status(f"[cyan]正在获取 {repo_name} 的commits...[/cyan]"):
            for commit in commits:
                if max_count and count >= max_count:
                    break
                yield commit
                count += 1
    
    @rate_limit_handler
    def get_contributors(self, repo_name: str, 
                         max_count: Optional[int] = None) -> Iterator[tuple]:
        """
        获取仓库贡献者
        
        Args:
            repo_name: 仓库全名
            max_count: 最大获取数量
            
        Yields:
            (NamedUser, contributions) 元组
        """
        repo = self.get_repository(repo_name)
        contributors = repo.get_contributors()
        
        count = 0
        with console.status(f"[cyan]正在获取 {repo_name} 的贡献者...[/cyan]"):
            for contributor in contributors:
                if max_count and count >= max_count:
                    break
                yield contributor
                count += 1
    
    @rate_limit_handler
    def get_issues(self, repo_name: str, state: str = 'all',
                   since: Optional[datetime] = None,
                   max_count: Optional[int] = None) -> Iterator[Issue]:
        """
        获取仓库Issue
        
        Args:
            repo_name: 仓库全名
            state: Issue状态 ('open', 'closed', 'all')
            since: 起始时间
            max_count: 最大获取数量
            
        Yields:
            Issue对象
        """
        repo = self.get_repository(repo_name)
        
        kwargs = {'state': state}
        if since:
            kwargs['since'] = since
        
        issues = repo.get_issues(**kwargs)
        
        count = 0
        with console.status(f"[cyan]正在获取 {repo_name} 的Issues...[/cyan]"):
            for issue in issues:
                # 排除Pull Request（GitHub API中PR也是Issue）
                if issue.pull_request is None:
                    if max_count and count >= max_count:
                        break
                    yield issue
                    count += 1
    
    @rate_limit_handler
    def get_pull_requests(self, repo_name: str, state: str = 'all',
                          max_count: Optional[int] = None) -> Iterator[PullRequest]:
        """
        获取仓库Pull Request
        
        Args:
            repo_name: 仓库全名
            state: PR状态 ('open', 'closed', 'all')
            max_count: 最大获取数量
            
        Yields:
            PullRequest对象
        """
        repo = self.get_repository(repo_name)
        pulls = repo.get_pulls(state=state, sort='created', direction='desc')
        
        count = 0
        with console.status(f"[cyan]正在获取 {repo_name} 的Pull Requests...[/cyan]"):
            for pr in pulls:
                if max_count and count >= max_count:
                    break
                yield pr
                count += 1
    
    @rate_limit_handler
    def get_branches(self, repo_name: str) -> List[dict]:
        """
        获取仓库分支
        
        Args:
            repo_name: 仓库全名
            
        Returns:
            分支信息列表
        """
        cache_key = self.cache._get_cache_key('get_branches', repo_name)
        cached = self.cache.get(cache_key, ttl=1800)  # 缓存30分钟
        
        if cached:
            return cached
        
        repo = self.get_repository(repo_name)
        branches = repo.get_branches()
        
        result = []
        for branch in branches:
            try:
                result.append({
                    'name': branch.name,
                    'protected': branch.protected,
                    'commit_sha': branch.commit.sha[:7],
                    'commit_url': branch.commit.html_url
                })
            except:
                pass
        
        self.cache.set(cache_key, result)
        return result
    
    @rate_limit_handler
    def get_releases(self, repo_name: str, 
                     max_count: Optional[int] = None) -> List[dict]:
        """
        获取仓库发布版本
        
        Args:
            repo_name: 仓库全名
            max_count: 最大获取数量
            
        Returns:
            发布版本信息列表
        """
        cache_key = self.cache._get_cache_key('get_releases', repo_name, max_count)
        cached = self.cache.get(cache_key, ttl=3600)
        
        if cached:
            return cached
        
        repo = self.get_repository(repo_name)
        releases = repo.get_releases()
        
        result = []
        count = 0
        for release in releases:
            if max_count and count >= max_count:
                break
            result.append({
                'tag_name': release.tag_name,
                'name': release.title,
                'created_at': release.created_at,
                'published_at': release.published_at,
                'draft': release.draft,
                'prerelease': release.prerelease,
                'author': release.author.login if release.author else None,
                'download_count': release.get_download_count(),
                'assets_count': len(list(release.get_assets()))
            })
            count += 1
        
        self.cache.set(cache_key, result)
        return result
    
    def search_repositories(self, query: str, 
                           sort: str = 'stars',
                           max_count: int = 10) -> List[dict]:
        """
        搜索仓库
        
        Args:
            query: 搜索关键词
            sort: 排序方式 ('stars', 'forks', 'updated')
            max_count: 最大返回数量
            
        Returns:
            仓库信息列表
        """
        cache_key = self.cache._get_cache_key('search_repositories', query, sort, max_count)
        cached = self.cache.get(cache_key, ttl=300)  # 搜索缓存5分钟
        
        if cached:
            return cached
        
        try:
            repos = self.github.search_repositories(query=query, sort=sort)
            
            result = []
            for i, repo in enumerate(repos):
                if i >= max_count:
                    break
                result.append({
                    'full_name': repo.full_name,
                    'description': repo.description,
                    'stars': repo.stargazers_count,
                    'forks': repo.forks_count,
                    'watchers': repo.watchers_count,
                    'language': repo.language,
                    'updated_at': repo.updated_at,
                    'url': repo.html_url,
                    'score': repo.score
                })
            
            self.cache.set(cache_key, result)
            return result
            
        except GithubException as e:
            console.print(f"[red]搜索失败: {e.data.get('message', str(e))}[/red]")
            return []
    
    def get_commit_activity(self, repo_name: str, weeks: int = 52) -> List[int]:
        """
        获取每周commit活动统计
        
        Args:
            repo_name: 仓库全名
            weeks: 统计周数
            
        Returns:
            每周commit数量列表
        """
        cache_key = self.cache._get_cache_key('get_commit_activity', repo_name, weeks)
        cached = self.cache.get(cache_key, ttl=3600)
        
        if cached:
            return cached
        
        repo = self.get_repository(repo_name)
        stats = repo.get_stats_commit_activity()
        
        if stats:
            result = [week.total for week in stats][-weeks:]
        else:
            result = [0] * weeks
        
        self.cache.set(cache_key, result)
        return result
    
    def get_code_frequency(self, repo_name: str) -> List[tuple]:
        """
        获取代码频率统计
        
        Args:
            repo_name: 仓库全名
            
        Returns:
            每周代码变更统计列表
        """
        repo = self.get_repository(repo_name)
        stats = repo.get_stats_code_frequency()
        
        if stats:
            return [(week.week, week.additions, week.deletions) for week in stats]
        return []
    