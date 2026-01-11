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


def main():
    """主入口函数"""
    cli()


if __name__ == '__main__':
    main()
