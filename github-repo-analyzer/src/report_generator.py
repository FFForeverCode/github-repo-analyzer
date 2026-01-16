"""
报告生成模块

生成HTML和JSON格式的分析报告
已集成：仓库健康度诊断 (Repository Health Diagnosis)
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from jinja2 import Template
from rich.console import Console

console = Console()

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

        /* --- 新增：健康诊断卡片样式 --- */
        .health-dashboard {
            display: flex;
            align-items: center;
            background: #fff;
            margin: 30px 40px 10px 40px;
            padding: 30px;
            border-radius: 15px;
            border-left: 12px solid {{ health_diagnosis.color }};
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        }
        .health-score-ring {
            width: 110px; height: 110px;
            border-radius: 50%;
            background: {{ health_diagnosis.color }};
            color: white;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin-right: 35px;
            flex-shrink: 0;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .health-score-ring .score-val { font-size: 2.2em; font-weight: 800; line-height: 1; }
        .health-score-ring .score-label { font-size: 0.75em; margin-top: 5px; opacity: 0.9; }
        .health-info-body h3 { font-size: 1.6em; color: {{ health_diagnosis.color }}; margin-bottom: 8px; }
        .health-info-body .diagnosis-text { color: #555; margin-bottom: 12px; font-size: 1.05em; }
        .risk-tags-container { display: flex; flex-wrap: wrap; gap: 8px; }
        .risk-tag {
            padding: 4px 12px; border-radius: 6px; font-size: 0.85em;
            background: #fff5f5; color: #e53e3e; border: 1px solid #feb2b2;
            font-weight: 500;
        }
        /* ------------------------- */
        
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
            .health-dashboard { flex-direction: column; text-align: center; padding: 20px; }
            .health-score-ring { margin-right: 0; margin-bottom: 20px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 {{ repo_name }}</h1>
            <p class="subtitle">GitHub仓库分析报告 | 生成时间: {{ analysis_time }}</p>
        </header>
        
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

        <div class="health-dashboard">
            <div class="health-score-ring">
                <div class="score-val">{{ health_diagnosis.score }}</div>
                <div class="score-label">健康评分</div>
            </div>
            <div class="health-info-body">
                <h3>项目健康诊断：{{ health_diagnosis.grade }}</h3>
                <p class="diagnosis-text">{{ health_diagnosis.summary }}</p>
                <div class="risk-tags-container">
                    {% for risk in health_diagnosis.risks %}
                    <div class="risk-tag">⚠️ {{ risk }}</div>
                    {% endfor %}
                    {% if not health_diagnosis.risks %}
                    <div class="risk-tag" style="background: #f0fff4; color: #2f855a; border-color: #9ae6b4;">✅ 未发现明显运行风险</div>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <main>
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
    """报告生成器 (完整集成版)"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _calculate_health(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        核心补充算法：基于多维数据进行健康评分
        """
        score = 65  # 基础分
        risks = []
        
        commit_a = result.get('commit_analysis', {})
        issue_a = result.get('issue_analysis', {})
        pr_a = result.get('pr_analysis', {})
        contrib_a = result.get('contributor_analysis', {})
        
        # 1. 活跃度
        freq = commit_a.get('commit_frequency', {}).get('average_commits_per_day', 0)
        if freq > 0.5: score += 10
        elif freq < 0.1: 
            score -= 15
            risks.append("开发活动极不活跃")

        # 2. 响应度
        i_rate = issue_a.get('close_rate', 0)
        if i_rate > 0.7: score += 10
        elif i_rate < 0.2: 
            score -= 10
            risks.append("Issue 长期未处理堆积")

        # 3. 集中度风险
        gini = contrib_a.get('contribution_distribution', {}).get('gini_coefficient', 0)
        if gini > 0.85:
            score -= 20
            risks.append("项目极度依赖单一开发者 (Bus Factor 低)")

        # 4. PR 吞吐
        p_rate = pr_a.get('merge_rate', 0)
        if p_rate < 0.3:
            risks.append("PR 合并通过率低，可能存在社区协作障碍")

        # 结果包装
        score = max(0, min(100, score))
        if score >= 85: grade, color = "极佳 (Excellent)", "#2ECC71"
        elif score >= 70: grade, color = "健康 (Healthy)", "#3498DB"
        elif score >= 50: grade, color = "一般 (Fair)", "#F39C12"
        else: grade, color = "预警 (At Risk)", "#E74C3C"

        return {
            "score": int(score),
            "grade": grade,
            "color": color,
            "risks": risks,
            "summary": f"当前仓库健康度积分为 {int(score)}。分析显示该项目{'处于活跃且健康的协作状态' if score >= 70 else '可能存在维护力度不足或社区化程度低的问题'}。"
        }
    
    def generate_html_report(self, analysis_result: Dict[str, Any],
                             chart_paths: List[str] = None) -> str:
        """生成HTML报告"""
        console.print("[cyan]正在生成完整HTML报告...[/cyan]")
        
        # 处理图表路径（完全保留原逻辑）
        charts = {}
        if chart_paths:
            for path in chart_paths:
                if not path: continue
                filename = os.path.basename(path)
                rel_path = os.path.basename(path)
                
                if 'hourly' in filename: charts['hourly'] = rel_path
                elif 'weekday' in filename: charts['weekday'] = rel_path
                elif 'monthly_commits' in filename: charts['monthly'] = rel_path
                elif 'top_authors' in filename: charts['authors'] = rel_path
                elif 'contribution_dist' in filename: charts['contribution_dist'] = rel_path
                elif 'issue_status' in filename: charts['issue_status'] = rel_path
                elif 'issue_labels' in filename: charts['issue_labels'] = rel_path
                elif 'pr_status' in filename: charts['pr_status'] = rel_path
                elif 'pr_size' in filename: charts['pr_size'] = rel_path
                elif 'heatmap' in filename: charts['heatmap'] = rel_path
        
        # 计算健康诊断
        health = self._calculate_health(analysis_result)
        
        # 自定义过滤器（完全保留原逻辑）
        def format_number(value):
            if value is None: return 'N/A'
            if isinstance(value, (int, float)):
                if value >= 1000000: return f"{value/1000000:.1f}M"
                elif value >= 1000: return f"{value/1000:.1f}K"
                return str(int(value))
            return str(value)
        
        template = Template(HTML_TEMPLATE)
        template.globals['format_number'] = format_number
        
        repo_info = analysis_result.get('repo_info', {})
        repo_name = repo_info.get('full_name', 'Unknown Repository')
        
        html_content = template.render(
            repo_name=repo_name,
            analysis_time=analysis_result.get('analysis_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            repo_info=repo_info,
            commit_analysis=analysis_result.get('commit_analysis'),
            contributor_analysis=analysis_result.get('contributor_analysis'),
            issue_analysis=analysis_result.get('issue_analysis'),
            pr_analysis=analysis_result.get('pr_analysis'),
            analysis_params=analysis_result.get('analysis_params', {}),
            charts=charts,
            health_diagnosis=health  # 注入健康数据
        )
        
        safe_repo_name = repo_name.replace('/', '_')
        filepath = os.path.join(self.output_dir, f"{safe_repo_name}_report.html")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        console.print(f"[green]✓ HTML报告已生成 (已集成健康诊断): {filepath}[/green]")
        return filepath
    
    def generate_json_report(self, analysis_result: Dict[str, Any]) -> str:
        """生成JSON报告"""
        console.print("[cyan]正在生成JSON报告...[/cyan]")
        result_copy = self._clean_for_json(analysis_result)
        # JSON 报告也加入健康评分数据
        result_copy['health_diagnosis'] = self._calculate_health(analysis_result)
        
        repo_name = analysis_result.get('repo_info', {}).get('full_name', 'unknown')
        safe_repo_name = repo_name.replace('/', '_')
        filepath = os.path.join(self.output_dir, f"{safe_repo_name}_report.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result_copy, f, ensure_ascii=False, indent=2, default=str)
        
        return filepath
    
    def _clean_for_json(self, data: Any) -> Any:
        """清理数据以便JSON序列化 (保留原逻辑)"""
        if isinstance(data, dict):
            return {k: self._clean_for_json(v) for k, v in data.items() if k != 'raw_data'}
        elif isinstance(data, list):
            return [self._clean_for_json(item) for item in data]
        elif isinstance(data, datetime):
            return data.strftime('%Y-%m-%d %H:%M:%S')
        return data

    def generate_summary(self, analysis_result: Dict[str, Any]) -> str:
        """生成带诊断信息的文本摘要"""
        repo_info = analysis_result.get('repo_info', {})
        health = self._calculate_health(analysis_result)
        
        summary = f"============================================================\n"
        summary += f"📊 GitHub仓库分析报告摘要\n"
        summary += f"仓库: {repo_info.get('full_name', 'N/A')}\n"
        summary += f"健康评价: {health['grade']} (得分: {health['score']})\n"
        if health['risks']:
            summary += f"风险点: {', '.join(health['risks'])}\n"
        summary += f"============================================================\n"
        return summary