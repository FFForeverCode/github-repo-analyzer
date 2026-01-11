"""
数据分析模块

提供Commit模式、贡献者活跃度等分析功能
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics

import pandas as pd
import numpy as np
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .github_client import GitHubClient
from .config import get_config

console = Console()


class CommitAnalyzer:
    """Commit分析器"""
    
    def __init__(self, client: GitHubClient):
        self.client = client
        self.config = get_config().get_analysis_config()
    
    def analyze_commit_patterns(self, repo_name: str, 
                                 days: int = 365,
                                 max_commits: int = 1000) -> Dict[str, Any]:
        """
        分析commit模式
        
        Args:
            repo_name: 仓库名
            days: 分析天数
            max_commits: 最大commit数
            
        Returns:
            分析结果字典
        """
        console.print(f"[cyan]正在分析 {repo_name} 的commit模式...[/cyan]")
        
        since = datetime.now() - timedelta(days=days)
        commits_data = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            task = progress.add_task("获取commits...", total=max_commits)
            
            for commit in self.client.get_commits(repo_name, since=since, max_count=max_commits):
                try:
                    commit_date = commit.commit.author.date
                    author = commit.commit.author.name
                    message = commit.commit.message
                    
                    # 获取文件变更统计
                    stats = commit.stats
                    
                    commits_data.append({
                        'sha': commit.sha[:7],
                        'author': author,
                        'date': commit_date,
                        'hour': commit_date.hour,
                        'weekday': commit_date.weekday(),
                        'month': commit_date.month,
                        'year': commit_date.year,
                        'message': message.split('\n')[0][:100],  # 只取第一行，限制长度
                        'additions': stats.additions,
                        'deletions': stats.deletions,
                        'total_changes': stats.total
                    })
                    progress.update(task, advance=1)
                except Exception as e:
                    continue
        
        if not commits_data:
            return {'error': '未获取到commit数据'}
        
        df = pd.DataFrame(commits_data)
        
        # 分析结果
        result = {
            'total_commits': len(df),
            'date_range': {
                'start': df['date'].min().strftime('%Y-%m-%d'),
                'end': df['date'].max().strftime('%Y-%m-%d')
            },
            'hourly_distribution': self._analyze_hourly_distribution(df),
            'weekday_distribution': self._analyze_weekday_distribution(df),
            'monthly_distribution': self._analyze_monthly_distribution(df),
            'author_stats': self._analyze_author_stats(df),
            'code_changes': self._analyze_code_changes(df),
            'commit_frequency': self._analyze_commit_frequency(df),
            'raw_data': df.to_dict('records')
        }
        
        console.print(f"[green]✓ 分析完成，共处理 {len(df)} 个commits[/green]")
        return result
    
    def _analyze_hourly_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析每小时commit分布"""
        hourly = df['hour'].value_counts().sort_index()
        
        # 确保所有小时都有数据
        all_hours = pd.Series(0, index=range(24))
        all_hours.update(hourly)
        
        peak_hour = all_hours.idxmax()
        
        return {
            'distribution': all_hours.to_dict(),
            'peak_hour': peak_hour,
            'peak_count': int(all_hours[peak_hour]),
            'working_hours_ratio': float(all_hours[9:18].sum() / all_hours.sum()) if all_hours.sum() > 0 else 0
        }
    
    def _analyze_weekday_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析每周commit分布"""
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        weekday = df['weekday'].value_counts().sort_index()
        
        # 确保所有工作日都有数据
        all_weekdays = pd.Series(0, index=range(7))
        all_weekdays.update(weekday)
        
        peak_day = all_weekdays.idxmax()
        
        return {
            'distribution': {weekday_names[i]: int(all_weekdays[i]) for i in range(7)},
            'peak_day': weekday_names[peak_day],
            'peak_count': int(all_weekdays[peak_day]),
            'weekend_ratio': float(all_weekdays[5:7].sum() / all_weekdays.sum()) if all_weekdays.sum() > 0 else 0
        }
    
    def _analyze_monthly_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析每月commit分布"""
        df['year_month'] = df['date'].dt.to_period('M')
        monthly = df.groupby('year_month').size()
        
        return {
            'distribution': {str(k): int(v) for k, v in monthly.items()},
            'average_per_month': float(monthly.mean()),
            'max_month': str(monthly.idxmax()),
            'max_count': int(monthly.max()),
            'min_month': str(monthly.idxmin()),
            'min_count': int(monthly.min())
        }
    
    def _analyze_author_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析作者统计"""
        author_commits = df['author'].value_counts()
        
        top_authors = author_commits.head(10).to_dict()
        
        return {
            'total_authors': len(author_commits),
            'top_authors': top_authors,
            'top_contributor': author_commits.index[0] if len(author_commits) > 0 else None,
            'top_contributor_commits': int(author_commits.iloc[0]) if len(author_commits) > 0 else 0,
            'average_commits_per_author': float(author_commits.mean()),
            'median_commits_per_author': float(author_commits.median())
        }
    
    def _analyze_code_changes(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析代码变更"""
        return {
            'total_additions': int(df['additions'].sum()),
            'total_deletions': int(df['deletions'].sum()),
            'total_changes': int(df['total_changes'].sum()),
            'average_additions_per_commit': float(df['additions'].mean()),
            'average_deletions_per_commit': float(df['deletions'].mean()),
            'max_single_commit_changes': int(df['total_changes'].max()),
            'change_ratio': float(df['additions'].sum() / df['deletions'].sum()) if df['deletions'].sum() > 0 else float('inf')
        }
    
    def _analyze_commit_frequency(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析commit频率"""
        df['date_only'] = df['date'].dt.date
        daily_commits = df.groupby('date_only').size()
        
        # 计算连续提交天数
        dates = sorted(df['date_only'].unique())
        max_streak = 1
        current_streak = 1
        
        for i in range(1, len(dates)):
            if (dates[i] - dates[i-1]).days == 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1
        
        return {
            'average_commits_per_day': float(daily_commits.mean()),
            'max_commits_per_day': int(daily_commits.max()),
            'max_commits_date': str(daily_commits.idxmax()),
            'active_days': len(daily_commits),
            'max_streak_days': max_streak,
            'commits_per_week': float(len(df) / (len(dates) / 7)) if dates else 0
        }


class ContributorAnalyzer:
    """贡献者分析器"""
    
    def __init__(self, client: GitHubClient):
        self.client = client
        self.config = get_config().get_analysis_config()
    
    def analyze_contributors(self, repo_name: str,
                             max_contributors: int = 100) -> Dict[str, Any]:
        """
        分析贡献者活跃度
        
        Args:
            repo_name: 仓库名
            max_contributors: 最大贡献者数
            
        Returns:
            分析结果字典
        """
        console.print(f"[cyan]正在分析 {repo_name} 的贡献者...[/cyan]")
        
        contributors_data = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task("获取贡献者信息...", total=None)
            
            for contributor in self.client.get_contributors(repo_name, max_count=max_contributors):
                try:
                    contributors_data.append({
                        'login': contributor.login,
                        'name': contributor.name or contributor.login,
                        'contributions': contributor.contributions,
                        'followers': contributor.followers,
                        'public_repos': contributor.public_repos,
                        'avatar_url': contributor.avatar_url,
                        'profile_url': contributor.html_url,
                        'company': contributor.company,
                        'location': contributor.location,
                        'created_at': contributor.created_at
                    })
                except Exception as e:
                    continue
        
        if not contributors_data:
            return {'error': '未获取到贡献者数据'}
        
        df = pd.DataFrame(contributors_data)
        
        # 贡献者分析
        result = {
            'total_contributors': len(df),
            'contribution_distribution': self._analyze_contribution_distribution(df),
            'top_contributors': self._get_top_contributors(df),
            'contributor_diversity': self._analyze_diversity(df),
            'account_age_analysis': self._analyze_account_age(df),
            'raw_data': df.to_dict('records')
        }
        
        console.print(f"[green]✓ 分析完成，共处理 {len(df)} 个贡献者[/green]")
        return result
    
    def _analyze_contribution_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析贡献分布"""
        contributions = df['contributions']
        
        # 计算贡献集中度（基尼系数）
        sorted_contributions = np.sort(contributions)
        n = len(sorted_contributions)
        cumsum = np.cumsum(sorted_contributions)
        gini = (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n if n > 0 and cumsum[-1] > 0 else 0
        
        # 帕累托分析：前20%贡献者贡献了多少
        top_20_percent_count = max(1, int(n * 0.2))
        top_20_contributions = df.nlargest(top_20_percent_count, 'contributions')['contributions'].sum()
        total_contributions = contributions.sum()
        pareto_ratio = top_20_contributions / total_contributions if total_contributions > 0 else 0
        
        return {
            'total_contributions': int(total_contributions),
            'average_contributions': float(contributions.mean()),
            'median_contributions': float(contributions.median()),
            'std_contributions': float(contributions.std()),
            'gini_coefficient': float(gini),
            'pareto_ratio': float(pareto_ratio),  # 前20%贡献者的贡献比例
            'contribution_tiers': {
                '1-10': int((contributions <= 10).sum()),
                '11-50': int(((contributions > 10) & (contributions <= 50)).sum()),
                '51-100': int(((contributions > 50) & (contributions <= 100)).sum()),
                '101-500': int(((contributions > 100) & (contributions <= 500)).sum()),
                '500+': int((contributions > 500).sum())
            }
        }
    
    def _get_top_contributors(self, df: pd.DataFrame, top_n: int = 10) -> List[Dict]:
        """获取顶级贡献者"""
        top = df.nlargest(top_n, 'contributions')
        return top[['login', 'name', 'contributions', 'followers', 'profile_url']].to_dict('records')
    
    def _analyze_diversity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析贡献者多样性"""
        # 公司分布
        companies = df['company'].dropna()
        company_distribution = companies.value_counts().head(10).to_dict() if len(companies) > 0 else {}
        
        # 地理位置分布
        locations = df['location'].dropna()
        location_distribution = locations.value_counts().head(10).to_dict() if len(locations) > 0 else {}
        
        return {
            'company_distribution': company_distribution,
            'location_distribution': location_distribution,
            'contributors_with_company': int(df['company'].notna().sum()),
            'contributors_with_location': int(df['location'].notna().sum())
        }
    
    def _analyze_account_age(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析账户年龄"""
        now = datetime.now()
        df['account_age_days'] = (now - pd.to_datetime(df['created_at']).dt.tz_localize(None)).dt.days
        
        return {
            'average_account_age_days': float(df['account_age_days'].mean()),
            'oldest_account_days': int(df['account_age_days'].max()),
            'newest_account_days': int(df['account_age_days'].min()),
            'accounts_older_than_year': int((df['account_age_days'] > 365).sum()),
            'accounts_newer_than_year': int((df['account_age_days'] <= 365).sum())
        }


class IssueAnalyzer:
    """Issue分析器"""
    
    def __init__(self, client: GitHubClient):
        self.client = client
    
    def analyze_issues(self, repo_name: str, 
                       days: int = 365,
                       max_issues: int = 500) -> Dict[str, Any]:
        """
        分析Issue
        
        Args:
            repo_name: 仓库名
            days: 分析天数
            max_issues: 最大Issue数
            
        Returns:
            分析结果字典
        """
        console.print(f"[cyan]正在分析 {repo_name} 的Issues...[/cyan]")
        
        since = datetime.now() - timedelta(days=days)
        issues_data = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task("获取Issues...", total=None)
            
            for issue in self.client.get_issues(repo_name, since=since, max_count=max_issues):
                try:
                    # 计算解决时间
                    resolution_time = None
                    if issue.closed_at:
                        resolution_time = (issue.closed_at - issue.created_at).total_seconds() / 3600  # 小时
                    
                    issues_data.append({
                        'number': issue.number,
                        'title': issue.title[:100],
                        'state': issue.state,
                        'author': issue.user.login if issue.user else None,
                        'created_at': issue.created_at,
                        'closed_at': issue.closed_at,
                        'resolution_time_hours': resolution_time,
                        'comments': issue.comments,
                        'labels': [label.name for label in issue.labels],
                        'assignees': [a.login for a in issue.assignees]
                    })
                except Exception as e:
                    continue
        
        if not issues_data:
            return {'error': '未获取到Issue数据'}
        
        df = pd.DataFrame(issues_data)
        
        result = {
            'total_issues': len(df),
            'open_issues': int((df['state'] == 'open').sum()),
            'closed_issues': int((df['state'] == 'closed').sum()),
            'close_rate': float((df['state'] == 'closed').sum() / len(df)) if len(df) > 0 else 0,
            'resolution_time': self._analyze_resolution_time(df),
            'label_distribution': self._analyze_labels(df),
            'issue_creators': self._analyze_issue_creators(df),
            'monthly_trend': self._analyze_monthly_trend(df),
            'raw_data': df.to_dict('records')
        }
        
        console.print(f"[green]✓ 分析完成，共处理 {len(df)} 个Issues[/green]")
        return result
    
    def _analyze_resolution_time(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析解决时间"""
        closed_issues = df[df['state'] == 'closed']
        resolution_times = closed_issues['resolution_time_hours'].dropna()
        
        if len(resolution_times) == 0:
            return {'error': '没有已关闭的Issue'}
        
        return {
            'average_hours': float(resolution_times.mean()),
            'median_hours': float(resolution_times.median()),
            'min_hours': float(resolution_times.min()),
            'max_hours': float(resolution_times.max()),
            'within_24_hours': int((resolution_times <= 24).sum()),
            'within_week': int((resolution_times <= 168).sum()),  # 168 = 24 * 7
            'over_month': int((resolution_times > 720).sum())  # 720 = 24 * 30
        }
    
    def _analyze_labels(self, df: pd.DataFrame) -> Dict[str, int]:
        """分析标签分布"""
        all_labels = []
        for labels in df['labels']:
            all_labels.extend(labels)
        
        return dict(Counter(all_labels).most_common(15))
    
    def _analyze_issue_creators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析Issue创建者"""
        creators = df['author'].value_counts()
        
        return {
            'total_creators': len(creators),
            'top_creators': creators.head(10).to_dict(),
            'average_issues_per_creator': float(creators.mean()),
            'single_issue_creators': int((creators == 1).sum())
        }
    
    def _analyze_monthly_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析月度趋势"""
        df['year_month'] = pd.to_datetime(df['created_at']).dt.to_period('M')
        monthly = df.groupby('year_month').agg({
            'number': 'count',
            'state': lambda x: (x == 'closed').sum()
        }).rename(columns={'number': 'created', 'state': 'closed'})
        
        return {
            'monthly_created': {str(k): int(v) for k, v in monthly['created'].items()},
            'monthly_closed': {str(k): int(v) for k, v in monthly['closed'].items()}
        }


class PullRequestAnalyzer:
    """Pull Request分析器"""
    
    def __init__(self, client: GitHubClient):
        self.client = client
    
    def analyze_pull_requests(self, repo_name: str,
                               max_prs: int = 300) -> Dict[str, Any]:
        """
        分析Pull Request
        
        Args:
            repo_name: 仓库名
            max_prs: 最大PR数
            
        Returns:
            分析结果字典
        """
        console.print(f"[cyan]正在分析 {repo_name} 的Pull Requests...[/cyan]")
        
        prs_data = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task("获取Pull Requests...", total=None)
            
            for pr in self.client.get_pull_requests(repo_name, max_count=max_prs):
                try:
                    # 计算合并时间
                    merge_time = None
                    if pr.merged_at:
                        merge_time = (pr.merged_at - pr.created_at).total_seconds() / 3600
                    
                    prs_data.append({
                        'number': pr.number,
                        'title': pr.title[:100],
                        'state': pr.state,
                        'merged': pr.merged,
                        'author': pr.user.login if pr.user else None,
                        'created_at': pr.created_at,
                        'merged_at': pr.merged_at,
                        'closed_at': pr.closed_at,
                        'merge_time_hours': merge_time,
                        'comments': pr.comments,
                        'review_comments': pr.review_comments,
                        'additions': pr.additions,
                        'deletions': pr.deletions,
                        'changed_files': pr.changed_files,
                        'labels': [label.name for label in pr.labels]
                    })
                except Exception as e:
                    continue
        
        if not prs_data:
            return {'error': '未获取到Pull Request数据'}
        
        df = pd.DataFrame(prs_data)
        
        result = {
            'total_prs': len(df),
            'open_prs': int((df['state'] == 'open').sum()),
            'merged_prs': int(df['merged'].sum()),
            'closed_not_merged': int(((df['state'] == 'closed') & (~df['merged'])).sum()),
            'merge_rate': float(df['merged'].sum() / len(df)) if len(df) > 0 else 0,
            'merge_time': self._analyze_merge_time(df),
            'code_review': self._analyze_code_review(df),
            'pr_size': self._analyze_pr_size(df),
            'pr_creators': self._analyze_pr_creators(df),
            'raw_data': df.to_dict('records')
        }
        
        console.print(f"[green]✓ 分析完成，共处理 {len(df)} 个Pull Requests[/green]")
        return result
    
    def _analyze_merge_time(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析合并时间"""
        merged_prs = df[df['merged'] == True]
        merge_times = merged_prs['merge_time_hours'].dropna()
        
        if len(merge_times) == 0:
            return {'error': '没有已合并的PR'}
        
        return {
            'average_hours': float(merge_times.mean()),
            'median_hours': float(merge_times.median()),
            'min_hours': float(merge_times.min()),
            'max_hours': float(merge_times.max()),
            'within_24_hours': int((merge_times <= 24).sum()),
            'within_week': int((merge_times <= 168).sum())
        }
    
    def _analyze_code_review(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析代码审查"""
        return {
            'average_comments': float(df['comments'].mean()),
            'average_review_comments': float(df['review_comments'].mean()),
            'prs_with_review': int((df['review_comments'] > 0).sum()),
            'prs_without_review': int((df['review_comments'] == 0).sum()),
            'review_rate': float((df['review_comments'] > 0).sum() / len(df)) if len(df) > 0 else 0
        }
    
    def _analyze_pr_size(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析PR大小"""
        df['total_changes'] = df['additions'] + df['deletions']
        
        return {
            'average_additions': float(df['additions'].mean()),
            'average_deletions': float(df['deletions'].mean()),
            'average_total_changes': float(df['total_changes'].mean()),
            'average_changed_files': float(df['changed_files'].mean()),
            'size_distribution': {
                'small (< 50 lines)': int((df['total_changes'] < 50).sum()),
                'medium (50-200 lines)': int(((df['total_changes'] >= 50) & (df['total_changes'] < 200)).sum()),
                'large (200-500 lines)': int(((df['total_changes'] >= 200) & (df['total_changes'] < 500)).sum()),
                'xlarge (500+ lines)': int((df['total_changes'] >= 500).sum())
            }
        }
    
    def _analyze_pr_creators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析PR创建者"""
        creators = df['author'].value_counts()
        
        return {
            'total_creators': len(creators),
            'top_creators': creators.head(10).to_dict(),
            'average_prs_per_creator': float(creators.mean())
        }


class RepoAnalyzer:
    """仓库综合分析器"""
    
    def __init__(self, client: GitHubClient):
        self.client = client
        self.commit_analyzer = CommitAnalyzer(client)
        self.contributor_analyzer = ContributorAnalyzer(client)
        self.issue_analyzer = IssueAnalyzer(client)
        self.pr_analyzer = PullRequestAnalyzer(client)
    
    def full_analysis(self, repo_name: str,
                      days: int = 365,
                      max_commits: int = 1000,
                      max_contributors: int = 100,
                      max_issues: int = 500,
                      max_prs: int = 300,
                      analyze_issues: bool = True,
                      analyze_prs: bool = True) -> Dict[str, Any]:
        """
        执行完整的仓库分析
        
        Args:
            repo_name: 仓库名
            days: 分析天数
            max_commits: 最大commit数
            max_contributors: 最大贡献者数
            max_issues: 最大Issue数
            max_prs: 最大PR数
            analyze_issues: 是否分析Issues
            analyze_prs: 是否分析PRs
            
        Returns:
            完整分析结果
        """
        console.print(f"\n[bold blue]{'='*60}[/bold blue]")
        console.print(f"[bold blue]开始分析仓库: {repo_name}[/bold blue]")
        console.print(f"[bold blue]{'='*60}[/bold blue]\n")
        
        # 获取仓库基本信息
        repo_info = self.client.get_repo_info(repo_name)
        console.print(f"[green]✓ 获取仓库基本信息完成[/green]")
        
        # 执行各项分析
        result = {
            'repo_info': repo_info,
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'analysis_params': {
                'days': days,
                'max_commits': max_commits,
                'max_contributors': max_contributors,
                'max_issues': max_issues,
                'max_prs': max_prs
            }
        }
        
        # Commit分析
        result['commit_analysis'] = self.commit_analyzer.analyze_commit_patterns(
            repo_name, days=days, max_commits=max_commits
        )
        
        # 贡献者分析
        result['contributor_analysis'] = self.contributor_analyzer.analyze_contributors(
            repo_name, max_contributors=max_contributors
        )
        
        # Issue分析
        if analyze_issues:
            result['issue_analysis'] = self.issue_analyzer.analyze_issues(
                repo_name, days=days, max_issues=max_issues
            )
        
        # PR分析
        if analyze_prs:
            result['pr_analysis'] = self.pr_analyzer.analyze_pull_requests(
                repo_name, max_prs=max_prs
            )
        
        console.print(f"\n[bold green]{'='*60}[/bold green]")
        console.print(f"[bold green]仓库分析完成！[/bold green]")
        console.print(f"[bold green]{'='*60}[/bold green]\n")
        
        return result
