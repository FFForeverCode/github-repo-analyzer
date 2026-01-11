"""
配置管理模块

负责加载和管理应用程序配置
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List
from dotenv import load_dotenv


@dataclass
class AnalysisConfig:
    """分析配置类"""
    # 分析的时间范围（天数）
    days_range: int = 365
    
    # 最大获取的commit数量
    max_commits: int = 1000
    
    # 最大获取的贡献者数量
    max_contributors: int = 100
    
    # 是否分析issue
    analyze_issues: bool = True
    
    # 是否分析PR
    analyze_pull_requests: bool = True
    
    # 是否生成可视化图表
    generate_charts: bool = True
    
    # 输出目录
    output_dir: str = "output"
    
    # 要排除的文件类型（用于统计代码变更）
    exclude_extensions: List[str] = field(default_factory=lambda: [
        '.md', '.txt', '.json', '.yml', '.yaml', '.lock'
    ])


@dataclass
class GitHubConfig:
    """GitHub配置类"""
    token: Optional[str] = None
    base_url: str = "https://api.github.com"
    timeout: int = 30
    retry_count: int = 3
    
    def __post_init__(self):
        """初始化后加载环境变量"""
        load_dotenv()
        if self.token is None:
            self.token = os.getenv('GITHUB_TOKEN')


class ConfigManager:
    """配置管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.github_config = GitHubConfig()
        self.analysis_config = AnalysisConfig()
    
    def get_github_config(self) -> GitHubConfig:
        """获取GitHub配置"""
        return self.github_config
    
    def get_analysis_config(self) -> AnalysisConfig:
        """获取分析配置"""
        return self.analysis_config
    
    def update_analysis_config(self, **kwargs):
        """更新分析配置"""
        for key, value in kwargs.items():
            if hasattr(self.analysis_config, key):
                setattr(self.analysis_config, key, value)
    
    def validate(self) -> bool:
        """验证配置是否有效"""
        if not self.github_config.token:
            return False
        return True


def get_config() -> ConfigManager:
    """获取配置管理器单例"""
    return ConfigManager()
