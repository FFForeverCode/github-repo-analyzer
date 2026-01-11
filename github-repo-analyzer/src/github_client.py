"""
GitHub API客户端模块

封装PyGithub，提供统一的API访问接口
"""

import time
from typing import Optional, List, Iterator, Any
from datetime import datetime, timedelta
from functools import wraps

from github import Github, GithubException
from github.Repository import Repository
from github.Commit import Commit
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.NamedUser import NamedUser
from github.PaginatedList import PaginatedList
from rich.console import Console

from .config import get_config

console = Console()


def rate_limit_handler(func):
    """速率限制处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except GithubException as e:
                if e.status == 403 and 'rate limit' in str(e).lower():
                    wait_time = 60 * (attempt + 1)
                    console.print(f"[yellow]触发API速率限制，等待 {wait_time} 秒后重试...[/yellow]")
                    time.sleep(wait_time)
                else:
                    raise
        raise Exception("达到最大重试次数，请稍后再试")
    return wrapper


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
            raise ValueError("GitHub Token未配置，请设置GITHUB_TOKEN环境变量")
        
        self.github = Github(self.token)
        self._repo_cache = {}
    
    def get_rate_limit(self) -> dict:
        """获取API速率限制信息"""
        rate_limit = self.github.get_rate_limit()
        return {
            'core': {
                'limit': rate_limit.core.limit,
                'remaining': rate_limit.core.remaining,
                'reset_time': rate_limit.core.reset.strftime('%Y-%m-%d %H:%M:%S')
            },
            'search': {
                'limit': rate_limit.search.limit,
                'remaining': rate_limit.search.remaining,
                'reset_time': rate_limit.search.reset.strftime('%Y-%m-%d %H:%M:%S')
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
        repo = self.get_repository(repo_name)
        return {
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
            'url': repo.html_url
        }
    
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
        repo = self.get_repository(repo_name)
        branches = repo.get_branches()
        
        return [
            {
                'name': branch.name,
                'protected': branch.protected,
                'commit_sha': branch.commit.sha
            }
            for branch in branches
        ]
    
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
                'author': release.author.login if release.author else None
            })
            count += 1
        
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
        repos = self.github.search_repositories(query=query, sort=sort)
        
        result = []
        for i, repo in enumerate(repos):
            if i >= max_count:
                break
            result.append({
                'full_name': repo.full_name,
                'description': repo.description,
                'stars': repo.stargazers_count,
                'language': repo.language,
                'url': repo.html_url
            })
        
        return result
