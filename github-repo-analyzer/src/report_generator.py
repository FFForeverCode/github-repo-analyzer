"""
报告生成模块

生成HTML和JSON格式的分析报告
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from jinja2 import Template
from rich.console import Console

console = Console()


# HTML报告模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ repo_name }} - GitHub仓库分析报告</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        header .subtitle {
            opacity: 0.8;
            font-size: 1.1em;
        }
        
        .repo-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #eee;
        }
        
        .stat-card {
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-card .value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-card .label {
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        main {
            padding: 40px;
        }
        
        section {
            margin-bottom: 50px;
        }
        
        section h2 {
            color: #1a1a2e;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 25px;
            font-size: 1.8em;
        }
        
        section h3 {
            color: #333;
            margin: 20px 0 15px 0;
            font-size: 1.3em;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .metric {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }
        
        .metric .value {
            font-size: 1.8em;
            font-weight: bold;
            color: #1a1a2e;
        }
        
        .metric .label {
            color: #555;
            font-size: 0.9em;
        }
        
        .chart-container {
            margin: 30px 0;
            text-align: center;
        }
        
        .chart-container img {
            max-width: 100%;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.95em;
        }
        
        .data-table th,
        .data-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        
        .data-table th {
            background: #667eea;
            color: white;
            font-weight: 600;
        }
        
        .data-table tr:nth-child(even) {
            background: #f8f9fa;
        }
        
        .data-table tr:hover {
            background: #e9ecef;
        }
        
        .highlight-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            margin: 20px 0;
        }
        
        .highlight-box h4 {
            margin-bottom: 15px;
            font-size: 1.2em;
        }
        
        .highlight-box ul {
            list-style: none;
            padding: 0;
        }
        
        .highlight-box li {
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }
        
        .highlight-box li:last-child {
            border-bottom: none;
        }
        
        footer {
            text-align: center;
            padding: 30px;
            background: #1a1a2e;
            color: white;
        }
        
        footer a {
            color: #667eea;
            text-decoration: none;
        }
        
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
            margin: 2px;
        }
        
        .badge-primary { background: #667eea; color: white; }
        .badge-success { background: #2ECC71; color: white; }
        .badge-warning { background: #F39C12; color: white; }
        .badge-danger { background: #E74C3C; color: white; }
        .badge-info { background: #3498DB; color: white; }
        
        @media (max-width: 768px) {
            header h1 { font-size: 1.8em; }
            main { padding: 20px; }
            .repo-info { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 {{ repo_name }}</h1>
            <p class="subtitle">GitHub仓库分析报告 | 生成时间: {{ analysis_time }}</p>
        </header>
        
        <!-- 仓库基本信息 -->
        <div class="repo-info">
            <div class="stat-card">
                <div class="value">⭐ {{ repo_info.stars | format_number }}</div>
                <div class="label">Stars</div>
            </div>
            <div class="stat-card">
                <div class="value">🍴 {{ repo_info.forks | format_number }}</div>
                <div class="label">Forks</div>
            </div>
            <div class="stat-card">
                <div class="value">👀 {{ repo_info.watchers | format_number }}</div>
                <div class="label">Watchers</div>
            </div>
            <div class="stat-card">
                <div class="value">🐛 {{ repo_info.open_issues | format_number }}</div>
                <div class="label">Open Issues</div>
            </div>
            <div class="stat-card">
                <div class="value">💻 {{ repo_info.language or 'N/A' }}</div>
                <div class="label">主要语言</div>
            </div>
            <div class="stat-card">
                <div class="value">📜 {{ repo_info.license or 'N/A' }}</div>
                <div class="label">许可证</div>
            </div>
        </div>
        
        <main>
            <!-- 仓库描述 -->
            {% if repo_info.description %}
            <section>
                <h2>📝 仓库描述</h2>
                <p style="font-size: 1.1em; color: #555;">{{ repo_info.description }}</p>
                {% if repo_info.topics %}
                <div style="margin-top: 15px;">
                    {% for topic in repo_info.topics %}
                    <span class="badge badge-info">{{ topic }}</span>
                    {% endfor %}
                </div>
                {% endif %}
            </section>
            {% endif %}
            
            <!-- Commit分析 -->
            {% if commit_analysis %}
            <section>
                <h2>📈 Commit分析</h2>
                
                <div class="metrics-grid">
                    <div class="metric">
                        <div class="value">{{ commit_analysis.total_commits | format_number }}</div>
                        <div class="label">总Commit数</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ commit_analysis.author_stats.total_authors }}</div>
                        <div class="label">贡献者数量</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ commit_analysis.commit_frequency.average_commits_per_day | round(1) }}</div>
                        <div class="label">日均Commit</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ commit_analysis.commit_frequency.max_streak_days }}</div>
                        <div class="label">最长连续提交天数</div>
                    </div>
                </div>
                
                <h3>⏰ 提交时间分布</h3>
                <div class="highlight-box">
                    <h4>关键发现</h4>
                    <ul>
                        <li>🕐 峰值提交时间: {{ commit_analysis.hourly_distribution.peak_hour }}:00 ({{ commit_analysis.hourly_distribution.peak_count }}次)</li>
                        <li>📅 最活跃日: {{ commit_analysis.weekday_distribution.peak_day }} ({{ commit_analysis.weekday_distribution.peak_count }}次)</li>
                        <li>💼 工作时间(9-18点)提交比例: {{ (commit_analysis.hourly_distribution.working_hours_ratio * 100) | round(1) }}%</li>
                        <li>🌙 周末提交比例: {{ (commit_analysis.weekday_distribution.weekend_ratio * 100) | round(1) }}%</li>
                    </ul>
                </div>
                
                {% if charts.hourly %}
                <div class="chart-container">
                    <img src="{{ charts.hourly }}" alt="每小时Commit分布">
                </div>
                {% endif %}
                
                {% if charts.weekday %}
                <div class="chart-container">
                    <img src="{{ charts.weekday }}" alt="每周Commit分布">
                </div>
                {% endif %}
                
                {% if charts.heatmap %}
                <div class="chart-container">
                    <img src="{{ charts.heatmap }}" alt="Commit活动热力图">
                </div>
                {% endif %}
                
                <h3>📊 代码变更统计</h3>
                <div class="metrics-grid">
                    <div class="metric">
                        <div class="value" style="color: #2ECC71;">+{{ commit_analysis.code_changes.total_additions | format_number }}</div>
                        <div class="label">总增加行数</div>
                    </div>
                    <div class="metric">
                        <div class="value" style="color: #E74C3C;">-{{ commit_analysis.code_changes.total_deletions | format_number }}</div>
                        <div class="label">总删除行数</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ commit_analysis.code_changes.average_additions_per_commit | round(1) }}</div>
                        <div class="label">平均增加/次</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ commit_analysis.code_changes.change_ratio | round(2) }}</div>
                        <div class="label">增/删比例</div>
                    </div>
                </div>
                
                <h3>🏆 Top贡献者</h3>
                {% if charts.authors %}
                <div class="chart-container">
                    <img src="{{ charts.authors }}" alt="Top贡献者">
                </div>
                {% endif %}
                
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>贡献者</th>
                            <th>Commit数</th>
                            <th>占比</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for author, commits in commit_analysis.author_stats.top_authors.items() %}
                        <tr>
                            <td>{{ loop.index }}</td>
                            <td>{{ author }}</td>
                            <td>{{ commits }}</td>
                            <td>{{ ((commits / commit_analysis.total_commits) * 100) | round(1) }}%</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </section>
            {% endif %}
            
            <!-- 贡献者分析 -->
            {% if contributor_analysis %}
            <section>
                <h2>👥 贡献者分析</h2>
                
                <div class="metrics-grid">
                    <div class="metric">
                        <div class="value">{{ contributor_analysis.total_contributors }}</div>
                        <div class="label">总贡献者数</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ contributor_analysis.contribution_distribution.total_contributions | format_number }}</div>
                        <div class="label">总贡献数</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ contributor_analysis.contribution_distribution.gini_coefficient | round(3) }}</div>
                        <div class="label">基尼系数</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ (contributor_analysis.contribution_distribution.pareto_ratio * 100) | round(1) }}%</div>
                        <div class="label">前20%贡献占比</div>
                    </div>
                </div>
                
                {% if charts.contribution_dist %}
                <div class="chart-container">
                    <img src="{{ charts.contribution_dist }}" alt="贡献分布">
                </div>
                {% endif %}
                
                <h3>🌍 贡献者多样性</h3>
                {% if contributor_analysis.contributor_diversity.company_distribution %}
                <h4>公司分布 (Top 10)</h4>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>公司</th>
                            <th>贡献者数</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for company, count in contributor_analysis.contributor_diversity.company_distribution.items() %}
                        <tr>
                            <td>{{ company }}</td>
                            <td>{{ count }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% endif %}
            </section>
            {% endif %}
            
            <!-- Issue分析 -->
            {% if issue_analysis %}
            <section>
                <h2>🐛 Issue分析</h2>
                
                <div class="metrics-grid">
                    <div class="metric">
                        <div class="value">{{ issue_analysis.total_issues }}</div>
                        <div class="label">总Issue数</div>
                    </div>
                    <div class="metric">
                        <div class="value" style="color: #3498DB;">{{ issue_analysis.open_issues }}</div>
                        <div class="label">Open</div>
                    </div>
                    <div class="metric">
                        <div class="value" style="color: #2ECC71;">{{ issue_analysis.closed_issues }}</div>
                        <div class="label">Closed</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ (issue_analysis.close_rate * 100) | round(1) }}%</div>
                        <div class="label">关闭率</div>
                    </div>
                </div>
                
                {% if charts.issue_status %}
                <div class="chart-container">
                    <img src="{{ charts.issue_status }}" alt="Issue状态">
                </div>
                {% endif %}
                
                {% if issue_analysis.resolution_time and 'error' not in issue_analysis.resolution_time %}
                <h3>⏱️ 解决时间统计</h3>
                <div class="metrics-grid">
                    <div class="metric">
                        <div class="value">{{ issue_analysis.resolution_time.average_hours | round(1) }}h</div>
                        <div class="label">平均解决时间</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ issue_analysis.resolution_time.median_hours | round(1) }}h</div>
                        <div class="label">中位数解决时间</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ issue_analysis.resolution_time.within_24_hours }}</div>
                        <div class="label">24h内解决</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ issue_analysis.resolution_time.over_month }}</div>
                        <div class="label">超过1月</div>
                    </div>
                </div>
                {% endif %}
                
                {% if charts.issue_labels %}
                <h3>🏷️ 标签分布</h3>
                <div class="chart-container">
                    <img src="{{ charts.issue_labels }}" alt="Issue标签">
                </div>
                {% endif %}
            </section>
            {% endif %}
            
            <!-- PR分析 -->
            {% if pr_analysis %}
            <section>
                <h2>🔀 Pull Request分析</h2>
                
                <div class="metrics-grid">
                    <div class="metric">
                        <div class="value">{{ pr_analysis.total_prs }}</div>
                        <div class="label">总PR数</div>
                    </div>
                    <div class="metric">
                        <div class="value" style="color: #2ECC71;">{{ pr_analysis.merged_prs }}</div>
                        <div class="label">已合并</div>
                    </div>
                    <div class="metric">
                        <div class="value" style="color: #3498DB;">{{ pr_analysis.open_prs }}</div>
                        <div class="label">打开中</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ (pr_analysis.merge_rate * 100) | round(1) }}%</div>
                        <div class="label">合并率</div>
                    </div>
                </div>
                
                {% if charts.pr_status %}
                <div class="chart-container">
                    <img src="{{ charts.pr_status }}" alt="PR状态">
                </div>
                {% endif %}
                
                {% if pr_analysis.merge_time and 'error' not in pr_analysis.merge_time %}
                <h3>⏱️ 合并时间统计</h3>
                <div class="metrics-grid">
                    <div class="metric">
                        <div class="value">{{ pr_analysis.merge_time.average_hours | round(1) }}h</div>
                        <div class="label">平均合并时间</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ pr_analysis.merge_time.median_hours | round(1) }}h</div>
                        <div class="label">中位数合并时间</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ pr_analysis.merge_time.within_24_hours }}</div>
                        <div class="label">24h内合并</div>
                    </div>
                </div>
                {% endif %}
                
                <h3>📝 代码审查统计</h3>
                <div class="metrics-grid">
                    <div class="metric">
                        <div class="value">{{ pr_analysis.code_review.average_review_comments | round(1) }}</div>
                        <div class="label">平均Review评论</div>
                    </div>
                    <div class="metric">
                        <div class="value">{{ (pr_analysis.code_review.review_rate * 100) | round(1) }}%</div>
                        <div class="label">有Review的PR比例</div>
                    </div>
                </div>
                
                {% if charts.pr_size %}
                <h3>📏 PR大小分布</h3>
                <div class="chart-container">
                    <img src="{{ charts.pr_size }}" alt="PR大小分布">
                </div>
                {% endif %}
            </section>
            {% endif %}
            
            <!-- 分析总结 -->
            <section>
                <h2>📋 分析总结</h2>
                <div class="highlight-box">
                    <h4>主要发现</h4>
                    <ul>
                        <li>📅 分析时间范围: {{ analysis_params.days }}天</li>
                        <li>📝 分析Commit数: {{ commit_analysis.total_commits if commit_analysis else 'N/A' }}</li>
                        <li>👥 活跃贡献者: {{ contributor_analysis.total_contributors if contributor_analysis else 'N/A' }}人</li>
                        {% if commit_analysis %}
                        <li>🏆 最活跃贡献者: {{ commit_analysis.author_stats.top_contributor }} ({{ commit_analysis.author_stats.top_contributor_commits }}次提交)</li>
                        {% endif %}
                        {% if issue_analysis %}
                        <li>🐛 Issue关闭率: {{ (issue_analysis.close_rate * 100) | round(1) }}%</li>
                        {% endif %}
                        {% if pr_analysis %}
                        <li>🔀 PR合并率: {{ (pr_analysis.merge_rate * 100) | round(1) }}%</li>
                        {% endif %}
                    </ul>
                </div>
            </section>
        </main>
        
        <footer>
            <p>由 <strong>GitHub仓库分析工具</strong> 自动生成</p>
            <p>项目地址: <a href="{{ repo_info.url }}" target="_blank">{{ repo_info.url }}</a></p>
            <p style="margin-top: 15px; opacity: 0.7;">开源软件基础课程大作业 | {{ analysis_time }}</p>
        </footer>
    </div>
</body>
</html>
"""


class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_html_report(self, analysis_result: Dict[str, Any],
                             chart_paths: List[str] = None) -> str:
        """
        生成HTML报告
        
        Args:
            analysis_result: 分析结果
            chart_paths: 图表文件路径列表
            
        Returns:
            生成的HTML文件路径
        """
        console.print("[cyan]正在生成HTML报告...[/cyan]")
        
        # 处理图表路径
        charts = {}
        if chart_paths:
            for path in chart_paths:
                if not path:
                    continue
                filename = os.path.basename(path)
                # 转换为相对路径
                rel_path = os.path.basename(path)
                
                if 'hourly' in filename:
                    charts['hourly'] = rel_path
                elif 'weekday' in filename:
                    charts['weekday'] = rel_path
                elif 'monthly_commits' in filename:
                    charts['monthly'] = rel_path
                elif 'top_authors' in filename:
                    charts['authors'] = rel_path
                elif 'contribution_dist' in filename:
                    charts['contribution_dist'] = rel_path
                elif 'issue_status' in filename:
                    charts['issue_status'] = rel_path
                elif 'issue_labels' in filename:
                    charts['issue_labels'] = rel_path
                elif 'pr_status' in filename:
                    charts['pr_status'] = rel_path
                elif 'pr_size' in filename:
                    charts['pr_size'] = rel_path
                elif 'heatmap' in filename:
                    charts['heatmap'] = rel_path
        
        # 自定义过滤器
        def format_number(value):
            if value is None:
                return 'N/A'
            if isinstance(value, (int, float)):
                if value >= 1000000:
                    return f"{value/1000000:.1f}M"
                elif value >= 1000:
                    return f"{value/1000:.1f}K"
                return str(int(value))
            return str(value)
        
        # 创建模板
        template = Template(HTML_TEMPLATE)
        template.globals['format_number'] = format_number
        
        # 准备模板数据
        repo_info = analysis_result.get('repo_info', {})
        repo_name = repo_info.get('full_name', 'Unknown Repository')
        
        # 渲染HTML
        html_content = template.render(
            repo_name=repo_name,
            analysis_time=analysis_result.get('analysis_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            repo_info=repo_info,
            commit_analysis=analysis_result.get('commit_analysis'),
            contributor_analysis=analysis_result.get('contributor_analysis'),
            issue_analysis=analysis_result.get('issue_analysis'),
            pr_analysis=analysis_result.get('pr_analysis'),
            analysis_params=analysis_result.get('analysis_params', {}),
            charts=charts
        )
        
        # 保存文件
        safe_repo_name = repo_name.replace('/', '_')
        filename = f"{safe_repo_name}_report.html"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        console.print(f"[green]✓ HTML报告已生成: {filepath}[/green]")
        return filepath
    
    def generate_json_report(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成JSON报告
        
        Args:
            analysis_result: 分析结果
            
        Returns:
            生成的JSON文件路径
        """
        console.print("[cyan]正在生成JSON报告...[/cyan]")
        
        # 创建一个用于JSON的副本，移除raw_data以减小文件大小
        result_copy = self._clean_for_json(analysis_result)
        
        repo_name = analysis_result.get('repo_info', {}).get('full_name', 'unknown')
        safe_repo_name = repo_name.replace('/', '_')
        filename = f"{safe_repo_name}_report.json"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result_copy, f, ensure_ascii=False, indent=2, default=str)
        
        console.print(f"[green]✓ JSON报告已生成: {filepath}[/green]")
        return filepath
    
    def _clean_for_json(self, data: Any) -> Any:
        """清理数据以便JSON序列化"""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                # 跳过raw_data字段以减小文件大小
                if key == 'raw_data':
                    continue
                result[key] = self._clean_for_json(value)
            return result
        elif isinstance(data, list):
            return [self._clean_for_json(item) for item in data]
        elif isinstance(data, datetime):
            return data.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return data
    
    def generate_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        生成文本摘要
        
        Args:
            analysis_result: 分析结果
            
        Returns:
            摘要文本
        """
        repo_info = analysis_result.get('repo_info', {})
        commit_analysis = analysis_result.get('commit_analysis', {})
        contributor_analysis = analysis_result.get('contributor_analysis', {})
        issue_analysis = analysis_result.get('issue_analysis', {})
        pr_analysis = analysis_result.get('pr_analysis', {})
        
        summary_lines = [
            "=" * 60,
            f"📊 GitHub仓库分析报告摘要",
            f"仓库: {repo_info.get('full_name', 'N/A')}",
            "=" * 60,
            "",
            "📌 仓库概况",
            f"  ⭐ Stars: {repo_info.get('stars', 'N/A')}",
            f"  🍴 Forks: {repo_info.get('forks', 'N/A')}",
            f"  💻 主要语言: {repo_info.get('language', 'N/A')}",
            f"  📜 许可证: {repo_info.get('license', 'N/A')}",
            "",
        ]
        
        if commit_analysis:
            summary_lines.extend([
                "📈 Commit统计",
                f"  总Commit数: {commit_analysis.get('total_commits', 'N/A')}",
                f"  活跃贡献者: {commit_analysis.get('author_stats', {}).get('total_authors', 'N/A')}",
                f"  峰值提交时间: {commit_analysis.get('hourly_distribution', {}).get('peak_hour', 'N/A')}:00",
                f"  最活跃日: {commit_analysis.get('weekday_distribution', {}).get('peak_day', 'N/A')}",
                "",
            ])
        
        if contributor_analysis:
            contrib_dist = contributor_analysis.get('contribution_distribution', {})
            summary_lines.extend([
                "👥 贡献者分析",
                f"  总贡献者: {contributor_analysis.get('total_contributors', 'N/A')}",
                f"  基尼系数: {contrib_dist.get('gini_coefficient', 'N/A'):.3f}" if isinstance(contrib_dist.get('gini_coefficient'), (int, float)) else f"  基尼系数: N/A",
                f"  前20%贡献占比: {contrib_dist.get('pareto_ratio', 0) * 100:.1f}%" if isinstance(contrib_dist.get('pareto_ratio'), (int, float)) else f"  前20%贡献占比: N/A",
                "",
            ])
        
        if issue_analysis:
            summary_lines.extend([
                "🐛 Issue统计",
                f"  总Issue数: {issue_analysis.get('total_issues', 'N/A')}",
                f"  Open/Closed: {issue_analysis.get('open_issues', 'N/A')}/{issue_analysis.get('closed_issues', 'N/A')}",
                f"  关闭率: {issue_analysis.get('close_rate', 0) * 100:.1f}%" if isinstance(issue_analysis.get('close_rate'), (int, float)) else f"  关闭率: N/A",
                "",
            ])
        
        if pr_analysis:
            summary_lines.extend([
                "🔀 PR统计",
                f"  总PR数: {pr_analysis.get('total_prs', 'N/A')}",
                f"  已合并: {pr_analysis.get('merged_prs', 'N/A')}",
                f"  合并率: {pr_analysis.get('merge_rate', 0) * 100:.1f}%" if isinstance(pr_analysis.get('merge_rate'), (int, float)) else f"  合并率: N/A",
                "",
            ])
        
        summary_lines.append("=" * 60)
        
        return "\n".join(summary_lines)
