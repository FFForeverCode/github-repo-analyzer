"""
可视化模块

提供数据可视化功能，生成图表
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np
import pandas as pd
from rich.console import Console

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

console = Console()


class ChartGenerator:
    """图表生成器"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # 设置seaborn样式
        sns.set_style("whitegrid")
        sns.set_palette("husl")
    
    def generate_all_charts(self, analysis_result: Dict[str, Any], 
                           repo_name: str) -> List[str]:
        """
        生成所有图表
        
        Args:
            analysis_result: 分析结果
            repo_name: 仓库名
            
        Returns:
            生成的图表文件路径列表
        """
        charts = []
        safe_repo_name = repo_name.replace('/', '_')
        
        console.print("[cyan]正在生成可视化图表...[/cyan]")
        
        # Commit相关图表
        if 'commit_analysis' in analysis_result:
            commit_data = analysis_result['commit_analysis']
            
            if 'hourly_distribution' in commit_data:
                chart_path = self.generate_hourly_chart(
                    commit_data['hourly_distribution'],
                    f"{safe_repo_name}_hourly"
                )
                charts.append(chart_path)
            
            if 'weekday_distribution' in commit_data:
                chart_path = self.generate_weekday_chart(
                    commit_data['weekday_distribution'],
                    f"{safe_repo_name}_weekday"
                )
                charts.append(chart_path)
            
            if 'monthly_distribution' in commit_data:
                chart_path = self.generate_monthly_chart(
                    commit_data['monthly_distribution'],
                    f"{safe_repo_name}_monthly_commits"
                )
                charts.append(chart_path)
            
            if 'author_stats' in commit_data:
                chart_path = self.generate_author_chart(
                    commit_data['author_stats'],
                    f"{safe_repo_name}_top_authors"
                )
                charts.append(chart_path)
        
        # 贡献者相关图表
        if 'contributor_analysis' in analysis_result:
            contrib_data = analysis_result['contributor_analysis']
            
            if 'contribution_distribution' in contrib_data:
                chart_path = self.generate_contribution_distribution_chart(
                    contrib_data['contribution_distribution'],
                    f"{safe_repo_name}_contribution_dist"
                )
                charts.append(chart_path)
        
        # Issue相关图表
        if 'issue_analysis' in analysis_result:
            issue_data = analysis_result['issue_analysis']
            
            chart_path = self.generate_issue_status_chart(
                issue_data,
                f"{safe_repo_name}_issue_status"
            )
            charts.append(chart_path)
            
            if 'label_distribution' in issue_data:
                chart_path = self.generate_label_chart(
                    issue_data['label_distribution'],
                    f"{safe_repo_name}_issue_labels"
                )
                charts.append(chart_path)
        
        # PR相关图表
        if 'pr_analysis' in analysis_result:
            pr_data = analysis_result['pr_analysis']
            
            chart_path = self.generate_pr_status_chart(
                pr_data,
                f"{safe_repo_name}_pr_status"
            )
            charts.append(chart_path)
            
            if 'pr_size' in pr_data:
                chart_path = self.generate_pr_size_chart(
                    pr_data['pr_size'],
                    f"{safe_repo_name}_pr_size"
                )
                charts.append(chart_path)
        
        # 生成综合热力图
        if 'commit_analysis' in analysis_result:
            chart_path = self.generate_commit_heatmap(
                analysis_result['commit_analysis'],
                f"{safe_repo_name}_heatmap"
            )
            charts.append(chart_path)
        
        console.print(f"[green]✓ 已生成 {len(charts)} 个图表[/green]")
        return charts
    
    def generate_hourly_chart(self, hourly_data: Dict, filename: str) -> str:
        """生成每小时commit分布图"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        distribution = hourly_data['distribution']
        hours = list(range(24))
        counts = [distribution.get(h, 0) for h in hours]
        
        bars = ax.bar(hours, counts, color=sns.color_palette("Blues_d", 24))
        
        # 高亮峰值小时
        peak_hour = hourly_data['peak_hour']
        bars[peak_hour].set_color('#FF6B6B')
        
        ax.set_xlabel('小时 (24小时制)', fontsize=12)
        ax.set_ylabel('Commit数量', fontsize=12)
        ax.set_title('Commit时间分布（每小时）', fontsize=14, fontweight='bold')
        ax.set_xticks(hours)
        
        # 添加工作时间区域标注
        ax.axvspan(9, 18, alpha=0.2, color='green', label='工作时间')
        ax.legend()
        
        # 添加峰值标注
        ax.annotate(f'峰值: {peak_hour}:00\n({hourly_data["peak_count"]}次)',
                   xy=(peak_hour, hourly_data['peak_count']),
                   xytext=(peak_hour + 2, hourly_data['peak_count'] * 1.1),
                   fontsize=10,
                   arrowprops=dict(arrowstyle='->', color='red'))
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_weekday_chart(self, weekday_data: Dict, filename: str) -> str:
        """生成每周commit分布图"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        distribution = weekday_data['distribution']
        days = list(distribution.keys())
        counts = list(distribution.values())
        
        colors = ['#4ECDC4'] * 5 + ['#FF6B6B'] * 2  # 工作日vs周末
        bars = ax.bar(days, counts, color=colors)
        
        ax.set_xlabel('星期', fontsize=12)
        ax.set_ylabel('Commit数量', fontsize=12)
        ax.set_title('Commit分布（每周）', fontsize=14, fontweight='bold')
        
        # 添加数值标签
        for bar, count in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   str(count), ha='center', va='bottom', fontsize=10)
        
        # 添加图例
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#4ECDC4', label='工作日'),
            Patch(facecolor='#FF6B6B', label='周末')
        ]
        ax.legend(handles=legend_elements)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_monthly_chart(self, monthly_data: Dict, filename: str) -> str:
        """生成每月commit趋势图"""
        fig, ax = plt.subplots(figsize=(14, 6))
        
        distribution = monthly_data['distribution']
        months = list(distribution.keys())
        counts = list(distribution.values())
        
        ax.plot(months, counts, marker='o', linewidth=2, markersize=8, color='#3498DB')
        ax.fill_between(range(len(months)), counts, alpha=0.3, color='#3498DB')
        
        ax.set_xlabel('月份', fontsize=12)
        ax.set_ylabel('Commit数量', fontsize=12)
        ax.set_title('Commit趋势（每月）', fontsize=14, fontweight='bold')
        
        # 旋转x轴标签
        plt.xticks(range(len(months)), months, rotation=45, ha='right')
        
        # 添加平均线
        avg = monthly_data['average_per_month']
        ax.axhline(y=avg, color='red', linestyle='--', label=f'平均值: {avg:.1f}')
        ax.legend()
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_author_chart(self, author_data: Dict, filename: str) -> str:
        """生成Top贡献者图"""
        fig, ax = plt.subplots(figsize=(12, 8))
        
        top_authors = author_data['top_authors']
        authors = list(top_authors.keys())[:10]
        commits = list(top_authors.values())[:10]
        
        # 反转顺序，使最多的在上面
        authors = authors[::-1]
        commits = commits[::-1]
        
        colors = sns.color_palette("viridis", len(authors))
        bars = ax.barh(authors, commits, color=colors)
        
        ax.set_xlabel('Commit数量', fontsize=12)
        ax.set_ylabel('贡献者', fontsize=12)
        ax.set_title('Top 10 贡献者', fontsize=14, fontweight='bold')
        
        # 添加数值标签
        for bar, count in zip(bars, commits):
            ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                   str(count), ha='left', va='center', fontsize=10)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_contribution_distribution_chart(self, contrib_data: Dict, 
                                                  filename: str) -> str:
        """生成贡献分布图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # 贡献层级饼图
        tiers = contrib_data['contribution_tiers']
        labels = list(tiers.keys())
        sizes = list(tiers.values())
        colors = sns.color_palette("Set2", len(labels))
        
        ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
        ax1.set_title('贡献者分布（按贡献数量分层）', fontsize=12, fontweight='bold')
        
        # 帕累托分析文字
        pareto_ratio = contrib_data['pareto_ratio'] * 100
        gini = contrib_data['gini_coefficient']
        
        info_text = f"""
贡献集中度分析:
- 基尼系数: {gini:.3f}
- 前20%贡献者贡献了 {pareto_ratio:.1f}%
- 平均贡献: {contrib_data['average_contributions']:.1f}
- 中位数贡献: {contrib_data['median_contributions']:.1f}
        """
        
        ax2.text(0.5, 0.5, info_text, transform=ax2.transAxes, 
                fontsize=14, verticalalignment='center', horizontalalignment='center',
                bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        ax2.axis('off')
        ax2.set_title('贡献集中度分析', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_issue_status_chart(self, issue_data: Dict, filename: str) -> str:
        """生成Issue状态图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # 状态饼图
        labels = ['Open', 'Closed']
        sizes = [issue_data['open_issues'], issue_data['closed_issues']]
        colors = ['#FF6B6B', '#4ECDC4']
        explode = (0.05, 0)
        
        ax1.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
               colors=colors, shadow=True, startangle=90)
        ax1.set_title('Issue状态分布', fontsize=12, fontweight='bold')
        
        # 解决时间分布
        if 'resolution_time' in issue_data and 'error' not in issue_data['resolution_time']:
            resolution = issue_data['resolution_time']
            categories = ['< 24h', '< 1周', '> 1月']
            values = [
                resolution['within_24_hours'],
                resolution['within_week'] - resolution['within_24_hours'],
                resolution['over_month']
            ]
            colors = ['#2ECC71', '#F39C12', '#E74C3C']
            
            ax2.bar(categories, values, color=colors)
            ax2.set_xlabel('解决时间', fontsize=12)
            ax2.set_ylabel('Issue数量', fontsize=12)
            ax2.set_title('Issue解决时间分布', fontsize=12, fontweight='bold')
        else:
            ax2.text(0.5, 0.5, '无解决时间数据', transform=ax2.transAxes,
                    ha='center', va='center', fontsize=14)
            ax2.axis('off')
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_label_chart(self, label_data: Dict, filename: str) -> str:
        """生成标签分布图"""
        if not label_data:
            return ""
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        labels = list(label_data.keys())[:15]
        counts = list(label_data.values())[:15]
        
        # 反转顺序
        labels = labels[::-1]
        counts = counts[::-1]
        
        colors = sns.color_palette("husl", len(labels))
        bars = ax.barh(labels, counts, color=colors)
        
        ax.set_xlabel('数量', fontsize=12)
        ax.set_ylabel('标签', fontsize=12)
        ax.set_title('Issue标签分布 (Top 15)', fontsize=14, fontweight='bold')
        
        for bar, count in zip(bars, counts):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                   str(count), ha='left', va='center', fontsize=10)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_pr_status_chart(self, pr_data: Dict, filename: str) -> str:
        """生成PR状态图"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        labels = ['已合并', '打开中', '已关闭(未合并)']
        sizes = [
            pr_data['merged_prs'],
            pr_data['open_prs'],
            pr_data['closed_not_merged']
        ]
        colors = ['#2ECC71', '#3498DB', '#E74C3C']
        
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors,
              shadow=True, startangle=90)
        ax.set_title('Pull Request状态分布', fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_pr_size_chart(self, pr_size_data: Dict, filename: str) -> str:
        """生成PR大小分布图"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        distribution = pr_size_data['size_distribution']
        labels = list(distribution.keys())
        sizes = list(distribution.values())
        colors = ['#2ECC71', '#F39C12', '#E67E22', '#E74C3C']
        
        bars = ax.bar(labels, sizes, color=colors)
        
        ax.set_xlabel('PR大小', fontsize=12)
        ax.set_ylabel('数量', fontsize=12)
        ax.set_title('Pull Request大小分布', fontsize=14, fontweight='bold')
        
        for bar, count in zip(bars, sizes):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                   str(count), ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_commit_heatmap(self, commit_data: Dict, filename: str) -> str:
        """生成commit活动热力图"""
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # 构建热力图数据
        hourly = commit_data['hourly_distribution']['distribution']
        weekday = commit_data['weekday_distribution']['distribution']
        
        # 创建7x24的矩阵
        raw_data = commit_data.get('raw_data', [])
        
        if raw_data:
            df = pd.DataFrame(raw_data)
            heatmap_data = np.zeros((7, 24))
            
            for _, row in df.iterrows():
                heatmap_data[row['weekday'], row['hour']] += 1
            
            weekday_labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            hour_labels = [f'{h:02d}' for h in range(24)]
            
            sns.heatmap(heatmap_data, ax=ax, cmap='YlOrRd',
                       xticklabels=hour_labels, yticklabels=weekday_labels,
                       cbar_kws={'label': 'Commit数量'})
            
            ax.set_xlabel('小时', fontsize=12)
            ax.set_ylabel('星期', fontsize=12)
            ax.set_title('Commit活动热力图', fontsize=14, fontweight='bold')
        else:
            ax.text(0.5, 0.5, '数据不足，无法生成热力图', transform=ax.transAxes,
                   ha='center', va='center', fontsize=14)
            ax.axis('off')
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
