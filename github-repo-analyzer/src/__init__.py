"""
GitHub仓库分析工具

使用PyGithub分析热门开源项目的commit模式、贡献者活跃度等
"""

__version__ = "2.0.0"
__author__ = "开源软件基础课程小组"

# 核心模块
from .github_client import GitHubClient
from .analyzer import RepoAnalyzer, CommitAnalyzer, ContributorAnalyzer, IssueAnalyzer, PRAnalyzer
from .visualizer import ChartGenerator, DashboardGenerator, WordCloudGenerator, NetworkGraphGenerator
from .report_generator import ReportGenerator
from .config import get_config

# 新增功能模块
from .cache_manager import CacheManager, CachedGitHubClient, MemoryCache, FileCache
from .exporter import ExportManager, CSVExporter, ExcelExporter, MarkdownExporter, PDFExporter
from .comparator import RepoComparator, BenchmarkAnalyzer, TrendComparator, RepoMetrics
from .predictor import TrendPredictor, ProjectHealthPredictor, SeasonalAnalyzer, AnomalyDetector

__all__ = [
    # 版本信息
    '__version__',
    '__author__',
    
    # 核心类
    'GitHubClient',
    'RepoAnalyzer',
    'CommitAnalyzer',
    'ContributorAnalyzer',
    'IssueAnalyzer',
    'PRAnalyzer',
    
    # 可视化
    'ChartGenerator',
    'DashboardGenerator',
    'WordCloudGenerator',
    'NetworkGraphGenerator',
    
    # 报告生成
    'ReportGenerator',
    
    # 配置
    'get_config',
    
    # 缓存
    'CacheManager',
    'CachedGitHubClient',
    'MemoryCache',
    'FileCache',
    
    # 导出
    'ExportManager',
    'CSVExporter',
    'ExcelExporter',
    'MarkdownExporter',
    'PDFExporter',
    
    # 对比分析
    'RepoComparator',
    'BenchmarkAnalyzer',
    'TrendComparator',
    'RepoMetrics',
    
    # 预测分析
    'TrendPredictor',
    'ProjectHealthPredictor',
    'SeasonalAnalyzer',
    'AnomalyDetector',
]
