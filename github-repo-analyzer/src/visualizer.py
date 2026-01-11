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
    
    def generate_code_churn_chart(self, code_churn_data: Dict, filename: str) -> str:
        """生成代码变更量（Code Churn）趋势图"""
        fig, ax = plt.subplots(figsize=(14, 7))
        
        months = list(code_churn_data.get('monthly_churn', {}).keys())
        additions = [code_churn_data['monthly_churn'][m].get('additions', 0) for m in months]
        deletions = [code_churn_data['monthly_churn'][m].get('deletions', 0) for m in months]
        
        x = np.arange(len(months))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, additions, width, label='新增行数', color='#2ECC71', alpha=0.8)
        bars2 = ax.bar(x + width/2, deletions, width, label='删除行数', color='#E74C3C', alpha=0.8)
        
        # 添加净变更折线
        net_change = [a - d for a, d in zip(additions, deletions)]
        ax2 = ax.twinx()
        ax2.plot(x, net_change, 'b-o', linewidth=2, markersize=6, label='净变更')
        ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax2.set_ylabel('净变更行数', fontsize=12, color='blue')
        
        ax.set_xlabel('月份', fontsize=12)
        ax.set_ylabel('代码行数', fontsize=12)
        ax.set_title('代码变更量趋势（Code Churn）', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=45, ha='right')
        
        # 合并图例
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_contributor_growth_chart(self, growth_data: Dict, filename: str) -> str:
        """生成贡献者增长曲线图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        
        # 左图：累计贡献者增长
        months = list(growth_data.get('cumulative_contributors', {}).keys())
        cumulative = list(growth_data.get('cumulative_contributors', {}).values())
        
        ax1.fill_between(range(len(months)), cumulative, alpha=0.3, color='#3498DB')
        ax1.plot(range(len(months)), cumulative, 'o-', color='#3498DB', linewidth=2, markersize=6)
        
        ax1.set_xlabel('月份', fontsize=12)
        ax1.set_ylabel('累计贡献者数量', fontsize=12)
        ax1.set_title('贡献者累计增长趋势', fontsize=12, fontweight='bold')
        ax1.set_xticks(range(len(months)))
        ax1.set_xticklabels(months, rotation=45, ha='right')
        
        # 右图：每月新增贡献者
        new_contributors = list(growth_data.get('new_contributors_per_month', {}).values())
        colors = ['#2ECC71' if v > 0 else '#E74C3C' for v in new_contributors]
        
        ax2.bar(range(len(months)), new_contributors, color=colors, alpha=0.8)
        ax2.axhline(y=np.mean(new_contributors), color='red', linestyle='--', 
                   label=f'平均值: {np.mean(new_contributors):.1f}')
        
        ax2.set_xlabel('月份', fontsize=12)
        ax2.set_ylabel('新增贡献者数量', fontsize=12)
        ax2.set_title('每月新增贡献者', fontsize=12, fontweight='bold')
        ax2.set_xticks(range(len(months)))
        ax2.set_xticklabels(months, rotation=45, ha='right')
        ax2.legend()
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_file_type_chart(self, file_data: Dict, filename: str) -> str:
        """生成文件类型分布图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # 饼图：文件类型分布
        file_types = file_data.get('file_types', {})
        labels = list(file_types.keys())[:10]
        sizes = list(file_types.values())[:10]
        colors = sns.color_palette("Set3", len(labels))
        
        wedges, texts, autotexts = ax1.pie(sizes, labels=labels, autopct='%1.1f%%',
                                           colors=colors, startangle=90)
        ax1.set_title('文件类型分布', fontsize=12, fontweight='bold')
        
        # 条形图：各类型文件数量
        ax2.barh(labels[::-1], sizes[::-1], color=colors[::-1])
        ax2.set_xlabel('文件数量', fontsize=12)
        ax2.set_title('各类型文件数量', fontsize=12, fontweight='bold')
        
        for i, (label, size) in enumerate(zip(labels[::-1], sizes[::-1])):
            ax2.text(size + 0.5, i, str(size), va='center', fontsize=10)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_release_timeline_chart(self, release_data: Dict, filename: str) -> str:
        """生成版本发布时间线图"""
        fig, ax = plt.subplots(figsize=(16, 8))
        
        releases = release_data.get('releases', [])
        if not releases:
            ax.text(0.5, 0.5, '无发布版本数据', transform=ax.transAxes,
                   ha='center', va='center', fontsize=14)
            ax.axis('off')
        else:
            dates = [r.get('date', '') for r in releases]
            versions = [r.get('version', '') for r in releases]
            downloads = [r.get('downloads', 0) for r in releases]
            
            # 转换日期
            try:
                date_objects = [datetime.strptime(d, '%Y-%m-%d') for d in dates if d]
            except:
                date_objects = list(range(len(dates)))
            
            # 绘制时间线
            ax.scatter(date_objects, [1]*len(date_objects), s=100, c='#3498DB', zorder=2)
            ax.plot(date_objects, [1]*len(date_objects), 'b-', alpha=0.3, zorder=1)
            
            # 添加版本标签
            for i, (date, version) in enumerate(zip(date_objects, versions)):
                y_offset = 0.1 if i % 2 == 0 else -0.1
                ax.annotate(version, (date, 1), xytext=(date, 1 + y_offset),
                           ha='center', fontsize=9, rotation=45)
            
            ax.set_ylim(0.5, 1.5)
            ax.set_xlabel('发布日期', fontsize=12)
            ax.set_title('版本发布时间线', fontsize=14, fontweight='bold')
            ax.yaxis.set_visible(False)
            
            if isinstance(date_objects[0], datetime):
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
                plt.xticks(rotation=45)
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_activity_radar_chart(self, activity_data: Dict, filename: str) -> str:
        """生成项目活跃度雷达图"""
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
        
        # 定义评估维度
        categories = ['Commit活跃度', '贡献者多样性', 'Issue响应速度', 
                     'PR合并效率', '代码质量', '社区参与度']
        N = len(categories)
        
        # 获取各维度分数（0-100）
        scores = [
            activity_data.get('commit_activity', 50),
            activity_data.get('contributor_diversity', 50),
            activity_data.get('issue_response', 50),
            activity_data.get('pr_efficiency', 50),
            activity_data.get('code_quality', 50),
            activity_data.get('community_engagement', 50)
        ]
        
        # 计算角度
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        scores += scores[:1]  # 闭合图形
        angles += angles[:1]
        
        # 绘制雷达图
        ax.plot(angles, scores, 'o-', linewidth=2, color='#3498DB')
        ax.fill(angles, scores, alpha=0.25, color='#3498DB')
        
        # 设置刻度标签
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=11)
        ax.set_ylim(0, 100)
        
        # 添加网格线
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=9)
        
        ax.set_title('项目活跃度综合评估', fontsize=14, fontweight='bold', pad=20)
        
        # 添加总分
        total_score = np.mean(scores[:-1])
        ax.text(0, 0, f'综合评分\n{total_score:.1f}', ha='center', va='center',
               fontsize=16, fontweight='bold', color='#E74C3C')
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_commit_message_length_chart(self, message_data: Dict, filename: str) -> str:
        """生成Commit消息长度分布图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        lengths = message_data.get('lengths', [])
        
        if lengths:
            # 直方图
            ax1.hist(lengths, bins=30, color='#3498DB', edgecolor='white', alpha=0.7)
            ax1.axvline(x=np.mean(lengths), color='red', linestyle='--', 
                       label=f'平均值: {np.mean(lengths):.1f}')
            ax1.axvline(x=np.median(lengths), color='green', linestyle='--',
                       label=f'中位数: {np.median(lengths):.1f}')
            ax1.set_xlabel('消息长度（字符）', fontsize=12)
            ax1.set_ylabel('频次', fontsize=12)
            ax1.set_title('Commit消息长度分布', fontsize=12, fontweight='bold')
            ax1.legend()
            
            # 箱线图
            bp = ax2.boxplot(lengths, vert=True, patch_artist=True)
            bp['boxes'][0].set_facecolor('#3498DB')
            bp['boxes'][0].set_alpha(0.7)
            
            # 添加统计信息
            stats_text = f"""
统计信息:
- 最短: {min(lengths)}
- 最长: {max(lengths)}
- 平均值: {np.mean(lengths):.1f}
- 标准差: {np.std(lengths):.1f}
- 四分位数: Q1={np.percentile(lengths, 25):.0f}, 
           Q3={np.percentile(lengths, 75):.0f}
            """
            ax2.text(1.3, np.median(lengths), stats_text, fontsize=10,
                    verticalalignment='center',
                    bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))
            ax2.set_ylabel('消息长度（字符）', fontsize=12)
            ax2.set_title('Commit消息长度箱线图', fontsize=12, fontweight='bold')
        else:
            ax1.text(0.5, 0.5, '无数据', transform=ax1.transAxes, ha='center', va='center')
            ax2.text(0.5, 0.5, '无数据', transform=ax2.transAxes, ha='center', va='center')
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_bus_factor_chart(self, bus_factor_data: Dict, filename: str) -> str:
        """生成Bus Factor（关键人物依赖）可视化图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # 左图：关键贡献者贡献占比
        key_contributors = bus_factor_data.get('key_contributors', [])
        names = [c.get('name', 'Unknown') for c in key_contributors[:5]]
        contributions = [c.get('percentage', 0) for c in key_contributors[:5]]
        
        colors = ['#E74C3C' if p > 30 else '#F39C12' if p > 15 else '#2ECC71' 
                 for p in contributions]
        
        bars = ax1.barh(names[::-1], contributions[::-1], color=colors[::-1])
        ax1.set_xlabel('贡献占比 (%)', fontsize=12)
        ax1.set_title('关键贡献者贡献占比', fontsize=12, fontweight='bold')
        ax1.axvline(x=30, color='red', linestyle='--', alpha=0.5, label='高风险线(30%)')
        ax1.legend()
        
        for bar, pct in zip(bars, contributions[::-1]):
            ax1.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                    f'{pct:.1f}%', va='center', fontsize=10)
        
        # 右图：Bus Factor指示器
        bus_factor = bus_factor_data.get('bus_factor', 1)
        
        # 创建仪表盘效果
        theta = np.linspace(0, np.pi, 100)
        r = 1
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        
        ax2.plot(x, y, 'k-', linewidth=2)
        ax2.fill_between(x, y, alpha=0.1)
        
        # 分区着色
        colors_zones = ['#E74C3C', '#F39C12', '#F1C40F', '#2ECC71']
        for i, color in enumerate(colors_zones):
            theta_start = i * np.pi / 4
            theta_end = (i + 1) * np.pi / 4
            theta_zone = np.linspace(theta_start, theta_end, 25)
            ax2.fill_between(np.cos(theta_zone), np.sin(theta_zone), 
                           alpha=0.3, color=color)
        
        # 绘制指针
        pointer_angle = np.pi - (bus_factor / 10) * np.pi  # 假设最大值为10
        pointer_angle = max(0, min(np.pi, pointer_angle))
        ax2.annotate('', xy=(0.8*np.cos(pointer_angle), 0.8*np.sin(pointer_angle)),
                    xytext=(0, 0),
                    arrowprops=dict(arrowstyle='->', color='black', lw=3))
        
        ax2.text(0, -0.2, f'Bus Factor: {bus_factor}', ha='center', 
                fontsize=16, fontweight='bold')
        
        # 添加刻度标签
        for i in range(5):
            angle = np.pi - (i * 2.5 / 10) * np.pi
            ax2.text(1.1*np.cos(angle), 1.1*np.sin(angle), str(int(i*2.5)),
                    ha='center', va='center', fontsize=10)
        
        ax2.set_xlim(-1.5, 1.5)
        ax2.set_ylim(-0.5, 1.3)
        ax2.axis('off')
        ax2.set_title('Bus Factor 指标', fontsize=12, fontweight='bold')
        
        # 风险说明
        risk_text = "风险等级:\n🔴 1-2: 极高风险\n🟠 3-4: 高风险\n🟡 5-6: 中等风险\n🟢 7+: 低风险"
        ax2.text(1.0, 0.5, risk_text, fontsize=10, 
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, f"{filename}.png")
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    
    def generate_review_time_chart(self, review_data: Dict, filename: str) -> str:
        """生成PR审查时间分布图"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        review_times = review_data.get('review_times_hours', [])
        
        if review_times:
            # 直方图
            ax1.hist(review_times, bins=20, color='#9B59B6', edgecolor='white', alpha=0.7)
            ax1.axvline(x=np.median(review_times), color='red', linestyle='--',
                       label=f'中位数: {np.median(review_times):.1f}h')
            ax1.set_xlabel('审查时间（小时）', fontsize=12)
            ax1.set_ylabel('PR数量', fontsize=12)
            ax1.set_title('PR审查时间分布', fontsize=12, fontweight='bold')
            ax1.legend()
            
            # 分类统计
            categories = ['< 1h', '1-4h', '4-24h', '1-7天', '> 7天']
            counts = [
                len([t for t in review_times if t < 1]),
                len([t for t in review_times if 1 <= t < 4]),
                len([t for t in review_times if 4 <= t < 24]),
                len([t for t in review_times if 24 <= t < 168]),
                len([t for t in review_times if t >= 168])
            ]
            colors = ['#2ECC71', '#27AE60', '#F39C12', '#E67E22', '#E74C3C']
            
            ax2.pie(counts, labels=categories, autopct='%1.1f%%', colors=colors,
                   startangle=90)
            ax2.set_title('审查时间分类', fontsize=12, fontweight='bold')
        else:
            ax1.text(0.5, 0.5, '无审查时间数据', transform=ax1.transAxes, 
                    ha='center', va='center')
            ax2.text(0.5, 0.5, '无审查时间数据', transform=ax2.transAxes,
                    ha='center', va='center')
        
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
