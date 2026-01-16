"""
多仓库比较分析模块

支持对多个GitHub仓库进行对比分析
"""

import os
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import json

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class MetricCategory(Enum):
    """指标类别"""
    POPULARITY = "popularity"       # 受欢迎程度
    ACTIVITY = "activity"           # 活跃度
    COMMUNITY = "community"         # 社区健康
    QUALITY = "quality"             # 质量指标
    GROWTH = "growth"               # 增长趋势


@dataclass
class RepoMetrics:
    """仓库指标数据类"""
    repo_name: str
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    total_commits: int = 0
    total_contributors: int = 0
    total_issues: int = 0
    total_prs: int = 0
    pr_merge_rate: float = 0.0
    avg_issue_close_time: float = 0.0
    avg_pr_review_time: float = 0.0
    language: str = ""
    license: str = ""
    created_at: str = ""
    last_updated: str = ""
    
    # 计算得分
    popularity_score: float = 0.0
    activity_score: float = 0.0
    community_score: float = 0.0
    overall_score: float = 0.0
    
    # [新增字段：不破坏原有构造]
    stack_footprint: Dict[str, float] = field(default_factory=dict)
    
    @classmethod
    def from_analysis_result(cls, data: Dict) -> 'RepoMetrics':
        """从分析结果创建指标对象"""
        repo_info = data.get('repo_info', {})
        commit_data = data.get('commit_analysis', {})
        contrib_data = data.get('contributor_analysis', {})
        issue_data = data.get('issue_analysis', {})
        pr_data = data.get('pr_analysis', {})
        
        return cls(
            repo_name=repo_info.get('full_name', 'Unknown'),
            stars=repo_info.get('stars', 0),
            forks=repo_info.get('forks', 0),
            watchers=repo_info.get('watchers', 0),
            open_issues=repo_info.get('open_issues', 0),
            total_commits=commit_data.get('total_commits', 0),
            total_contributors=contrib_data.get('total_contributors', 0),
            total_issues=issue_data.get('total_issues', 0),
            total_prs=pr_data.get('total_prs', 0),
            pr_merge_rate=pr_data.get('merge_rate', 0),
            avg_issue_close_time=issue_data.get('avg_close_time_days', 0),
            avg_pr_review_time=pr_data.get('avg_review_time_days', 0),
            language=repo_info.get('language', ''),
            license=repo_info.get('license', ''),
            created_at=str(repo_info.get('created_at', ''))[:10],
            last_updated=str(repo_info.get('updated_at', ''))[:10]
        )


class RepoComparator:
    """仓库比较器"""
    
    def __init__(self):
        self.repos: List[RepoMetrics] = []
        self.comparison_result: Dict = {}
    
    def add_repo(self, analysis_result: Dict):
        """添加仓库分析结果"""
        metrics = RepoMetrics.from_analysis_result(analysis_result)
        self._calculate_scores(metrics)
        # [新增调用：分析技术栈特征]
        self._analyze_stack_footprint(metrics, analysis_result)
        self.repos.append(metrics)
    
    def add_repos(self, analysis_results: List[Dict]):
        """批量添加仓库分析结果"""
        for result in analysis_results:
            self.add_repo(result)
    
    def _calculate_scores(self, metrics: RepoMetrics):
        """计算各项评分"""
        # 受欢迎程度评分（基于stars、forks、watchers）
        metrics.popularity_score = self._calculate_popularity_score(metrics)
        
        # 活跃度评分（基于commits、contributors、更新频率）
        metrics.activity_score = self._calculate_activity_score(metrics)
        
        # 社区健康评分（基于issue处理、PR合并率等）
        metrics.community_score = self._calculate_community_score(metrics)
        
        # 综合评分
        metrics.overall_score = (
            metrics.popularity_score * 0.3 +
            metrics.activity_score * 0.4 +
            metrics.community_score * 0.3
        )
    
    def _calculate_popularity_score(self, metrics: RepoMetrics) -> float:
        """计算受欢迎程度评分（0-100）"""
        # 使用对数尺度，因为star数量差异可能很大
        import math
        
        star_score = min(100, (math.log10(metrics.stars + 1) / math.log10(100000)) * 100) if metrics.stars > 0 else 0
        fork_score = min(100, (math.log10(metrics.forks + 1) / math.log10(10000)) * 100) if metrics.forks > 0 else 0
        
        return star_score * 0.7 + fork_score * 0.3
    
    def _calculate_activity_score(self, metrics: RepoMetrics) -> float:
        """计算活跃度评分（0-100）"""
        import math
        
        commit_score = min(100, (math.log10(metrics.total_commits + 1) / math.log10(10000)) * 100)
        contributor_score = min(100, (math.log10(metrics.total_contributors + 1) / math.log10(1000)) * 100)
        
        return commit_score * 0.6 + contributor_score * 0.4
    
    def _calculate_community_score(self, metrics: RepoMetrics) -> float:
        """计算社区健康评分（0-100）"""
        # PR合并率评分
        merge_rate_score = metrics.pr_merge_rate if metrics.pr_merge_rate <= 100 else 100
        
        # Issue关闭时间评分（越快越好，7天为满分基准）
        if metrics.avg_issue_close_time > 0:
            close_time_score = max(0, 100 - (metrics.avg_issue_close_time / 7) * 50)
        else:
            close_time_score = 50  # 无数据给中等分
        
        return merge_rate_score * 0.5 + close_time_score * 0.5

    def _analyze_stack_footprint(self, metrics: RepoMetrics, raw_data: Dict):
        """
        [新增功能] 分析技术栈足迹
        利用语言分布和仓库描述简单推断项目的'技术指纹'
        """
        repo_info = raw_data.get('repo_info', {})
        description = str(repo_info.get('description', '')).lower()
        
        # 预定义一些技术关键词权重
        footprint = {"Web": 0.0, "AI/ML": 0.0, "System": 0.0, "Tool": 0.0}
        
        # 简单逻辑：根据主语言和描述打分
        lang = metrics.language.lower()
        if lang in ['python', 'r', 'julia']: footprint["AI/ML"] += 40
        if lang in ['javascript', 'typescript', 'html', 'css']: footprint["Web"] += 50
        if lang in ['c', 'cpp', 'rust', 'go']: footprint["System"] += 50
        
        if 'api' in description or 'web' in description: footprint["Web"] += 30
        if 'deep learning' in description or 'model' in description: footprint["AI/ML"] += 40
        if 'cli' in description or 'utility' in description: footprint["Tool"] += 50
        
        metrics.stack_footprint = {k: min(100.0, v) for k, v in footprint.items()}
    
    def compare(self) -> Dict:
        """执行比较分析"""
        if len(self.repos) < 2:
            console.print("[yellow]至少需要2个仓库才能进行比较[/yellow]")
            return {}
        
        self.comparison_result = {
            'repos': [self._repo_to_dict(r) for r in self.repos],
            'rankings': self._generate_rankings(),
            'statistics': self._generate_statistics(),
            'recommendations': self._generate_recommendations(),
            'comparison_time': datetime.now().isoformat()
        }
        
        return self.comparison_result
    
    def _repo_to_dict(self, repo: RepoMetrics) -> Dict:
        """将仓库指标转换为字典"""
        return {
            'name': repo.repo_name,
            'stars': repo.stars,
            'forks': repo.forks,
            'watchers': repo.watchers,
            'commits': repo.total_commits,
            'contributors': repo.total_contributors,
            'issues': repo.total_issues,
            'prs': repo.total_prs,
            'pr_merge_rate': repo.pr_merge_rate,
            'language': repo.language,
            'license': repo.license,
            'stack_footprint': repo.stack_footprint, # [新增导出]
            'scores': {
                'popularity': round(repo.popularity_score, 2),
                'activity': round(repo.activity_score, 2),
                'community': round(repo.community_score, 2),
                'overall': round(repo.overall_score, 2)
            }
        }
    
    def _generate_rankings(self) -> Dict:
        """生成各维度排名"""
        rankings = {}
        
        # 按不同指标排名
        metrics_to_rank = [
            ('stars', 'Stars排名', True),
            ('forks', 'Forks排名', True),
            ('total_commits', 'Commits排名', True),
            ('total_contributors', '贡献者排名', True),
            ('pr_merge_rate', 'PR合并率排名', True),
            ('popularity_score', '受欢迎度排名', True),
            ('activity_score', '活跃度排名', True),
            ('community_score', '社区健康排名', True),
            ('overall_score', '综合排名', True),
        ]
        
        for attr, name, desc in metrics_to_rank:
            sorted_repos = sorted(self.repos, key=lambda x: getattr(x, attr), reverse=desc)
            rankings[name] = [r.repo_name for r in sorted_repos]
        
        return rankings
    
    def _generate_statistics(self) -> Dict:
        """生成统计数据"""
        if not self.repos:
            return {}
        
        def calc_stats(values: List[float]) -> Dict:
            import statistics
            if not values:
                return {'min': 0, 'max': 0, 'avg': 0, 'median': 0}
            return {
                'min': min(values),
                'max': max(values),
                'avg': round(statistics.mean(values), 2),
                'median': round(statistics.median(values), 2)
            }
        
        return {
            'stars': calc_stats([r.stars for r in self.repos]),
            'forks': calc_stats([r.forks for r in self.repos]),
            'commits': calc_stats([r.total_commits for r in self.repos]),
            'contributors': calc_stats([r.total_contributors for r in self.repos]),
            'issues': calc_stats([r.total_issues for r in self.repos]),
            'prs': calc_stats([r.total_prs for r in self.repos]),
            'pr_merge_rate': calc_stats([r.pr_merge_rate for r in self.repos]),
            'overall_score': calc_stats([r.overall_score for r in self.repos])
        }
    
    def _generate_recommendations(self) -> List[Dict]:
        """生成建议"""
        recommendations = []
        
        if not self.repos:
            return recommendations
        
        # 找出各方面最佳和最差的仓库
        best_overall = max(self.repos, key=lambda x: x.overall_score)
        worst_overall = min(self.repos, key=lambda x: x.overall_score)
        
        recommendations.append({
            'type': 'best_overall',
            'repo': best_overall.repo_name,
            'message': f"综合表现最佳的仓库是 {best_overall.repo_name}，综合评分 {best_overall.overall_score:.1f}"
        })
        
        # 最活跃的仓库
        most_active = max(self.repos, key=lambda x: x.activity_score)
        recommendations.append({
            'type': 'most_active',
            'repo': most_active.repo_name,
            'message': f"最活跃的仓库是 {most_active.repo_name}，活跃度评分 {most_active.activity_score:.1f}"
        })
        
        # 社区最健康的仓库
        best_community = max(self.repos, key=lambda x: x.community_score)
        recommendations.append({
            'type': 'best_community',
            'repo': best_community.repo_name,
            'message': f"社区最健康的仓库是 {best_community.repo_name}，社区评分 {best_community.community_score:.1f}"
        })
        
        # 针对表现较差的仓库给出改进建议
        for repo in self.repos:
            if repo.community_score < 50:
                recommendations.append({
                    'type': 'improvement',
                    'repo': repo.repo_name,
                    'message': f"{repo.repo_name} 的社区健康度较低，建议加快Issue处理速度和PR审查效率"
                })
            if repo.activity_score < 40:
                recommendations.append({
                    'type': 'warning',
                    'repo': repo.repo_name,
                    'message': f"{repo.repo_name} 的活跃度较低，可能需要更多的社区贡献者参与"
                })
        
        return recommendations
    
    def print_comparison_table(self):
        """打印比较表格"""
        if not self.repos:
            console.print("[yellow]没有可比较的仓库数据[/yellow]")
            return
        
        table = Table(title="📊 仓库对比分析", show_header=True, header_style="bold cyan")
        
        table.add_column("指标", style="cyan", no_wrap=True)
        for repo in self.repos:
            short_name = repo.repo_name.split('/')[-1][:15]
            table.add_column(short_name, justify="right")
        
        # 添加数据行
        metrics = [
            ("⭐ Stars", "stars"),
            ("🍴 Forks", "forks"),
            ("📝 Commits", "total_commits"),
            ("👥 贡献者", "total_contributors"),
            ("🐛 Issues", "total_issues"),
            ("🔀 PRs", "total_prs"),
            ("✅ PR合并率", "pr_merge_rate"),
            ("💻 语言", "language"),
            ("📜 许可证", "license"),
            ("🏆 综合评分", "overall_score"),
        ]
        
        for label, attr in metrics:
            row = [label]
            for repo in self.repos:
                value = getattr(repo, attr)
                if isinstance(value, float):
                    row.append(f"{value:.1f}")
                elif isinstance(value, int):
                    row.append(f"{value:,}")
                else:
                    row.append(str(value) or "N/A")
            table.add_row(*row)
        
        console.print(table)
    
    def print_rankings(self):
        """打印排名信息"""
        if not self.comparison_result:
            self.compare()
        
        rankings = self.comparison_result.get('rankings', {})
        
        console.print("\n[bold]🏅 各维度排名[/bold]\n")
        
        for category, ranking in rankings.items():
            ranking_str = " > ".join([f"{i+1}.{r.split('/')[-1]}" for i, r in enumerate(ranking)])
            console.print(f"[cyan]{category}:[/cyan] {ranking_str}")
    
    def print_recommendations(self):
        """打印建议"""
        if not self.comparison_result:
            self.compare()
        
        recommendations = self.comparison_result.get('recommendations', [])
        
        console.print("\n[bold]💡 分析建议[/bold]\n")
        
        for rec in recommendations:
            rec_type = rec.get('type', '')
            message = rec.get('message', '')
            
            if rec_type in ['best_overall', 'most_active', 'best_community']:
                console.print(f"[green]✓ {message}[/green]")
            elif rec_type == 'warning':
                console.print(f"[yellow]⚠ {message}[/yellow]")
            else:
                console.print(f"[blue]ℹ {message}[/blue]")
    
    def export_comparison(self, output_dir: str = "output") -> str:
        """导出比较结果为JSON"""
        if not self.comparison_result:
            self.compare()
        
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, "repo_comparison.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.comparison_result, f, indent=2, ensure_ascii=False)
        
        console.print(f"[green]比较结果已导出: {filepath}[/green]")
        return filepath


class BenchmarkAnalyzer:
    """基准分析器 - 与行业标准对比"""
    
    # 行业基准数据（可配置）
    BENCHMARKS = {
        'small': {  # 小型项目 (<1k stars)
            'min_commits_per_month': 5,
            'min_contributors': 3,
            'target_pr_merge_rate': 70,
            'target_issue_close_days': 14
        },
        'medium': {  # 中型项目 (1k-10k stars)
            'min_commits_per_month': 20,
            'min_contributors': 10,
            'target_pr_merge_rate': 75,
            'target_issue_close_days': 7
        },
        'large': {  # 大型项目 (>10k stars)
            'min_commits_per_month': 50,
            'min_contributors': 30,
            'target_pr_merge_rate': 80,
            'target_issue_close_days': 5
        }
    }
    
    def __init__(self):
        self.results = []
    
    def analyze(self, analysis_result: Dict) -> Dict:
        """对仓库进行基准分析"""
        metrics = RepoMetrics.from_analysis_result(analysis_result)
        
        # 确定项目规模
        if metrics.stars < 1000:
            size = 'small'
        elif metrics.stars < 10000:
            size = 'medium'
        else:
            size = 'large'
        
        benchmark = self.BENCHMARKS[size]
        
        # 计算各项对比
        result = {
            'repo_name': metrics.repo_name,
            'project_size': size,
            'benchmark_comparison': {
                'commits_vs_benchmark': {
                    'current': metrics.total_commits,
                    'benchmark': benchmark['min_commits_per_month'] * 12,
                    'status': 'pass' if metrics.total_commits >= benchmark['min_commits_per_month'] * 12 else 'fail'
                },
                'contributors_vs_benchmark': {
                    'current': metrics.total_contributors,
                    'benchmark': benchmark['min_contributors'],
                    'status': 'pass' if metrics.total_contributors >= benchmark['min_contributors'] else 'fail'
                },
                'pr_merge_rate_vs_benchmark': {
                    'current': metrics.pr_merge_rate,
                    'benchmark': benchmark['target_pr_merge_rate'],
                    'status': 'pass' if metrics.pr_merge_rate >= benchmark['target_pr_merge_rate'] else 'fail'
                },
                'issue_close_time_vs_benchmark': {
                    'current': metrics.avg_issue_close_time,
                    'benchmark': benchmark['target_issue_close_days'],
                    'status': 'pass' if metrics.avg_issue_close_time <= benchmark['target_issue_close_days'] else 'fail'
                }
            },
            'overall_benchmark_score': 0,
            'recommendations': []
        }
        
        # 计算总体基准分数
        passed = sum(1 for item in result['benchmark_comparison'].values() if item['status'] == 'pass')
        result['overall_benchmark_score'] = (passed / 4) * 100
        
        # 生成建议
        for metric, data in result['benchmark_comparison'].items():
            if data['status'] == 'fail':
                metric_name = metric.replace('_vs_benchmark', '').replace('_', ' ')
                result['recommendations'].append(
                    f"{metric_name} 未达到{size}项目基准 (当前: {data['current']}, 基准: {data['benchmark']})"
                )
        
        self.results.append(result)
        return result
    
    def print_benchmark_report(self, result: Dict):
        """打印基准分析报告"""
        console.print(Panel(
            f"[bold]{result['repo_name']}[/bold]\n"
            f"项目规模: {result['project_size'].upper()}\n"
            f"基准达标率: {result['overall_benchmark_score']:.0f}%",
            title="📏 基准分析报告"
        ))
        
        table = Table(show_header=True, header_style="bold")
        table.add_column("指标", style="cyan")
        table.add_column("当前值", justify="right")
        table.add_column("基准值", justify="right")
        table.add_column("状态", justify="center")
        
        for metric, data in result['benchmark_comparison'].items():
            metric_name = metric.replace('_vs_benchmark', '').replace('_', ' ').title()
            status_icon = "✅" if data['status'] == 'pass' else "❌"
            status_style = "green" if data['status'] == 'pass' else "red"
            
            table.add_row(
                metric_name,
                f"{data['current']:.1f}" if isinstance(data['current'], float) else str(data['current']),
                str(data['benchmark']),
                f"[{status_style}]{status_icon}[/{status_style}]"
            )
        
        console.print(table)
        
        if result['recommendations']:
            console.print("\n[bold yellow]改进建议:[/bold yellow]")
            for rec in result['recommendations']:
                console.print(f"  • {rec}")


class TrendComparator:
    """趋势对比器 - 对比多个仓库的时间趋势"""
    
    def __init__(self):
        self.repos_data = []
    
    def add_repo_data(self, analysis_result: Dict):
        """添加仓库数据"""
        self.repos_data.append(analysis_result)
    
    def compare_commit_trends(self) -> Dict:
        """对比Commit趋势"""
        trends = {}
        
        for data in self.repos_data:
            repo_name = data.get('repo_info', {}).get('full_name', 'Unknown')
            commit_data = data.get('commit_analysis', {})
            monthly = commit_data.get('monthly_distribution', {}).get('distribution', {})
            
            trends[repo_name] = monthly
        
        return {
            'type': 'commit_trend',
            'data': trends,
            'analysis': self._analyze_trends(trends)
        }
    
    def _analyze_trends(self, trends: Dict) -> Dict:
        """分析趋势数据"""
        analysis = {
            'most_consistent': None,
            'fastest_growing': None,
            'declining': []
        }
        
        for repo_name, monthly in trends.items():
            if not monthly:
                continue
            
            values = list(monthly.values())
            if len(values) < 3:
                continue
            
            # 计算趋势（简单线性回归斜率）
            import statistics
            n = len(values)
            x_mean = (n - 1) / 2
            y_mean = statistics.mean(values)
            
            numerator = sum((i - x_mean) * (values[i] - y_mean) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            
            if denominator != 0:
                slope = numerator / denominator
                
                # 检查是否下降趋势
                if slope < -1:
                    analysis['declining'].append(repo_name)
                elif slope > 1 and (analysis['fastest_growing'] is None or 
                                    slope > analysis.get('_fastest_slope', 0)):
                    analysis['fastest_growing'] = repo_name
                    analysis['_fastest_slope'] = slope
            
            # 计算一致性（标准差越小越一致）
            std_dev = statistics.stdev(values) if len(values) > 1 else 0
            if analysis['most_consistent'] is None:
                analysis['most_consistent'] = (repo_name, std_dev)
            elif std_dev < analysis['most_consistent'][1]:
                analysis['most_consistent'] = (repo_name, std_dev)
        
        # 清理临时数据
        if '_fastest_slope' in analysis:
            del analysis['_fastest_slope']
        if analysis['most_consistent']:
            analysis['most_consistent'] = analysis['most_consistent'][0]
        
        return analysis
    
    def get_comparison_data_for_visualization(self) -> Dict:
        """获取用于可视化的对比数据"""
        result = {
            'repos': [],
            'months': set(),
            'commits': {},
            'contributors': {},
            'issues': {},
            'prs': {}
        }
        
        for data in self.repos_data:
            repo_name = data.get('repo_info', {}).get('full_name', 'Unknown')
            short_name = repo_name.split('/')[-1]
            result['repos'].append(short_name)
            
            # Commits
            commit_data = data.get('commit_analysis', {})
            monthly = commit_data.get('monthly_distribution', {}).get('distribution', {})
            result['commits'][short_name] = monthly
            result['months'].update(monthly.keys())
        
        result['months'] = sorted(list(result['months']))
        return result