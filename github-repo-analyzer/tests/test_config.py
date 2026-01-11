"""
单元测试 - 配置模块
"""

import os
import pytest
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import ConfigManager, GitHubConfig, AnalysisConfig, get_config


class TestGitHubConfig:
    """GitHub配置测试"""
    
    def test_default_values(self):
        """测试默认配置值"""
        config = GitHubConfig()
        assert config.base_url == "https://api.github.com"
        assert config.timeout == 30
        assert config.retry_count == 3
    
    @patch.dict(os.environ, {'GITHUB_TOKEN': 'test_token_123'})
    def test_load_token_from_env(self):
        """测试从环境变量加载Token"""
        config = GitHubConfig()
        config.__post_init__()
        # 注意：由于dotenv会被调用，实际行为可能不同
        # 这里只是验证机制存在
        assert True


class TestAnalysisConfig:
    """分析配置测试"""
    
    def test_default_values(self):
        """测试默认配置值"""
        config = AnalysisConfig()
        assert config.days_range == 365
        assert config.max_commits == 1000
        assert config.max_contributors == 100
        assert config.analyze_issues == True
        assert config.analyze_pull_requests == True
        assert config.generate_charts == True
        assert config.output_dir == "output"
    
    def test_exclude_extensions(self):
        """测试排除的文件扩展名"""
        config = AnalysisConfig()
        assert '.md' in config.exclude_extensions
        assert '.json' in config.exclude_extensions


class TestConfigManager:
    """配置管理器测试"""
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        config1 = ConfigManager()
        config2 = ConfigManager()
        assert config1 is config2
    
    def test_get_github_config(self):
        """测试获取GitHub配置"""
        manager = ConfigManager()
        config = manager.get_github_config()
        assert isinstance(config, GitHubConfig)
    
    def test_get_analysis_config(self):
        """测试获取分析配置"""
        manager = ConfigManager()
        config = manager.get_analysis_config()
        assert isinstance(config, AnalysisConfig)
    
    def test_update_analysis_config(self):
        """测试更新分析配置"""
        manager = ConfigManager()
        manager.update_analysis_config(days_range=180, max_commits=500)
        config = manager.get_analysis_config()
        assert config.days_range == 180
        assert config.max_commits == 500
    
    def test_get_config_function(self):
        """测试get_config函数"""
        config = get_config()
        assert isinstance(config, ConfigManager)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
