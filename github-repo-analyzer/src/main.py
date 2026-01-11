#!/usr/bin/env python3
"""
GitHub仓库分析工具 - 命令行入口

使用方法:
    python main.py <repo_name> [options]
    
示例:
    python main.py facebook/react
    python main.py tensorflow/tensorflow --days 180 --max-commits 500
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.github_client import GitHubClient
from src.analyzer import RepoAnalyzer
from src.visualizer import ChartGenerator
from src.report_generator import ReportGenerator
from src.config import get_config

console = Console()


def print_banner():
    """打印程序横幅"""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   📊  GitHub 仓库分析工具  📊                                 ║
║                                                               ║
║   分析开源项目的Commit模式、贡献者活跃度等                    ║
║                                                               ║
║   开源软件基础课程大作业                                      ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold blue")


@click.group()
def cli():
    """GitHub仓库分析工具 - 分析开源项目的commit模式、贡献者活跃度等"""
    pass


@cli.command()
@click.argument('repo_name')
@click.option('--days', '-d', default=365, help='分析的时间范围（天数），默认365天')
@click.option('--max-commits', '-c', default=1000, help='最大获取的commit数量，默认1000')
@click.option('--max-contributors', '-u', default=100, help='最大获取的贡献者数量，默认100')
@click.option('--max-issues', '-i', default=500, help='最大获取的issue数量，默认500')
@click.option('--max-prs', '-p', default=300, help='最大获取的PR数量，默认300')
@click.option('--no-issues', is_flag=True, help='不分析issues')
@click.option('--no-prs', is_flag=True, help='不分析pull requests')
@click.option('--no-charts', is_flag=True, help='不生成图表')
@click.option('--output', '-o', default='output', help='输出目录，默认output')
@click.option('--token', '-t', help='GitHub Personal Access Token')
def analyze(repo_name, days, max_commits, max_contributors, max_issues, 
            max_prs, no_issues, no_prs, no_charts, output, token):
    """
    分析指定的GitHub仓库
    
    REPO_NAME: 仓库全名，格式为 owner/repo，例如 facebook/react
    """
    print_banner()
    
    try:
        # 初始化客户端
        client = GitHubClient(token=token)
        
        # 显示API限制信息
        rate_limit = client.get_rate_limit()
        console.print(Panel(
            f"API限制: {rate_limit['core']['remaining']}/{rate_limit['core']['limit']} "
            f"(重置时间: {rate_limit['core']['reset_time']})",
            title="📡 GitHub API 状态"
        ))
        
        # 执行分析
        analyzer = RepoAnalyzer(client)
        result = analyzer.full_analysis(
            repo_name=repo_name,
            days=days,
            max_commits=max_commits,
            max_contributors=max_contributors,
            max_issues=max_issues,
            max_prs=max_prs,
            analyze_issues=not no_issues,
            analyze_prs=not no_prs
        )
        
        # 生成图表
        chart_paths = []
        if not no_charts:
            chart_generator = ChartGenerator(output_dir=output)
            chart_paths = chart_generator.generate_all_charts(result, repo_name)
        
        # 生成报告
        report_generator = ReportGenerator(output_dir=output)
        html_path = report_generator.generate_html_report(result, chart_paths)
        json_path = report_generator.generate_json_report(result)
        
        # 打印摘要
        summary = report_generator.generate_summary(result)
        console.print("\n")
        console.print(Panel(summary, title="📋 分析摘要", border_style="green"))
        
        # 显示输出文件
        console.print("\n[bold green]✅ 分析完成！[/bold green]")
        console.print(f"\n📁 输出文件:")
        console.print(f"   📄 HTML报告: {html_path}")
        console.print(f"   📄 JSON报告: {json_path}")
        if chart_paths:
            console.print(f"   📊 图表文件: {len(chart_paths)} 个")
        
    except ValueError as e:
        console.print(f"\n[red]❌ 配置错误: {e}[/red]")
        console.print("[yellow]请设置 GITHUB_TOKEN 环境变量或使用 --token 参数[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ 分析失败: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument('query')
@click.option('--limit', '-l', default=10, help='返回结果数量，默认10')
@click.option('--sort', '-s', default='stars', 
              type=click.Choice(['stars', 'forks', 'updated']),
              help='排序方式，默认按stars')
@click.option('--token', '-t', help='GitHub Personal Access Token')
def search(query, limit, sort, token):
    """
    搜索GitHub仓库
    
    QUERY: 搜索关键词，例如 "machine learning language:python"
    """
    print_banner()
    
    try:
        client = GitHubClient(token=token)
        
        console.print(f"\n[cyan]搜索: {query}[/cyan]")
        results = client.search_repositories(query, sort=sort, max_count=limit)
        
        if not results:
            console.print("[yellow]未找到匹配的仓库[/yellow]")
            return
        
        # 创建表格
        table = Table(title=f"搜索结果 (共 {len(results)} 个)")
        table.add_column("仓库", style="cyan", no_wrap=True)
        table.add_column("Stars", style="yellow", justify="right")
        table.add_column("语言", style="green")
        table.add_column("描述", max_width=50)
        
        for repo in results:
            table.add_row(
                repo['full_name'],
                str(repo['stars']),
                repo['language'] or 'N/A',
                (repo['description'] or '')[:50] + '...' if repo['description'] and len(repo['description']) > 50 else (repo['description'] or 'N/A')
            )
        
        console.print(table)
        console.print("\n[dim]使用 'python main.py analyze <仓库名>' 来分析某个仓库[/dim]")
        
    except Exception as e:
        console.print(f"\n[red]❌ 搜索失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--token', '-t', help='GitHub Personal Access Token')
def rate_limit(token):
    """查看GitHub API速率限制状态"""
    try:
        client = GitHubClient(token=token)
        limit = client.get_rate_limit()
        
        console.print("\n[bold]GitHub API 速率限制状态[/bold]\n")
        
        table = Table()
        table.add_column("类型", style="cyan")
        table.add_column("剩余", style="yellow", justify="right")
        table.add_column("限制", style="green", justify="right")
        table.add_column("重置时间", style="dim")
        
        table.add_row(
            "Core API",
            str(limit['core']['remaining']),
            str(limit['core']['limit']),
            limit['core']['reset_time']
        )
        table.add_row(
            "Search API",
            str(limit['search']['remaining']),
            str(limit['search']['limit']),
            limit['search']['reset_time']
        )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"\n[red]❌ 获取失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('repo_name')
@click.option('--token', '-t', help='GitHub Personal Access Token')
def info(repo_name, token):
    """
    查看仓库基本信息
    
    REPO_NAME: 仓库全名，格式为 owner/repo
    """
    try:
        client = GitHubClient(token=token)
        repo_info = client.get_repo_info(repo_name)
        
        console.print(f"\n[bold cyan]📦 {repo_info['full_name']}[/bold cyan]\n")
        
        if repo_info['description']:
            console.print(f"[dim]{repo_info['description']}[/dim]\n")
        
        table = Table(show_header=False, box=None)
        table.add_column("属性", style="cyan")
        table.add_column("值", style="white")
        
        table.add_row("⭐ Stars", f"{repo_info['stars']:,}")
        table.add_row("🍴 Forks", f"{repo_info['forks']:,}")
        table.add_row("👀 Watchers", f"{repo_info['watchers']:,}")
        table.add_row("🐛 Open Issues", f"{repo_info['open_issues']:,}")
        table.add_row("💻 语言", repo_info['language'] or 'N/A')
        table.add_row("📜 许可证", repo_info['license'] or 'N/A')
        table.add_row("🔗 URL", repo_info['url'])
        table.add_row("📅 创建时间", str(repo_info['created_at']))
        table.add_row("📅 最后更新", str(repo_info['updated_at']))
        
        console.print(table)
        
        if repo_info['topics']:
            console.print(f"\n[bold]标签:[/bold] {', '.join(repo_info['topics'])}")
        
    except Exception as e:
        console.print(f"\n[red]❌ 获取失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('repos', nargs=-1, required=True)
@click.option('--output', '-o', default='output', help='输出目录')
@click.option('--format', '-f', default='excel', 
              type=click.Choice(['csv', 'excel', 'markdown', 'pdf']),
              help='导出格式')
@click.option('--token', '-t', help='GitHub Personal Access Token')
def compare(repos, output, format, token):
    """
    对比多个GitHub仓库
    
    REPOS: 多个仓库名，格式为 owner/repo，用空格分隔
    
    示例: python main.py compare facebook/react vuejs/vue angular/angular
    """
    print_banner()
    
    if len(repos) < 2:
        console.print("[red]❌ 至少需要2个仓库进行比较[/red]")
        sys.exit(1)
    
    try:
        from src.comparator import RepoComparator, BenchmarkAnalyzer
        from src.exporter import ExportManager
        
        client = GitHubClient(token=token)
        analyzer = RepoAnalyzer(client)
        comparator = RepoComparator()
        
        console.print(f"\n[cyan]正在分析 {len(repos)} 个仓库...[/cyan]\n")
        
        # 分析每个仓库
        results = []
        for repo_name in repos:
            console.print(f"[dim]分析中: {repo_name}[/dim]")
            try:
                result = analyzer.full_analysis(
                    repo_name=repo_name,
                    days=365,
                    max_commits=500,
                    max_contributors=50,
                    max_issues=200,
                    max_prs=100
                )
                comparator.add_repo(result)
                results.append(result)
            except Exception as e:
                console.print(f"[yellow]⚠ {repo_name} 分析失败: {e}[/yellow]")
        
        if len(results) < 2:
            console.print("[red]❌ 成功分析的仓库不足2个[/red]")
            sys.exit(1)
        
        # 执行比较
        comparison = comparator.compare()
        
        # 打印比较结果
        comparator.print_comparison_table()
        comparator.print_rankings()
        comparator.print_recommendations()
        
        # 导出结果
        export_manager = ExportManager(output)
        
        # 导出比较JSON
        comparator.export_comparison(output)
        
        console.print(f"\n[bold green]✅ 对比分析完成！[/bold green]")
        console.print(f"[dim]结果已保存到 {output} 目录[/dim]")
        
    except ImportError as e:
        console.print(f"[red]❌ 模块导入失败: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ 对比分析失败: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument('repo_name')
@click.option('--periods', '-p', default=6, help='预测周期数（月），默认6')
@click.option('--output', '-o', default='output', help='输出目录')
@click.option('--token', '-t', help='GitHub Personal Access Token')
def predict(repo_name, periods, output, token):
    """
    预测仓库未来趋势
    
    REPO_NAME: 仓库全名，格式为 owner/repo
    
    示例: python main.py predict facebook/react --periods 12
    """
    print_banner()
    
    try:
        from src.predictor import ProjectHealthPredictor, SeasonalAnalyzer, AnomalyDetector
        
        client = GitHubClient(token=token)
        analyzer = RepoAnalyzer(client)
        
        console.print(f"\n[cyan]正在分析 {repo_name} 并预测趋势...[/cyan]\n")
        
        # 分析仓库
        result = analyzer.full_analysis(
            repo_name=repo_name,
            days=730,  # 获取2年数据以提高预测准确性
            max_commits=2000
        )
        
        # 趋势预测
        predictor = ProjectHealthPredictor()
        predictions = predictor.predict_project_health(result, periods)
        
        # 打印预测报告
        predictor.print_prediction_report(predictions, repo_name)
        
        # 季节性分析
        console.print("\n[bold]📅 季节性分析[/bold]")
        seasonal_analyzer = SeasonalAnalyzer()
        commit_data = result.get('commit_analysis', {})
        monthly = commit_data.get('monthly_distribution', {}).get('distribution', {})
        
        if monthly:
            seasonality = seasonal_analyzer.analyze_seasonality(monthly)
            console.print(f"  是否有季节性: {'是' if seasonality['has_seasonality'] else '否'}")
            console.print(f"  变异系数: {seasonality['coefficient_of_variation']}")
            if seasonality['peak_months']:
                console.print(f"  高峰月份: {', '.join(seasonality['peak_months'])}")
            console.print(f"  模式描述: {seasonality['pattern_description']}")
        
        # 异常检测
        console.print("\n[bold]🔍 异常检测[/bold]")
        detector = AnomalyDetector()
        if monthly:
            anomalies = detector.detect_anomalies(
                list(monthly.values()), 
                list(monthly.keys())
            )
            if anomalies['has_anomalies']:
                console.print(f"  发现 {len(anomalies['anomalies'])} 个异常点:")
                for a in anomalies['anomalies'][:5]:
                    console.print(f"    • {a.get('label', a['index'])}: {a['value']} (Z-score: {a['z_score']}, 类型: {a['type']})")
            else:
                console.print("  未发现明显异常")
        
        console.print(f"\n[bold green]✅ 预测分析完成！[/bold green]")
        
    except ImportError as e:
        console.print(f"[red]❌ 模块导入失败: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ 预测分析失败: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument('repo_name')
@click.option('--format', '-f', default='excel',
              type=click.Choice(['csv', 'excel', 'markdown', 'pdf', 'all']),
              help='导出格式，默认excel')
@click.option('--output', '-o', default='output', help='输出目录')
@click.option('--token', '-t', help='GitHub Personal Access Token')
def export(repo_name, format, output, token):
    """
    分析并导出报告到指定格式
    
    REPO_NAME: 仓库全名，格式为 owner/repo
    
    示例: python main.py export facebook/react --format pdf
    """
    print_banner()
    
    try:
        from src.exporter import ExportManager
        
        client = GitHubClient(token=token)
        analyzer = RepoAnalyzer(client)
        
        console.print(f"\n[cyan]正在分析 {repo_name}...[/cyan]\n")
        
        # 分析仓库
        result = analyzer.full_analysis(repo_name=repo_name)
        
        # 导出
        export_manager = ExportManager(output)
        safe_name = repo_name.replace('/', '_')
        
        if format == 'all':
            console.print("[cyan]导出所有格式...[/cyan]")
            files = export_manager.export_all(result, safe_name)
            console.print("\n[bold green]✅ 导出完成！[/bold green]")
            for fmt, path in files.items():
                if path:
                    console.print(f"  📄 {fmt.upper()}: {path}")
        else:
            filepath = export_manager.export(result, safe_name, format)
            console.print(f"\n[bold green]✅ 导出完成！[/bold green]")
            console.print(f"  📄 文件: {filepath}")
        
    except ImportError as e:
        console.print(f"[red]❌ 模块导入失败: {e}[/red]")
        console.print("[yellow]请确保已安装相关依赖: pip install openpyxl reportlab pandas[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ 导出失败: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument('repo_name')
@click.option('--token', '-t', help='GitHub Personal Access Token')
def benchmark(repo_name, token):
    """
    对仓库进行基准测试分析
    
    REPO_NAME: 仓库全名，格式为 owner/repo
    
    与同规模项目的行业标准进行对比
    """
    print_banner()
    
    try:
        from src.comparator import BenchmarkAnalyzer
        
        client = GitHubClient(token=token)
        analyzer = RepoAnalyzer(client)
        
        console.print(f"\n[cyan]正在分析 {repo_name} 并进行基准测试...[/cyan]\n")
        
        # 分析仓库
        result = analyzer.full_analysis(repo_name=repo_name)
        
        # 基准分析
        benchmark_analyzer = BenchmarkAnalyzer()
        benchmark_result = benchmark_analyzer.analyze(result)
        benchmark_analyzer.print_benchmark_report(benchmark_result)
        
        console.print(f"\n[bold green]✅ 基准测试完成！[/bold green]")
        
    except ImportError as e:
        console.print(f"[red]❌ 模块导入失败: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ 基准测试失败: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.option('--strategy', '-s', default='file',
              type=click.Choice(['memory', 'file']),
              help='缓存策略，默认file')
@click.option('--action', '-a', default='stats',
              type=click.Choice(['stats', 'clear']),
              help='操作：stats查看统计，clear清空缓存')
def cache(strategy, action):
    """
    管理API请求缓存
    
    示例: 
        python main.py cache --action stats
        python main.py cache --action clear
    """
    try:
        from src.cache_manager import CacheManager
        
        cache_manager = CacheManager(strategy=strategy)
        
        if action == 'stats':
            stats = cache_manager.get_stats()
            console.print("\n[bold]📊 缓存统计[/bold]\n")
            
            table = Table()
            table.add_column("指标", style="cyan")
            table.add_column("值", style="white")
            
            for key, value in stats.items():
                table.add_row(str(key), str(value))
            
            console.print(table)
        
        elif action == 'clear':
            cache_manager.clear()
            console.print("[green]✅ 缓存已清空[/green]")
        
    except ImportError as e:
        console.print(f"[red]❌ 模块导入失败: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ 缓存操作失败: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument('repo_name')
@click.option('--output', '-o', default='output', help='输出目录')
@click.option('--token', '-t', help='GitHub Personal Access Token')
def dashboard(repo_name, output, token):
    """
    生成项目综合仪表盘
    
    REPO_NAME: 仓库全名，格式为 owner/repo
    
    生成包含所有关键指标的可视化仪表盘
    """
    print_banner()
    
    try:
        from src.visualizer import DashboardGenerator
        
        client = GitHubClient(token=token)
        analyzer = RepoAnalyzer(client)
        
        console.print(f"\n[cyan]正在分析 {repo_name} 并生成仪表盘...[/cyan]\n")
        
        # 分析仓库
        result = analyzer.full_analysis(repo_name=repo_name)
        
        # 生成仪表盘
        dashboard_gen = DashboardGenerator(output_dir=output)
        filepath = dashboard_gen.generate_project_dashboard(result, repo_name)
        
        console.print(f"\n[bold green]✅ 仪表盘生成完成！[/bold green]")
        console.print(f"  📊 文件: {filepath}")
        
    except ImportError as e:
        console.print(f"[red]❌ 模块导入失败: {e}[/red]")
        console.print("[yellow]请确保已安装matplotlib和seaborn[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ 仪表盘生成失败: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)


def main():
    """主入口函数"""
    cli()


if __name__ == '__main__':
    main()
