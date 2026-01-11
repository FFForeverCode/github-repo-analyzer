#!/usr/bin/env python3
"""
示例脚本 - 展示如何使用GitHub仓库分析工具
"""

import os
import sys

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.github_client import GitHubClient
from src.analyzer import RepoAnalyzer, CommitAnalyzer, ContributorAnalyzer
from src.visualizer import ChartGenerator
from src.report_generator import ReportGenerator


def example_basic_analysis():
    """基础分析示例"""
    print("\n" + "="*60)
    print("示例1: 基础仓库分析")
    print("="*60 + "\n")
    
    # 初始化客户端
    client = GitHubClient()
    
    # 获取仓库基本信息
    repo_name = "pallets/flask"  # 使用一个相对小的仓库作为示例
    print(f"正在获取仓库信息: {repo_name}")
    
    repo_info = client.get_repo_info(repo_name)
    
    print(f"\n仓库: {repo_info['full_name']}")
    print(f"描述: {repo_info['description']}")
    print(f"Stars: {repo_info['stars']:,}")
    print(f"Forks: {repo_info['forks']:,}")
    print(f"主要语言: {repo_info['language']}")
    print(f"许可证: {repo_info['license']}")
    print(f"URL: {repo_info['url']}")


def example_commit_analysis():
    """Commit分析示例"""
    print("\n" + "="*60)
    print("示例2: Commit模式分析")
    print("="*60 + "\n")
    
    client = GitHubClient()
    analyzer = CommitAnalyzer(client)
    
    repo_name = "pallets/flask"
    print(f"正在分析 {repo_name} 的commit模式（最近90天，最多100个commit）...")
    
    result = analyzer.analyze_commit_patterns(
        repo_name=repo_name,
        days=90,
        max_commits=100
    )
    
    if 'error' not in result:
        print(f"\n分析结果:")
        print(f"  总Commit数: {result['total_commits']}")
        print(f"  分析时间范围: {result['date_range']['start']} - {result['date_range']['end']}")
        print(f"  贡献者数量: {result['author_stats']['total_authors']}")
        print(f"  峰值提交时间: {result['hourly_distribution']['peak_hour']}:00")
        print(f"  最活跃日: {result['weekday_distribution']['peak_day']}")
        print(f"  代码增加行数: {result['code_changes']['total_additions']:,}")
        print(f"  代码删除行数: {result['code_changes']['total_deletions']:,}")
    else:
        print(f"分析失败: {result['error']}")


def example_contributor_analysis():
    """贡献者分析示例"""
    print("\n" + "="*60)
    print("示例3: 贡献者活跃度分析")
    print("="*60 + "\n")
    
    client = GitHubClient()
    analyzer = ContributorAnalyzer(client)
    
    repo_name = "pallets/flask"
    print(f"正在分析 {repo_name} 的贡献者（最多50人）...")
    
    result = analyzer.analyze_contributors(
        repo_name=repo_name,
        max_contributors=50
    )
    
    if 'error' not in result:
        print(f"\n分析结果:")
        print(f"  总贡献者数: {result['total_contributors']}")
        
        contrib_dist = result['contribution_distribution']
        print(f"  总贡献数: {contrib_dist['total_contributions']:,}")
        print(f"  基尼系数: {contrib_dist['gini_coefficient']:.3f}")
        print(f"  前20%贡献者占比: {contrib_dist['pareto_ratio']*100:.1f}%")
        
        print(f"\n  Top 5 贡献者:")
        for i, contrib in enumerate(result['top_contributors'][:5], 1):
            print(f"    {i}. {contrib['login']}: {contrib['contributions']} 次贡献")
    else:
        print(f"分析失败: {result['error']}")


def example_full_analysis():
    """完整分析示例"""
    print("\n" + "="*60)
    print("示例4: 完整仓库分析并生成报告")
    print("="*60 + "\n")
    
    client = GitHubClient()
    analyzer = RepoAnalyzer(client)
    
    repo_name = "pallets/click"  # 使用click作为示例
    output_dir = "output"
    
    print(f"正在对 {repo_name} 进行完整分析...")
    print("（这可能需要几分钟时间）\n")
    
    # 执行完整分析（使用较小的参数以加快速度）
    result = analyzer.full_analysis(
        repo_name=repo_name,
        days=180,
        max_commits=200,
        max_contributors=50,
        max_issues=100,
        max_prs=100,
        analyze_issues=True,
        analyze_prs=True
    )
    
    # 生成图表
    print("\n正在生成图表...")
    chart_generator = ChartGenerator(output_dir=output_dir)
    chart_paths = chart_generator.generate_all_charts(result, repo_name)
    
    # 生成报告
    print("正在生成报告...")
    report_generator = ReportGenerator(output_dir=output_dir)
    html_path = report_generator.generate_html_report(result, chart_paths)
    json_path = report_generator.generate_json_report(result)
    
    # 打印摘要
    summary = report_generator.generate_summary(result)
    print("\n" + summary)
    
    print(f"\n生成的文件:")
    print(f"  HTML报告: {html_path}")
    print(f"  JSON报告: {json_path}")
    print(f"  图表文件: {len(chart_paths)} 个")


def example_search_repos():
    """搜索仓库示例"""
    print("\n" + "="*60)
    print("示例5: 搜索热门Python仓库")
    print("="*60 + "\n")
    
    client = GitHubClient()
    
    query = "language:python stars:>10000"
    print(f"搜索条件: {query}\n")
    
    results = client.search_repositories(query, sort='stars', max_count=10)
    
    print("Top 10 Python 仓库 (按Stars排序):\n")
    for i, repo in enumerate(results, 1):
        print(f"{i}. {repo['full_name']}")
        print(f"   ⭐ {repo['stars']:,} Stars")
        print(f"   📝 {repo['description'][:60]}..." if repo['description'] and len(repo['description']) > 60 else f"   📝 {repo['description'] or 'N/A'}")
        print()


def main():
    """主函数"""
    print("\n" + "="*60)
    print("  GitHub仓库分析工具 - 示例演示")
    print("="*60)
    
    # 检查Token
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print("\n⚠️  警告: 未设置GITHUB_TOKEN环境变量")
        print("   请设置环境变量或创建.env文件")
        print("   示例: export GITHUB_TOKEN=your_token_here")
        print("\n   继续运行可能会受到API速率限制...\n")
    
    # 运行示例
    try:
        # 选择要运行的示例
        print("\n请选择要运行的示例:")
        print("1. 基础仓库分析")
        print("2. Commit模式分析")
        print("3. 贡献者活跃度分析")
        print("4. 完整分析并生成报告")
        print("5. 搜索热门仓库")
        print("6. 运行所有示例")
        print("0. 退出")
        
        choice = input("\n请输入选项 (0-6): ").strip()
        
        if choice == '1':
            example_basic_analysis()
        elif choice == '2':
            example_commit_analysis()
        elif choice == '3':
            example_contributor_analysis()
        elif choice == '4':
            example_full_analysis()
        elif choice == '5':
            example_search_repos()
        elif choice == '6':
            example_basic_analysis()
            example_commit_analysis()
            example_contributor_analysis()
            example_search_repos()
            # 完整分析比较耗时，单独确认
            run_full = input("\n是否运行完整分析（耗时较长）? (y/n): ").strip().lower()
            if run_full == 'y':
                example_full_analysis()
        elif choice == '0':
            print("\n再见！")
            return
        else:
            print("\n无效选项，退出。")
            return
        
        print("\n" + "="*60)
        print("  示例运行完成！")
        print("="*60 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n用户中断，退出。")
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
