"""
数据分析模块

提供Commit模式、贡献者活跃度等分析功能
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
import re
import math
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
            console=console
        ) as progress:
            task = progress.add_task("获取commits...", total=max_commits)
            
            for commit in self.client.get_commits(repo_name, since=since, max_count=max_commits):
                try:
                    commit_date = commit.commit.author.date
                    author = commit.commit.author.name
                    message = commit.commit.message
                    
                    # 获取文件变更统计
                    stats = commit.stats
                    
                    # 分析commit消息类型
                    message_type = self._classify_commit_message(message)
                    
                    # 获取文件变更详情（如果可用）
                    files_changed = []
                    try:
                        for file in commit.files:
                            files_changed.append({
                                'filename': file.filename,
                                'additions': file.additions,
                                'deletions': file.deletions,
                                'changes': file.changes,
                                'status': file.status
                            })
                    except:
                        pass
                    
                    commits_data.append({
                        'sha': commit.sha[:7],
                        'author': author,
                        'date': commit_date,
                        'hour': commit_date.hour,
                        'weekday': commit_date.weekday(),
                        'month': commit_date.month,
                        'year': commit_date.year,
                        'message': message.split('\n')[0][:100],  # 只取第一行，限制长度
                        'full_message': message,
                        'message_type': message_type,
                        'additions': stats.additions,
                        'deletions': stats.deletions,
                        'total_changes': stats.total,
                        'files_changed': len(files_changed),
                        'files_details': files_changed[:5]  # 只保留前5个文件的详细信息
                    })
                    progress.update(task, advance=1)
                except Exception as e:
                    console.print(f"[yellow]⚠️ 处理commit时出错: {e}[/yellow]")
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
            'commit_patterns': self._analyze_commit_patterns(df),
            'message_types': self._analyze_message_types(df),
            'files_analysis': self._analyze_files(df),
            'raw_data': df.to_dict('records')
        }
        
        console.print(f"[green]✓ 分析完成，共处理 {len(df)} 个commits[/green]")
        return result
    
    def _classify_commit_message(self, message: str) -> str:
        """分类commit消息类型"""
        message_lower = message.lower()
        
        # 常见commit类型模式
        patterns = {
            'feat': r'\b(feat|feature|add)\b',
            'fix': r'\b(fix|bug|issue)\b',
            'docs': r'\b(docs|doc|readme|documentation)\b',
            'style': r'\b(style|format|lint)\b',
            'refactor': r'\b(refactor|restructure|reorganize)\b',
            'test': r'\b(test|tests|testing)\b',
            'chore': r'\b(chore|build|ci|travis|github)\b',
            'perf': r'\b(perf|performance|optimize)\b',
            'revert': r'\b(revert|undo|rollback)\b'
        }
        
        for msg_type, pattern in patterns.items():
            if re.search(pattern, message_lower):
                return msg_type
        
        # 检查是否包含版本号
        if re.search(r'\bv?\d+\.\d+\.\d+\b', message_lower):
            return 'version'
        
        # 检查是否包含合并操作
        if any(word in message_lower for word in ['merge', 'pull request', 'pr']):
            return 'merge'
        
        return 'other'
    
    def _analyze_hourly_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析每小时commit分布"""
        hourly = df['hour'].value_counts().sort_index()
        
        # 确保所有小时都有数据
        all_hours = pd.Series(0, index=range(24))
        all_hours.update(hourly)
        
        peak_hour = all_hours.idxmax()
        
        # 计算不同时间段的比例
        night_ratio = float(all_hours[0:6].sum() / all_hours.sum()) if all_hours.sum() > 0 else 0
        morning_ratio = float(all_hours[6:12].sum() / all_hours.sum()) if all_hours.sum() > 0 else 0
        afternoon_ratio = float(all_hours[12:18].sum() / all_hours.sum()) if all_hours.sum() > 0 else 0
        evening_ratio = float(all_hours[18:24].sum() / all_hours.sum()) if all_hours.sum() > 0 else 0
        
        return {
            'distribution': all_hours.to_dict(),
            'peak_hour': peak_hour,
            'peak_count': int(all_hours[peak_hour]),
            'working_hours_ratio': float(all_hours[9:18].sum() / all_hours.sum()) if all_hours.sum() > 0 else 0,
            'time_slots': {
                'night': night_ratio,
                'morning': morning_ratio,
                'afternoon': afternoon_ratio,
                'evening': evening_ratio
            }
        }
    
    def _analyze_weekday_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析每周commit分布"""
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        weekday = df['weekday'].value_counts().sort_index()
        
        # 确保所有工作日都有数据
        all_weekdays = pd.Series(0, index=range(7))
        all_weekdays.update(weekday)
        
        peak_day = all_weekdays.idxmax()
        
        # 计算工作日vs周末
        weekday_total = float(all_weekdays[0:5].sum())
        weekend_total = float(all_weekdays[5:7].sum())
        total = weekday_total + weekend_total
        
        return {
            'distribution': {weekday_names[i]: int(all_weekdays[i]) for i in range(7)},
            'peak_day': weekday_names[peak_day],
            'peak_count': int(all_weekdays[peak_day]),
            'weekend_ratio': float(all_weekdays[5:7].sum() / all_weekdays.sum()) if all_weekdays.sum() > 0 else 0,
            'weekday_avg': float(weekday_total / 5) if weekday_total > 0 else 0,
            'weekend_avg': float(weekend_total / 2) if weekend_total > 0 else 0
        }
    
    def _analyze_monthly_distribution(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析每月commit分布"""
        df['year_month'] = df['date'].dt.to_period('M')
        monthly = df.groupby('year_month').size()
        
        # 计算月度和季度统计
        if len(monthly) > 0:
            monthly_series = monthly.tolist()
            monthly_change = [0] + [monthly_series[i] - monthly_series[i-1] for i in range(1, len(monthly_series))]
            
            # 季度统计
            df['quarter'] = df['date'].dt.to_period('Q')
            quarterly = df.groupby('quarter').size()
        else:
            monthly_change = []
            quarterly = pd.Series()
        
        return {
            'distribution': {str(k): int(v) for k, v in monthly.items()},
            'average_per_month': float(monthly.mean()),
            'max_month': str(monthly.idxmax()),
            'max_count': int(monthly.max()),
            'min_month': str(monthly.idxmin()),
            'min_count': int(monthly.min()),
            'monthly_changes': monthly_change,
            'quarterly_distribution': {str(k): int(v) for k, v in quarterly.items()} if len(quarterly) > 0 else {}
        }
    
    def _analyze_author_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析作者统计"""
        author_commits = df['author'].value_counts()
        
        # 计算各种统计指标
        total_authors = len(author_commits)
        top_authors = author_commits.head(20).to_dict()
        
        # 活跃度分析
        total_commits = len(df)
        if total_authors > 0:
            active_contributors = int((author_commits >= 10).sum())
            occasional_contributors = int(((author_commits >= 2) & (author_commits < 10)).sum())
            one_time_contributors = int((author_commits == 1).sum())
        else:
            active_contributors = occasional_contributors = one_time_contributors = 0
        
        return {
            'total_authors': total_authors,
            'top_authors': top_authors,
            'top_contributor': author_commits.index[0] if len(author_commits) > 0 else None,
            'top_contributor_commits': int(author_commits.iloc[0]) if len(author_commits) > 0 else 0,
            'top_contributor_ratio': float(author_commits.iloc[0] / total_commits) if len(author_commits) > 0 and total_commits > 0 else 0,
            'average_commits_per_author': float(author_commits.mean()),
            'median_commits_per_author': float(author_commits.median()),
            'std_commits_per_author': float(author_commits.std()),
            'contributor_levels': {
                'active': active_contributors,
                'occasional': occasional_contributors,
                'one_time': one_time_contributors
            }
        }
    
    def _analyze_code_changes(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析代码变更"""
        total_additions = int(df['additions'].sum())
        total_deletions = int(df['deletions'].sum())
        total_changes = total_additions + total_deletions
        
        # 计算净变化和变更效率
        net_change = total_additions - total_deletions
        change_ratio = total_additions / total_deletions if total_deletions > 0 else float('inf')
        
        # 大变更和小变更统计
        large_changes = int((df['total_changes'] > 100).sum())
        medium_changes = int(((df['total_changes'] >= 10) & (df['total_changes'] <= 100)).sum())
        small_changes = int((df['total_changes'] < 10).sum())
        
        return {
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'total_changes': total_changes,
            'net_change': net_change,
            'average_additions_per_commit': float(df['additions'].mean()),
            'average_deletions_per_commit': float(df['deletions'].mean()),
            'max_single_commit_changes': int(df['total_changes'].max()),
            'change_ratio': float(change_ratio),
            'change_distribution': {
                'large': large_changes,
                'medium': medium_changes,
                'small': small_changes
            }
        }
    
    def _analyze_commit_frequency(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析commit频率"""
        df['date_only'] = df['date'].dt.date
        daily_commits = df.groupby('date_only').size()
        
        # 计算连续提交天数
        dates = sorted(df['date_only'].unique())
        max_streak = 0
        current_streak = 0
        streak_start = None
        streaks = []
        
        for i in range(len(dates)):
            if i == 0 or (dates[i] - dates[i-1]).days > 1:
                if current_streak > max_streak:
                    max_streak = current_streak
                if current_streak >= 2:  # 记录至少2天的连续提交
                    streaks.append({
                        'start': dates[i-current_streak],
                        'end': dates[i-1],
                        'length': current_streak
                    })
                current_streak = 1
                streak_start = dates[i]
            else:
                current_streak += 1
        
        # 处理最后一个streak
        if current_streak > max_streak:
            max_streak = current_streak
        if current_streak >= 2:
            streaks.append({
                'start': dates[-current_streak] if len(dates) >= current_streak else dates[0],
                'end': dates[-1],
                'length': current_streak
            })
        
        # 计算间隔统计
        gaps = []
        for i in range(1, len(dates)):
            gap = (dates[i] - dates[i-1]).days
            gaps.append(gap)
        
        avg_gap = statistics.mean(gaps) if gaps else 0
        max_gap = max(gaps) if gaps else 0
        
        return {
            'average_commits_per_day': float(daily_commits.mean()),
            'max_commits_per_day': int(daily_commits.max()),
            'max_commits_date': str(daily_commits.idxmax()),
            'active_days': len(daily_commits),
            'inactive_days': days - len(daily_commits),
            'max_streak_days': max_streak,
            'streaks': streaks[-5:],  # 只返回最近5个streak
            'average_gap_days': float(avg_gap),
            'max_gap_days': max_gap,
            'commits_per_week': float(len(df) / (len(dates) / 7)) if dates else 0
        }
    
    def _analyze_commit_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析commit模式"""
        # 计算提交大小分布
        df['change_size'] = pd.cut(df['total_changes'], 
                                   bins=[0, 10, 50, 100, 500, float('inf')],
                                   labels=['tiny', 'small', 'medium', 'large', 'huge'])
        
        size_dist = df['change_size'].value_counts().to_dict()
        
        # 计算提交时间间隔（按作者）
        df_sorted = df.sort_values(['author', 'date'])
        df_sorted['time_diff'] = df_sorted.groupby('author')['date'].diff().dt.total_seconds() / 3600
        
        avg_time_between_commits = float(df_sorted['time_diff'].mean()) if not df_sorted['time_diff'].isnull().all() else 0
        
        return {
            'size_distribution': size_dist,
            'average_time_between_commits': avg_time_between_commits,
            'commits_per_file': float(df['files_changed'].mean()),
            'multi_file_commits': int((df['files_changed'] > 1).sum())
        }
    
    def _analyze_message_types(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析commit消息类型"""
        type_counts = df['message_type'].value_counts().to_dict()
        total = len(df)
        
        type_percentages = {}
        for msg_type, count in type_counts.items():
            type_percentages[msg_type] = float(count / total)
        
        # 分析消息长度
        df['message_length'] = df['full_message'].str.len()
        avg_message_length = float(df['message_length'].mean())
        
        return {
            'type_counts': type_counts,
            'type_percentages': type_percentages,
            'average_message_length': avg_message_length
        }
    
    def _analyze_files(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析文件变更模式"""
        # 统计文件变更频率
        all_files = []
        for files in df['files_details']:
            if files:
                all_files.extend([f['filename'] for f in files])
        
        if all_files:
            file_counts = Counter(all_files)
            top_files = dict(file_counts.most_common(20))
            
            # 分析文件扩展名
            extensions = Counter()
            for filename in all_files:
                if '.' in filename:
                    ext = filename.split('.')[-1].lower()
                    extensions[ext] += 1
            
            top_extensions = dict(extensions.most_common(10))
        else:
            top_files = {}
            top_extensions = {}
        
        return {
            'most_changed_files': top_files,
            'file_extensions': top_extensions,
            'average_files_per_commit': float(df['files_changed'].mean())
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
            BarColumn(),
            console=console
        ) as progress:
            task = progress.add_task("获取贡献者信息...", total=max_contributors)
            
            for contributor in self.client.get_contributors(repo_name, max_count=max_contributors):
                try:
                    # 获取更多详细信息
                    created_at = contributor.created_at
                    account_age_days = (datetime.now() - created_at).days if created_at else 0
                    
                    contributors_data.append({
                        'login': contributor.login,
                        'name': contributor.name or contributor.login,
                        'contributions': contributor.contributions,
                        'followers': contributor.followers,
                        'following': contributor.following,
                        'public_repos': contributor.public_repos,
                        'public_gists': contributor.public_gists,
                        'avatar_url': contributor.avatar_url,
                        'profile_url': contributor.html_url,
                        'company': contributor.company,
                        'location': contributor.location,
                        'created_at': created_at,
                        'updated_at': contributor.updated_at,
                        'bio': contributor.bio,
                        'email': contributor.email,
                        'blog': contributor.blog,
                        'twitter_username': contributor.twitter_username,
                        'account_age_days': account_age_days,
                        'hireable': contributor.hireable,
                        'type': contributor.type
                    })
                    progress.update(task, advance=1)
                except Exception as e:
                    console.print(f"[yellow]⚠️ 处理贡献者 {contributor.login} 时出错: {e}[/yellow]")
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
            'account_analysis': self._analyze_accounts(df),
            'social_analysis': self._analyze_social(df),
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
        if n > 0 and sorted_contributions.sum() > 0:
            cumsum = np.cumsum(sorted_contributions)
            gini = (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n
        else:
            gini = 0
        
        # 帕累托分析
        total_contributions = contributions.sum()
        
        for percentage in [0.1, 0.2, 0.5]:
            top_count = max(1, int(n * percentage))
            top_contributions = df.nlargest(top_count, 'contributions')['contributions'].sum()
            ratio = top_contributions / total_contributions if total_contributions > 0 else 0
            
            if percentage == 0.2:
                pareto_ratio = ratio
        
        # 赫芬达尔-赫希曼指数（HHI）用于衡量集中度
        if total_contributions > 0:
            market_shares = contributions / total_contributions
            hhi = (market_shares ** 2).sum() * 10000
        else:
            hhi = 0
        
        return {
            'total_contributions': int(total_contributions),
            'average_contributions': float(contributions.mean()),
            'median_contributions': float(contributions.median()),
            'std_contributions': float(contributions.std()),
            'gini_coefficient': float(gini),
            'hhi_index': float(hhi),
            'pareto_ratio': float(pareto_ratio),  # 前20%贡献者的贡献比例
            'contribution_tiers': {
                '1-5': int((contributions <= 5).sum()),
                '6-10': int(((contributions > 5) & (contributions <= 10)).sum()),
                '11-50': int(((contributions > 10) & (contributions <= 50)).sum()),
                '51-100': int(((contributions > 50) & (contributions <= 100)).sum()),
                '101-500': int(((contributions > 100) & (contributions <= 500)).sum()),
                '500+': int((contributions > 500).sum())
            }
        }
    
    def _get_top_contributors(self, df: pd.DataFrame, top_n: int = 15) -> List[Dict]:
        """获取顶级贡献者"""
        top = df.nlargest(top_n, 'contributions')
        return top[['login', 'name', 'contributions', 'followers', 'profile_url', 'company', 'location']].to_dict('records')
    
    def _analyze_diversity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析贡献者多样性"""
        # 公司分布
        companies = df['company'].dropna()
        company_distribution = companies.value_counts().head(15).to_dict() if len(companies) > 0 else {}
        
        # 地理位置分布
        locations = df['location'].dropna()
        location_distribution = locations.value_counts().head(15).to_dict() if len(locations) > 0 else {}
        
        # 贡献者类型分布
        types = df['type'].dropna()
        type_distribution = types.value_counts().to_dict() if len(types) > 0 else {}
        
        return {
            'company_distribution': company_distribution,
            'location_distribution': location_distribution,
            'type_distribution': type_distribution,
            'contributors_with_company': int(df['company'].notna().sum()),
            'contributors_with_location': int(df['location'].notna().sum()),
            'company_ratio': float(df['company'].notna().sum() / len(df)) if len(df) > 0 else 0,
            'location_ratio': float(df['location'].notna().sum() / len(df)) if len(df) > 0 else 0
        }
    
    def _analyze_accounts(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析账户信息"""
        # 账户年龄分析
        now = datetime.now()
        df['account_age_days'] = df['account_age_days']
        
        # 活跃度分析
        df['updated_days_ago'] = (now - pd.to_datetime(df['updated_at']).dt.tz_localize(None)).dt.days
        
        # 计算贡献密度
        df['contributions_per_day'] = df['contributions'] / df['account_age_days'].clip(lower=1)
        
        return {
            'average_account_age_days': float(df['account_age_days'].mean()),
            'median_account_age_days': float(df['account_age_days'].median()),
            'oldest_account_days': int(df['account_age_days'].max()),
            'newest_account_days': int(df['account_age_days'].min()),
            'accounts_by_age': {
                '< 1年': int((df['account_age_days'] < 365).sum()),
                '1-3年': int(((df['account_age_days'] >= 365) & (df['account_age_days'] < 1095)).sum()),
                '3-5年': int(((df['account_age_days'] >= 1095) & (df['account_age_days'] < 1825)).sum()),
                '> 5年': int((df['account_age_days'] >= 1825).sum())
            },
            'average_contributions_per_day': float(df['contributions_per_day'].mean()),
            'recently_active': int((df['updated_days_ago'] < 30).sum()),
            'inactive': int((df['updated_days_ago'] > 365).sum())
        }
    
    def _analyze_social(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析社交信息"""
        # 博客和社交媒体统计
        has_blog = int(df['blog'].notna().sum())
        has_twitter = int(df['twitter_username'].notna().sum())
        has_email = int(df['email'].notna().sum())
        has_bio = int(df['bio'].notna().sum())
        
        # 影响力分析
        avg_followers = float(df['followers'].mean())
        avg_following = float(df['following'].mean())
        
        # 高影响力用户
        high_influence = int((df['followers'] > 1000).sum())
        medium_influence = int(((df['followers'] >= 100) & (df['followers'] <= 1000)).sum())
        low_influence = int((df['followers'] < 100).sum())
        
        return {
            'social_presence': {
                'has_blog': has_blog,
                'has_twitter': has_twitter,
                'has_email': has_email,
                'has_bio': has_bio
            },
            'influence_stats': {
                'average_followers': avg_followers,
                'average_following': avg_following,
                'high_influence': high_influence,
                'medium_influence': medium_influence,
                'low_influence': low_influence
            }
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


class CodeQualityAnalyzer:
    """代码质量分析器
    
    分析提交信息质量、代码变更模式等指标来评估代码质量
    """
    
    def __init__(self, client: GitHubClient):
        self.client = client
        
        # 常见的不良提交信息模式
        self.bad_commit_patterns = [
            r'^fix$',
            r'^update$',
            r'^change$',
            r'^修改$',
            r'^更新$',
            r'^\.+$',
            r'^\s*$',
            r'^wip$',
            r'^test$',
            r'^temp$',
            r'^tmp$',
        ]
        
        # 良好提交信息的特征
        self.good_commit_prefixes = [
            'feat:', 'fix:', 'docs:', 'style:', 'refactor:',
            'perf:', 'test:', 'chore:', 'ci:', 'build:',
            'feat(', 'fix(', 'docs(', 'style(', 'refactor(',
        ]
    
    def analyze_code_quality(self, repo_name: str, 
                              commits_data: List[Dict] = None,
                              max_commits: int = 500) -> Dict[str, Any]:
        """
        分析代码质量指标
        
        Args:
            repo_name: 仓库名
            commits_data: 已有的commits数据（可选，避免重复获取）
            max_commits: 最大commit数
            
        Returns:
            代码质量分析结果
        """
        console.print(f"[cyan]正在分析 {repo_name} 的代码质量...[/cyan]")
        
        if commits_data is None:
            # 如果没有提供数据，从API获取
            since = datetime.now() - timedelta(days=365)
            commits_data = []
            for commit in self.client.get_commits(repo_name, since=since, max_count=max_commits):
                try:
                    commits_data.append({
                        'sha': commit.sha,
                        'message': commit.commit.message,
                        'additions': commit.stats.additions,
                        'deletions': commit.stats.deletions,
                        'files_changed': len(commit.files) if commit.files else 0,
                        'date': commit.commit.author.date,
                        'author': commit.commit.author.name
                    })
                except:
                    continue
        
        if not commits_data:
            return {'error': '未获取到commit数据'}
        
        result = {
            'commit_message_quality': self._analyze_commit_messages(commits_data),
            'code_change_patterns': self._analyze_change_patterns(commits_data),
            'commit_size_analysis': self._analyze_commit_sizes(commits_data),
            'refactoring_indicators': self._analyze_refactoring(commits_data),
            'quality_score': 0  # 将在最后计算
        }
        
        # 计算综合质量分数 (0-100)
        result['quality_score'] = self._calculate_quality_score(result)
        
        console.print(f"[green]✓ 代码质量分析完成，质量分数: {result['quality_score']:.1f}/100[/green]")
        return result
    
    def _analyze_commit_messages(self, commits_data: List[Dict]) -> Dict[str, Any]:
        """分析提交信息质量"""
        messages = [c.get('message', '') for c in commits_data]
        
        # 统计各类提交信息
        bad_messages = 0
        good_messages = 0
        conventional_commits = 0
        message_lengths = []
        
        for msg in messages:
            first_line = msg.split('\n')[0].strip().lower()
            message_lengths.append(len(first_line))
            
            # 检查是否是不良提交信息
            is_bad = False
            for pattern in self.bad_commit_patterns:
                if re.match(pattern, first_line, re.IGNORECASE):
                    bad_messages += 1
                    is_bad = True
                    break
            
            if not is_bad:
                # 检查是否符合Conventional Commits规范
                for prefix in self.good_commit_prefixes:
                    if first_line.startswith(prefix):
                        conventional_commits += 1
                        good_messages += 1
                        break
                else:
                    # 检查是否是有意义的提交信息（长度>10且包含动词）
                    if len(first_line) > 10:
                        good_messages += 1
        
        total = len(messages)
        
        return {
            'total_commits': total,
            'bad_messages': bad_messages,
            'bad_message_ratio': bad_messages / total if total > 0 else 0,
            'good_messages': good_messages,
            'good_message_ratio': good_messages / total if total > 0 else 0,
            'conventional_commits': conventional_commits,
            'conventional_ratio': conventional_commits / total if total > 0 else 0,
            'average_message_length': statistics.mean(message_lengths) if message_lengths else 0,
            'message_length_std': statistics.stdev(message_lengths) if len(message_lengths) > 1 else 0
        }
    
    def _analyze_change_patterns(self, commits_data: List[Dict]) -> Dict[str, Any]:
        """分析代码变更模式"""
        additions = [c.get('additions', 0) for c in commits_data]
        deletions = [c.get('deletions', 0) for c in commits_data]
        
        total_additions = sum(additions)
        total_deletions = sum(deletions)
        
        # 代码净增长
        net_growth = total_additions - total_deletions
        
        # 代码周转率（删除/添加比率）
        churn_rate = total_deletions / total_additions if total_additions > 0 else 0
        
        # 大型提交检测（单次变更>500行）
        large_commits = sum(1 for a, d in zip(additions, deletions) if a + d > 500)
        
        return {
            'total_additions': total_additions,
            'total_deletions': total_deletions,
            'net_growth': net_growth,
            'churn_rate': churn_rate,
            'large_commits': large_commits,
            'large_commit_ratio': large_commits / len(commits_data) if commits_data else 0,
            'average_change_per_commit': (total_additions + total_deletions) / len(commits_data) if commits_data else 0
        }
    
    def _analyze_commit_sizes(self, commits_data: List[Dict]) -> Dict[str, Any]:
        """分析提交大小分布"""
        sizes = [c.get('additions', 0) + c.get('deletions', 0) for c in commits_data]
        
        if not sizes:
            return {'error': '无数据'}
        
        return {
            'average_size': statistics.mean(sizes),
            'median_size': statistics.median(sizes),
            'max_size': max(sizes),
            'min_size': min(sizes),
            'std_size': statistics.stdev(sizes) if len(sizes) > 1 else 0,
            'size_distribution': {
                'tiny (<10 lines)': sum(1 for s in sizes if s < 10),
                'small (10-50 lines)': sum(1 for s in sizes if 10 <= s < 50),
                'medium (50-200 lines)': sum(1 for s in sizes if 50 <= s < 200),
                'large (200-500 lines)': sum(1 for s in sizes if 200 <= s < 500),
                'huge (500+ lines)': sum(1 for s in sizes if s >= 500)
            }
        }
    
    def _analyze_refactoring(self, commits_data: List[Dict]) -> Dict[str, Any]:
        """分析重构相关指标"""
        refactoring_keywords = ['refactor', 'restructure', 'reorganize', 'cleanup', 
                                 'clean up', 'improve', 'optimize', '重构', '优化']
        
        refactoring_commits = 0
        for c in commits_data:
            msg = c.get('message', '').lower()
            if any(kw in msg for kw in refactoring_keywords):
                refactoring_commits += 1
        
        # 检测可能的重构（删除量接近添加量）
        potential_refactoring = 0
        for c in commits_data:
            additions = c.get('additions', 0)
            deletions = c.get('deletions', 0)
            if additions > 50 and deletions > 50:
                ratio = min(additions, deletions) / max(additions, deletions)
                if ratio > 0.7:  # 添加和删除比例接近
                    potential_refactoring += 1
        
        return {
            'explicit_refactoring_commits': refactoring_commits,
            'refactoring_ratio': refactoring_commits / len(commits_data) if commits_data else 0,
            'potential_refactoring_commits': potential_refactoring,
            'total_refactoring_indicator': refactoring_commits + potential_refactoring
        }
    
    def _calculate_quality_score(self, analysis_result: Dict) -> float:
        """计算综合质量分数"""
        score = 100.0
        
        # 提交信息质量 (最多扣30分)
        msg_quality = analysis_result.get('commit_message_quality', {})
        bad_ratio = msg_quality.get('bad_message_ratio', 0)
        score -= bad_ratio * 30
        
        # 如果使用Conventional Commits规范，加分
        conventional_ratio = msg_quality.get('conventional_ratio', 0)
        score += conventional_ratio * 10  # 最多加10分
        
        # 大型提交惩罚 (最多扣20分)
        change_patterns = analysis_result.get('code_change_patterns', {})
        large_ratio = change_patterns.get('large_commit_ratio', 0)
        score -= large_ratio * 20
        
        # 重构活动奖励 (最多加10分)
        refactoring = analysis_result.get('refactoring_indicators', {})
        refactor_ratio = refactoring.get('refactoring_ratio', 0)
        score += min(refactor_ratio * 50, 10)
        
        return max(0, min(100, score))
    
class CodeComplexityAnalyzer:
    """代码复杂度分析器
    
    分析代码变更的复杂性指标，如文件变更模式、依赖关系等
    """
    
    def __init__(self, client: GitHubClient):
        self.client = client
        
        # 复杂代码变更的特征
        self.complexity_indicators = {
            'high_entropy': ['config', 'settings', 'constant', 'enum'],  # 配置/常量文件
            'critical': ['test', 'spec', '__tests__'],  # 测试文件
            'infrastructure': ['docker', 'dockerfile', 'ci', '.github'],  # 基础设施文件
            'documentation': ['readme', 'docs', 'guide', 'tutorial'],  # 文档文件
        }
    
    def analyze_complexity(self, repo_name: str,
                           commits_data: List[Dict] = None,
                           max_commits: int = 200) -> Dict[str, Any]:
        """
        分析代码复杂度指标
        
        Args:
            repo_name: 仓库名
            commits_data: 已有的commits数据
            max_commits: 最大commit数
            
        Returns:
            代码复杂度分析结果
        """
        console.print(f"[cyan]正在分析 {repo_name} 的代码复杂度...[/cyan]")
        
        if commits_data is None:
            # 获取commits数据
            since = datetime.now() - timedelta(days=180)
            commits_data = []
            try:
                for commit in self.client.get_commits(repo_name, since=since, max_count=max_commits):
                    try:
                        files_changed = []
                        for file in commit.files:
                            files_changed.append({
                                'filename': file.filename,
                                'additions': file.additions,
                                'deletions': file.deletions,
                                'changes': file.changes,
                                'status': file.status
                            })
                        
                        commits_data.append({
                            'sha': commit.sha[:7],
                            'message': commit.commit.message,
                            'files_changed': files_changed,
                            'date': commit.commit.author.date,
                            'total_changes': commit.stats.total
                        })
                    except:
                        continue
            except Exception as e:
                console.print(f"[yellow]⚠️ 获取commits时出错: {e}[/yellow]")
        
        if not commits_data:
            return {'error': '未获取到commit数据'}
        
        result = {
            'file_change_patterns': self._analyze_file_patterns(commits_data),
            'dependency_changes': self._analyze_dependency_changes(commits_data),
            'refactoring_complexity': self._analyze_refactoring_complexity(commits_data),
            'architecture_changes': self._analyze_architecture_changes(commits_data),
            'complexity_score': 0
        }
        
        # 计算复杂度分数
        result['complexity_score'] = self._calculate_complexity_score(result)
        
        console.print(f"[green]✓ 代码复杂度分析完成，复杂度分数: {result['complexity_score']:.1f}[/green]")
        return result
    
    def _analyze_file_patterns(self, commits_data: List[Dict]) -> Dict[str, Any]:
        """分析文件变更模式"""
        all_files = []
        file_types = Counter()
        
        for commit in commits_data:
            for file_info in commit.get('files_changed', []):
                filename = file_info['filename'].lower()
                all_files.append(filename)
                
                # 分析文件类型
                if '.' in filename:
                    ext = filename.split('.')[-1]
                    if len(ext) <= 5:  # 合理文件扩展名长度
                        file_types[ext] += 1
                
                # 检查文件类别
                for category, keywords in self.complexity_indicators.items():
                    if any(keyword in filename for keyword in keywords):
                        file_types[category] = file_types.get(category, 0) + 1
        
        # 计算文件变更的熵（衡量变更的集中度）
        if all_files:
            file_freq = Counter(all_files)
            total_changes = len(all_files)
            entropy = 0
            for freq in file_freq.values():
                probability = freq / total_changes
                entropy -= probability * math.log2(probability) if probability > 0 else 0
        else:
            entropy = 0
        
        return {
            'total_unique_files': len(set(all_files)),
            'total_file_changes': len(all_files),
            'most_frequently_changed_files': dict(file_freq.most_common(10)) if 'file_freq' in locals() else {},
            'file_type_distribution': dict(file_types.most_common(15)),
            'change_entropy': float(entropy),
            'files_per_commit': len(all_files) / len(commits_data) if commits_data else 0
        }
    
    def _analyze_dependency_changes(self, commits_data: List[Dict]) -> Dict[str, Any]:
        """分析依赖变更"""
        dependency_files = ['package.json', 'requirements.txt', 'pom.xml', 'build.gradle', 
                           'cargo.toml', 'go.mod', 'composer.json', 'pyproject.toml']
        
        dependency_changes = 0
        config_changes = 0
        
        for commit in commits_data:
            message = commit.get('message', '').lower()
            commit_files = [f['filename'].lower() for f in commit.get('files_changed', [])]
            
            # 检查依赖文件变更
            if any(dep_file in commit_files for dep_file in dependency_files):
                dependency_changes += 1
            
            # 检查配置文件变更
            config_keywords = ['config', 'setting', 'properties', '.env', '.yml', '.yaml']
            if any(keyword in message for keyword in ['depend', 'version', 'upgrade', 'update']) or \
               any(keyword in ' '.join(commit_files) for keyword in config_keywords):
                config_changes += 1
        
        return {
            'dependency_file_changes': dependency_changes,
            'config_file_changes': config_changes,
            'dependency_change_ratio': dependency_changes / len(commits_data) if commits_data else 0,
            'config_change_ratio': config_changes / len(commits_data) if commits_data else 0
        }
    
    def _analyze_refactoring_complexity(self, commits_data: List[Dict]) -> Dict[str, Any]:
        """分析重构复杂度"""
        refactoring_keywords = ['refactor', 'restructure', 'reorganize', 'cleanup', 
                               'rename', 'move', 'extract', 'inline', '重构']
        
        complex_refactoring = 0
        simple_refactoring = 0
        
        for commit in commits_data:
            message = commit.get('message', '').lower()
            files_changed = commit.get('files_changed', [])
            
            # 检查重构提交
            if any(keyword in message for keyword in refactoring_keywords):
                # 分析重构复杂度
                file_count = len(files_changed)
                total_changes = sum(f['changes'] for f in files_changed)
                
                if file_count > 5 or total_changes > 100:
                    complex_refactoring += 1
                else:
                    simple_refactoring += 1
        
        return {
            'complex_refactoring_commits': complex_refactoring,
            'simple_refactoring_commits': simple_refactoring,
            'total_refactoring_commits': complex_refactoring + simple_refactoring,
            'refactoring_ratio': (complex_refactoring + simple_refactoring) / len(commits_data) if commits_data else 0,
            'complex_refactoring_ratio': complex_refactoring / len(commits_data) if commits_data else 0
        }
    
    def _analyze_architecture_changes(self, commits_data: List[Dict]) -> Dict[str, Any]:
        """分析架构变更"""
        architecture_patterns = {
            'module_structure': ['src/', 'lib/', 'modules/', 'packages/'],
            'api_changes': ['api/', 'rest/', 'graphql', 'endpoint', 'route'],
            'database': ['migration', 'schema', 'model', 'entity', 'table'],
            'interface': ['interface', 'contract', 'protocol', 'api']
        }
        
        architecture_changes = {category: 0 for category in architecture_patterns}
        
        for commit in commits_data:
            message = commit.get('message', '').lower()
            commit_files = ' '.join([f['filename'].lower() for f in commit.get('files_changed', [])])
            
            for category, patterns in architecture_patterns.items():
                # 检查提交信息或文件路径中的架构相关关键词
                if any(pattern in message or pattern in commit_files for pattern in patterns):
                    architecture_changes[category] += 1
        
        return architecture_changes
    
    def _calculate_complexity_score(self, analysis_result: Dict) -> float:
        """计算复杂度分数"""
        score = 50.0  # 基础分
        
        file_patterns = analysis_result.get('file_change_patterns', {})
        dependency = analysis_result.get('dependency_changes', {})
        refactoring = analysis_result.get('refactoring_complexity', {})
        
        # 文件变更熵影响（0-20分）
        entropy = file_patterns.get('change_entropy', 0)
        score += min(entropy * 5, 20)
        
        # 依赖变更惩罚（最多扣15分）
        dep_ratio = dependency.get('dependency_change_ratio', 0)
        score -= min(dep_ratio * 30, 15)
        
        # 复杂重构奖励（最多加10分）
        complex_refactor_ratio = refactoring.get('complex_refactoring_ratio', 0)
        score += min(complex_refactor_ratio * 50, 10)
        
        # 架构变更加分（最多加15分）
        arch_changes = analysis_result.get('architecture_changes', {})
        total_arch_changes = sum(arch_changes.values())
        score += min(total_arch_changes * 2, 15)
        
        return max(0, min(100, score))

class ReleaseAnalyzer:
    """版本发布分析器
    
    分析项目的版本发布模式、发布频率和版本质量
    """
    
    def __init__(self, client: GitHubClient):
        self.client = client
    
    def analyze_releases(self, repo_name: str, max_releases: int = 50) -> Dict[str, Any]:
        """
        分析版本发布情况
        
        Args:
            repo_name: 仓库名
            max_releases: 最大获取的发布数
            
        Returns:
            发布分析结果
        """
        console.print(f"[cyan]正在分析 {repo_name} 的版本发布...[/cyan]")
        
        releases_data = []
        
        try:
            repo = self.client.github.get_repo(repo_name)
            releases = repo.get_releases()
            
            count = 0
            for release in releases:
                if count >= max_releases:
                    break
                    
                releases_data.append({
                    'tag_name': release.tag_name,
                    'name': release.title or release.tag_name,
                    'created_at': release.created_at,
                    'published_at': release.published_at,
                    'is_prerelease': release.prerelease,
                    'is_draft': release.draft,
                    'body_length': len(release.body) if release.body else 0,
                    'assets_count': release.get_assets().totalCount if release.get_assets() else 0,
                    'author': release.author.login if release.author else None
                })
                count += 1
                
        except Exception as e:
            console.print(f"[yellow]获取发布信息时出错: {e}[/yellow]")
        
        if not releases_data:
            return {
                'total_releases': 0,
                'message': '该仓库没有发布版本或无法获取发布信息'
            }
        
        df = pd.DataFrame(releases_data)
        
        result = {
            'total_releases': len(df),
            'prerelease_count': int(df['is_prerelease'].sum()),
            'stable_releases': int((~df['is_prerelease']).sum()),
            'release_frequency': self._analyze_release_frequency(df),
            'version_pattern': self._analyze_version_pattern(df),
            'release_quality': self._analyze_release_quality(df),
            'release_authors': self._analyze_release_authors(df),
            'raw_data': releases_data
        }
        
        console.print(f"[green]✓ 版本发布分析完成，共 {len(df)} 个版本[/green]")
        return result
    
    def _analyze_release_frequency(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析发布频率"""
        if len(df) < 2:
            return {'message': '发布数量不足，无法分析频率'}
        
        df_sorted = df.sort_values('published_at')
        dates = pd.to_datetime(df_sorted['published_at'])
        
        # 计算发布间隔
        intervals = dates.diff().dropna()
        intervals_days = intervals.dt.total_seconds() / 86400
        
        # 按年月统计发布数
        df['year_month'] = pd.to_datetime(df['published_at']).dt.to_period('M')
        monthly_releases = df.groupby('year_month').size()
        
        return {
            'average_interval_days': float(intervals_days.mean()),
            'median_interval_days': float(intervals_days.median()),
            'min_interval_days': float(intervals_days.min()),
            'max_interval_days': float(intervals_days.max()),
            'releases_per_month': float(monthly_releases.mean()),
            'monthly_distribution': {str(k): int(v) for k, v in monthly_releases.items()}
        }
    
    def _analyze_version_pattern(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析版本号模式"""
        tags = df['tag_name'].tolist()
        
        # 检测版本号格式
        semver_pattern = r'^v?\d+\.\d+\.\d+(-.*)?$'
        calver_pattern = r'^v?\d{4}[\.\-]\d{1,2}([\.\-]\d{1,2})?$'
        
        semver_count = sum(1 for t in tags if re.match(semver_pattern, t))
        calver_count = sum(1 for t in tags if re.match(calver_pattern, t))
        
        # 检测版本类型
        major_releases = 0
        minor_releases = 0
        patch_releases = 0
        
        for i, tag in enumerate(tags[:-1]):
            match = re.match(r'v?(\d+)\.(\d+)\.(\d+)', tag)
            next_match = re.match(r'v?(\d+)\.(\d+)\.(\d+)', tags[i+1])
            
            if match and next_match:
                curr = [int(x) for x in match.groups()]
                prev = [int(x) for x in next_match.groups()]
                
                if curr[0] > prev[0]:
                    major_releases += 1
                elif curr[1] > prev[1]:
                    minor_releases += 1
                else:
                    patch_releases += 1
        
        return {
            'uses_semver': semver_count > len(tags) * 0.8,
            'uses_calver': calver_count > len(tags) * 0.8,
            'semver_count': semver_count,
            'calver_count': calver_count,
            'major_releases': major_releases,
            'minor_releases': minor_releases,
            'patch_releases': patch_releases
        }
    
    def _analyze_release_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析发布质量"""
        return {
            'average_changelog_length': float(df['body_length'].mean()),
            'releases_with_changelog': int((df['body_length'] > 0).sum()),
            'releases_with_assets': int((df['assets_count'] > 0).sum()),
            'average_assets': float(df['assets_count'].mean()),
            'changelog_coverage': float((df['body_length'] > 0).sum() / len(df)) if len(df) > 0 else 0
        }
    
    def _analyze_release_authors(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析发布者"""
        authors = df['author'].dropna().value_counts()
        
        return {
            'total_authors': len(authors),
            'top_authors': authors.head(5).to_dict(),
            'releases_per_author': float(len(df) / len(authors)) if len(authors) > 0 else 0
        }


class ActivityTrendAnalyzer:
    """活跃度趋势分析器
    
    分析项目的活跃度变化趋势、生命周期阶段
    """
    
    def __init__(self, client: GitHubClient):
        self.client = client
    
    def analyze_activity_trend(self, repo_name: str,
                                commits_data: List[Dict] = None,
                                issues_data: List[Dict] = None,
                                prs_data: List[Dict] = None) -> Dict[str, Any]:
        """
        分析活跃度趋势
        
        Args:
            repo_name: 仓库名
            commits_data: commits数据
            issues_data: issues数据
            prs_data: PRs数据
            
        Returns:
            活跃度趋势分析结果
        """
        console.print(f"[cyan]正在分析 {repo_name} 的活跃度趋势...[/cyan]")
        
        result = {
            'commit_trend': self._analyze_commit_trend(commits_data) if commits_data else {},
            'engagement_trend': self._analyze_engagement_trend(issues_data, prs_data),
            'lifecycle_stage': '',
            'health_indicators': {}
        }
        
        # 判断项目生命周期阶段
        result['lifecycle_stage'] = self._determine_lifecycle_stage(result)
        
        # 计算健康指标
        result['health_indicators'] = self._calculate_health_indicators(
            commits_data, issues_data, prs_data
        )
        
        console.print(f"[green]✓ 活跃度趋势分析完成[/green]")
        return result
    
    def _analyze_commit_trend(self, commits_data: List[Dict]) -> Dict[str, Any]:
        """分析commit趋势"""
        if not commits_data:
            return {}
        
        df = pd.DataFrame(commits_data)
        df['date'] = pd.to_datetime(df['date'])
        df['year_month'] = df['date'].dt.to_period('M')
        
        monthly = df.groupby('year_month').size()
        
        if len(monthly) < 3:
            return {'message': '数据不足，无法分析趋势'}
        
        # 计算趋势（简单线性回归斜率）
        x = np.arange(len(monthly))
        y = monthly.values
        slope = np.polyfit(x, y, 1)[0]
        
        # 计算最近3个月与之前的对比
        recent_avg = monthly.tail(3).mean() if len(monthly) >= 3 else monthly.mean()
        historical_avg = monthly.head(len(monthly)-3).mean() if len(monthly) > 3 else monthly.mean()
        
        trend_direction = 'increasing' if slope > 0.5 else ('decreasing' if slope < -0.5 else 'stable')
        
        return {
            'trend_direction': trend_direction,
            'trend_slope': float(slope),
            'recent_monthly_average': float(recent_avg),
            'historical_monthly_average': float(historical_avg),
            'change_ratio': float(recent_avg / historical_avg) if historical_avg > 0 else 0,
            'monthly_data': {str(k): int(v) for k, v in monthly.items()}
        }
    
    def _analyze_engagement_trend(self, issues_data: List[Dict], 
                                   prs_data: List[Dict]) -> Dict[str, Any]:
        """分析参与度趋势"""
        result = {}
        
        if issues_data:
            df_issues = pd.DataFrame(issues_data)
            df_issues['created_at'] = pd.to_datetime(df_issues['created_at'])
            df_issues['year_month'] = df_issues['created_at'].dt.to_period('M')
            monthly_issues = df_issues.groupby('year_month').size()
            result['monthly_issues'] = {str(k): int(v) for k, v in monthly_issues.items()}
        
        if prs_data:
            df_prs = pd.DataFrame(prs_data)
            df_prs['created_at'] = pd.to_datetime(df_prs['created_at'])
            df_prs['year_month'] = df_prs['created_at'].dt.to_period('M')
            monthly_prs = df_prs.groupby('year_month').size()
            result['monthly_prs'] = {str(k): int(v) for k, v in monthly_prs.items()}
        
        return result
    
    def _determine_lifecycle_stage(self, analysis_result: Dict) -> str:
        """判断项目生命周期阶段"""
        commit_trend = analysis_result.get('commit_trend', {})
        trend_direction = commit_trend.get('trend_direction', 'unknown')
        change_ratio = commit_trend.get('change_ratio', 1)
        
        if trend_direction == 'increasing' and change_ratio > 1.2:
            return 'growth'  # 成长期
        elif trend_direction == 'stable' or (0.8 <= change_ratio <= 1.2):
            return 'mature'  # 成熟期
        elif trend_direction == 'decreasing' and change_ratio < 0.5:
            return 'decline'  # 衰退期
        elif change_ratio < 0.8:
            return 'maintenance'  # 维护期
        else:
            return 'unknown'
    
    def _calculate_health_indicators(self, commits_data: List[Dict],
                                      issues_data: List[Dict],
                                      prs_data: List[Dict]) -> Dict[str, Any]:
        """计算健康指标"""
        indicators = {
            'activity_score': 0,
            'responsiveness_score': 0,
            'community_score': 0,
            'overall_health': 0
        }
        
        # 活跃度分数 (基于commit)
        if commits_data:
            recent_commits = sum(1 for c in commits_data 
                               if datetime.now() - c.get('date', datetime.now()).replace(tzinfo=None) < timedelta(days=30))
            indicators['activity_score'] = min(100, recent_commits * 2)
        
        # 响应性分数 (基于Issue解决率)
        if issues_data:
            closed = sum(1 for i in issues_data if i.get('state') == 'closed')
            indicators['responsiveness_score'] = (closed / len(issues_data)) * 100 if issues_data else 0
        
        # 社区分数 (基于PR参与)
        if prs_data:
            with_review = sum(1 for p in prs_data if p.get('review_comments', 0) > 0)
            indicators['community_score'] = (with_review / len(prs_data)) * 100 if prs_data else 0
        
        # 综合健康分数
        scores = [v for v in [indicators['activity_score'], 
                              indicators['responsiveness_score'],
                              indicators['community_score']] if v > 0]
        indicators['overall_health'] = statistics.mean(scores) if scores else 0
        
        return indicators


class CommunityHealthAnalyzer:
    """社区健康度分析器
    
    评估开源社区的健康状况、多样性和可持续性
    """
    
    def __init__(self, client: GitHubClient):
        self.client = client
    
    def analyze_community_health(self, repo_name: str,
                                  contributor_data: List[Dict] = None,
                                  issues_data: List[Dict] = None,
                                  prs_data: List[Dict] = None) -> Dict[str, Any]:
        """
        分析社区健康度
        
        Args:
            repo_name: 仓库名
            contributor_data: 贡献者数据
            issues_data: Issues数据
            prs_data: PRs数据
            
        Returns:
            社区健康度分析结果
        """
        console.print(f"[cyan]正在分析 {repo_name} 的社区健康度...[/cyan]")
        
        result = {
            'bus_factor': self._calculate_bus_factor(contributor_data),
            'newcomer_friendliness': self._analyze_newcomer_friendliness(repo_name),
            'community_diversity': self._analyze_community_diversity(contributor_data),
            'response_time_metrics': self._analyze_response_times(issues_data, prs_data),
            'contributor_retention': self._analyze_contributor_retention(contributor_data),
            'community_score': 0
        }
        
        # 计算综合社区分数
        result['community_score'] = self._calculate_community_score(result)
        
        console.print(f"[green]✓ 社区健康度分析完成，社区分数: {result['community_score']:.1f}/100[/green]")
        return result
    
    def _calculate_bus_factor(self, contributor_data: List[Dict]) -> Dict[str, Any]:
        """计算Bus Factor（关键人物依赖度）
        
        Bus Factor是指项目需要失去多少个核心贡献者才会导致项目停滞
        """
        if not contributor_data:
            return {'bus_factor': 0, 'message': '无贡献者数据'}
        
        contributions = sorted([c.get('contributions', 0) for c in contributor_data], reverse=True)
        total = sum(contributions)
        
        if total == 0:
            return {'bus_factor': 0}
        
        # 计算达到50%贡献需要的人数
        cumsum = 0
        bus_factor = 0
        for c in contributions:
            cumsum += c
            bus_factor += 1
            if cumsum >= total * 0.5:
                break
        
        # 评估风险
        risk_level = 'high' if bus_factor <= 2 else ('medium' if bus_factor <= 5 else 'low')
        
        return {
            'bus_factor': bus_factor,
            'risk_level': risk_level,
            'top_contributor_share': contributions[0] / total if total > 0 else 0,
            'top_3_contributors_share': sum(contributions[:3]) / total if total > 0 and len(contributions) >= 3 else 0
        }
    
    def _analyze_newcomer_friendliness(self, repo_name: str) -> Dict[str, Any]:
        """分析对新手的友好程度"""
        try:
            repo = self.client.github.get_repo(repo_name)
            
            # 检查是否有贡献指南
            has_contributing = False
            has_code_of_conduct = False
            has_issue_templates = False
            has_pr_template = False
            
            try:
                repo.get_contents('CONTRIBUTING.md')
                has_contributing = True
            except:
                try:
                    repo.get_contents('.github/CONTRIBUTING.md')
                    has_contributing = True
                except:
                    pass
            
            try:
                repo.get_contents('CODE_OF_CONDUCT.md')
                has_code_of_conduct = True
            except:
                pass
            
            try:
                repo.get_contents('.github/ISSUE_TEMPLATE')
                has_issue_templates = True
            except:
                try:
                    repo.get_contents('.github/ISSUE_TEMPLATE.md')
                    has_issue_templates = True
                except:
                    pass
            
            try:
                repo.get_contents('.github/PULL_REQUEST_TEMPLATE.md')
                has_pr_template = True
            except:
                pass
            
            # 检查good first issue标签
            good_first_issues = repo.get_issues(labels=['good first issue'], state='open')
            good_first_issue_count = good_first_issues.totalCount
            
            # 计算新手友好度分数
            score = 0
            score += 25 if has_contributing else 0
            score += 20 if has_code_of_conduct else 0
            score += 20 if has_issue_templates else 0
            score += 15 if has_pr_template else 0
            score += min(20, good_first_issue_count * 2)
            
            return {
                'has_contributing_guide': has_contributing,
                'has_code_of_conduct': has_code_of_conduct,
                'has_issue_templates': has_issue_templates,
                'has_pr_template': has_pr_template,
                'good_first_issues_count': good_first_issue_count,
                'newcomer_score': score
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_community_diversity(self, contributor_data: List[Dict]) -> Dict[str, Any]:
        """分析社区多样性"""
        if not contributor_data:
            return {}
        
        # 公司多样性
        companies = [c.get('company') for c in contributor_data if c.get('company')]
        unique_companies = len(set(companies))
        
        # 地理多样性
        locations = [c.get('location') for c in contributor_data if c.get('location')]
        unique_locations = len(set(locations))
        
        # 计算公司集中度（单一公司占比）
        if companies:
            company_counts = Counter(companies)
            top_company_share = company_counts.most_common(1)[0][1] / len(companies)
        else:
            top_company_share = 0
        
        return {
            'unique_companies': unique_companies,
            'unique_locations': unique_locations,
            'contributors_with_company': len(companies),
            'contributors_with_location': len(locations),
            'company_diversity_index': 1 - top_company_share,  # 越高越多样
            'is_company_dominated': top_company_share > 0.5
        }
    
    def _analyze_response_times(self, issues_data: List[Dict], 
                                 prs_data: List[Dict]) -> Dict[str, Any]:
        """分析响应时间"""
        result = {}
        
        if issues_data:
            resolution_times = [i.get('resolution_time_hours') for i in issues_data 
                              if i.get('resolution_time_hours') is not None]
            if resolution_times:
                result['issue_avg_resolution_hours'] = statistics.mean(resolution_times)
                result['issue_median_resolution_hours'] = statistics.median(resolution_times)
        
        if prs_data:
            merge_times = [p.get('merge_time_hours') for p in prs_data 
                         if p.get('merge_time_hours') is not None]
            if merge_times:
                result['pr_avg_merge_hours'] = statistics.mean(merge_times)
                result['pr_median_merge_hours'] = statistics.median(merge_times)
        
        return result
    
    def _analyze_contributor_retention(self, contributor_data: List[Dict]) -> Dict[str, Any]:
        """分析贡献者留存"""
        if not contributor_data:
            return {}
        
        now = datetime.now()
        
        # 按账户年龄分类
        new_contributors = 0  # 1年内
        established = 0  # 1-3年
        veteran = 0  # 3年以上
        
        for c in contributor_data:
            created_at = c.get('created_at')
            if created_at:
                age_days = (now - created_at.replace(tzinfo=None)).days
                if age_days < 365:
                    new_contributors += 1
                elif age_days < 365 * 3:
                    established += 1
                else:
                    veteran += 1
        
        total = len(contributor_data)
        
        return {
            'new_contributors': new_contributors,
            'established_contributors': established,
            'veteran_contributors': veteran,
            'new_ratio': new_contributors / total if total > 0 else 0,
            'veteran_ratio': veteran / total if total > 0 else 0
        }
    
    def _calculate_community_score(self, analysis_result: Dict) -> float:
        """计算综合社区分数"""
        score = 0
        
        # Bus Factor评分 (最高30分)
        bus_factor = analysis_result.get('bus_factor', {}).get('bus_factor', 0)
        if bus_factor >= 5:
            score += 30
        elif bus_factor >= 3:
            score += 20
        elif bus_factor >= 2:
            score += 10
        
        # 新手友好度 (最高30分)
        newcomer_score = analysis_result.get('newcomer_friendliness', {}).get('newcomer_score', 0)
        score += newcomer_score * 0.3
        
        # 多样性 (最高20分)
        diversity = analysis_result.get('community_diversity', {})
        diversity_index = diversity.get('company_diversity_index', 0)
        score += diversity_index * 20
        
        # 响应速度 (最高20分)
        response = analysis_result.get('response_time_metrics', {})
        issue_response = response.get('issue_median_resolution_hours', float('inf'))
        if issue_response < 24:
            score += 20
        elif issue_response < 72:
            score += 15
        elif issue_response < 168:
            score += 10
        
        return min(100, score)


class RepoAnalyzer:
    """仓库综合分析器"""
    
    def __init__(self, client: GitHubClient):
        self.client = client
        self.commit_analyzer = CommitAnalyzer(client)
        self.contributor_analyzer = ContributorAnalyzer(client)
        self.issue_analyzer = IssueAnalyzer(client)
        self.pr_analyzer = PullRequestAnalyzer(client)
        self.code_quality_analyzer = CodeQualityAnalyzer(client)
        self.code_complexity_analyzer = CodeComplexityAnalyzer(client)  # 新增
        self.release_analyzer = ReleaseAnalyzer(client)
        self.activity_analyzer = ActivityTrendAnalyzer(client)
        self.community_analyzer = CommunityHealthAnalyzer(client)
    
    def full_analysis(self, repo_name: str,
                      days: int = 365,
                      max_commits: int = 1000,
                      max_contributors: int = 100,
                      max_issues: int = 500,
                      max_prs: int = 300,
                      analyze_issues: bool = True,
                      analyze_prs: bool = True,
                      analyze_releases: bool = True,
                      analyze_quality: bool = True,
                      analyze_complexity: bool = True,  # 新增参数
                      analyze_trends: bool = True,
                      analyze_community: bool = True) -> Dict[str, Any]:
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
            analyze_releases: 是否分析发布版本
            analyze_quality: 是否分析代码质量
            analyze_complexity: 是否分析代码复杂度（新增）
            analyze_trends: 是否分析活跃度趋势
            analyze_community: 是否分析社区健康度
            
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
        
        # 版本发布分析
        if analyze_releases:
            result['release_analysis'] = self.release_analyzer.analyze_releases(repo_name)
        
        # 代码质量分析
        if analyze_quality:
            commits_raw = result.get('commit_analysis', {}).get('raw_data', [])
            result['code_quality_analysis'] = self.code_quality_analyzer.analyze_code_quality(
                repo_name, commits_data=commits_raw
            )

        # 代码复杂度分析
        if analyze_complexity:
            commits_raw = result.get('commit_analysis', {}).get('raw_data', [])
            result['code_complexity_analysis'] = self.code_complexity_analyzer.analyze_complexity(
                repo_name,
                commits_data=commits_raw
            )

        # 活跃度趋势分析
        if analyze_trends:
            commits_raw = result.get('commit_analysis', {}).get('raw_data', [])
            issues_raw = result.get('issue_analysis', {}).get('raw_data', []) if analyze_issues else []
            prs_raw = result.get('pr_analysis', {}).get('raw_data', []) if analyze_prs else []
            
            result['activity_trend_analysis'] = self.activity_analyzer.analyze_activity_trend(
                repo_name,
                commits_data=commits_raw,
                issues_data=issues_raw,
                prs_data=prs_raw
            )
        
        # 社区健康度分析
        if analyze_community:
            contributor_raw = result.get('contributor_analysis', {}).get('raw_data', [])
            issues_raw = result.get('issue_analysis', {}).get('raw_data', []) if analyze_issues else []
            prs_raw = result.get('pr_analysis', {}).get('raw_data', []) if analyze_prs else []
            
            result['community_health_analysis'] = self.community_analyzer.analyze_community_health(
                repo_name,
                contributor_data=contributor_raw,
                issues_data=issues_raw,
                prs_data=prs_raw
            )
        
        # 生成综合评估
        result['overall_assessment'] = self._generate_overall_assessment(result)
        
        console.print(f"\n[bold green]{'='*60}[/bold green]")
        console.print(f"[bold green]仓库分析完成！[/bold green]")
        console.print(f"[bold green]{'='*60}[/bold green]\n")
        
        return result
    
    def _generate_overall_assessment(self, analysis_result: Dict) -> Dict[str, Any]:
        """生成综合评估报告"""
        assessment = {
            'scores': {},
            'strengths': [],
            'weaknesses': [],
            'recommendations': [],
            'overall_grade': ''
        }
        
        # 收集各项分数（添加复杂度分数）
        if 'code_complexity_analysis' in analysis_result:
            complexity_score = analysis_result['code_complexity_analysis'].get('complexity_score', 0)
            assessment['scores']['code_complexity'] = complexity_score
            
            # 根据复杂度分数给出建议
            if complexity_score > 70:
                assessment['weaknesses'].append('代码复杂度较高，维护成本可能增加')
                assessment['recommendations'].append('建议进行模块化重构，降低耦合度')
            elif complexity_score < 30:
                assessment['strengths'].append('代码结构简单清晰，易于维护')
        
        if 'community_health_analysis' in analysis_result:
            community_score = analysis_result['community_health_analysis'].get('community_score', 0)
            assessment['scores']['community_health'] = community_score
            
            bus_factor = analysis_result['community_health_analysis'].get('bus_factor', {}).get('bus_factor', 0)
            if bus_factor <= 2:
                assessment['weaknesses'].append(f'Bus Factor较低({bus_factor})，存在单点故障风险')
                assessment['recommendations'].append('建议培养更多核心贡献者')
            
            if community_score >= 70:
                assessment['strengths'].append('社区健康度良好')
        
        if 'activity_trend_analysis' in analysis_result:
            lifecycle = analysis_result['activity_trend_analysis'].get('lifecycle_stage', '')
            assessment['lifecycle_stage'] = lifecycle
            
            if lifecycle == 'growth':
                assessment['strengths'].append('项目处于成长期，活跃度持续上升')
            elif lifecycle == 'decline':
                assessment['weaknesses'].append('项目活跃度下降')
                assessment['recommendations'].append('建议增加推广和社区活动')
        
        # 计算综合评级
        scores = list(assessment['scores'].values())
        if scores:
            avg_score = statistics.mean(scores)
            if avg_score >= 85:
                assessment['overall_grade'] = 'A'
            elif avg_score >= 70:
                assessment['overall_grade'] = 'B'
            elif avg_score >= 55:
                assessment['overall_grade'] = 'C'
            else:
                assessment['overall_grade'] = 'D'
            assessment['average_score'] = avg_score
        
        return assessment
    
    def quick_analysis(self, repo_name: str) -> Dict[str, Any]:
        """
        快速分析（仅获取基本信息和关键指标）
        
        Args:
            repo_name: 仓库名
            
        Returns:
            快速分析结果
        """
        console.print(f"[cyan]正在执行快速分析: {repo_name}[/cyan]")
        
        repo_info = self.client.get_repo_info(repo_name)
        
        result = {
            'repo_info': repo_info,
            'quick_stats': {
                'stars': repo_info.get('stars', 0),
                'forks': repo_info.get('forks', 0),
                'open_issues': repo_info.get('open_issues', 0),
                'watchers': repo_info.get('watchers', 0),
                'is_active': repo_info.get('updated_at', '') > (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            }
        }
        
        console.print(f"[green]✓ 快速分析完成[/green]")
        return result
