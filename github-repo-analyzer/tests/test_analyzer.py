"""
单元测试 - 分析模块

注意：这些测试需要网络连接和有效的GitHub Token
可以通过使用pytest的标记来跳过需要网络的测试
"""

import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import pandas as pd

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analyzer import CommitAnalyzer, ContributorAnalyzer, IssueAnalyzer, PullRequestAnalyzer


class TestCommitAnalyzer:
    """Commit分析器测试"""
    
    @pytest.fixture
    def mock_client(self):
        """创建模拟客户端"""
        client = Mock()
        return client
    
    @pytest.fixture
    def analyzer(self, mock_client):
        """创建分析器实例"""
        return CommitAnalyzer(mock_client)
    
    def test_analyze_hourly_distribution(self, analyzer):
        """测试每小时分布分析"""
        # 创建测试数据
        data = {
            'hour': [9, 10, 10, 14, 14, 14, 15, 22],
            'date': pd.date_range('2024-01-01', periods=8, freq='h')
        }
        df = pd.DataFrame(data)
        
        result = analyzer._analyze_hourly_distribution(df)
        
        assert 'distribution' in result
        assert 'peak_hour' in result
        assert 'peak_count' in result
        assert 'working_hours_ratio' in result
        assert result['peak_hour'] == 14
        assert result['peak_count'] == 3
    
    def test_analyze_weekday_distribution(self, analyzer):
        """测试每周分布分析"""
        data = {
            'weekday': [0, 0, 1, 2, 3, 4, 5, 6],  # 周一到周日
            'date': pd.date_range('2024-01-01', periods=8, freq='D')
        }
        df = pd.DataFrame(data)
        
        result = analyzer._analyze_weekday_distribution(df)
        
        assert 'distribution' in result
        assert 'peak_day' in result
        assert 'weekend_ratio' in result
        assert result['peak_day'] == '周一'  # 周一有2个
    
    def test_analyze_code_changes(self, analyzer):
        """测试代码变更分析"""
        data = {
            'additions': [100, 200, 50],
            'deletions': [50, 100, 25],
            'total_changes': [150, 300, 75]
        }
        df = pd.DataFrame(data)
        
        result = analyzer._analyze_code_changes(df)
        
        assert result['total_additions'] == 350
        assert result['total_deletions'] == 175
        assert result['total_changes'] == 525
        assert result['change_ratio'] == 2.0


class TestContributorAnalyzer:
    """贡献者分析器测试"""
    
    @pytest.fixture
    def mock_client(self):
        """创建模拟客户端"""
        return Mock()
    
    @pytest.fixture
    def analyzer(self, mock_client):
        """创建分析器实例"""
        return ContributorAnalyzer(mock_client)
    
    def test_analyze_contribution_distribution(self, analyzer):
        """测试贡献分布分析"""
        data = {
            'contributions': [1000, 500, 100, 50, 20, 10, 5, 3, 2, 1]
        }
        df = pd.DataFrame(data)
        
        result = analyzer._analyze_contribution_distribution(df)
        
        assert 'total_contributions' in result
        assert 'gini_coefficient' in result
        assert 'pareto_ratio' in result
        assert 'contribution_tiers' in result
        assert result['total_contributions'] == 1691
    
    def test_get_top_contributors(self, analyzer):
        """测试获取Top贡献者"""
        data = {
            'login': ['user1', 'user2', 'user3'],
            'name': ['User One', 'User Two', 'User Three'],
            'contributions': [100, 50, 25],
            'followers': [1000, 500, 100],
            'profile_url': ['url1', 'url2', 'url3']
        }
        df = pd.DataFrame(data)
        
        result = analyzer._get_top_contributors(df, top_n=2)
        
        assert len(result) == 2
        assert result[0]['login'] == 'user1'
        assert result[0]['contributions'] == 100


class TestIssueAnalyzer:
    """Issue分析器测试"""
    
    @pytest.fixture
    def mock_client(self):
        """创建模拟客户端"""
        return Mock()
    
    @pytest.fixture
    def analyzer(self, mock_client):
        """创建分析器实例"""
        return IssueAnalyzer(mock_client)
    
    def test_analyze_resolution_time(self, analyzer):
        """测试解决时间分析"""
        data = {
            'state': ['closed', 'closed', 'closed', 'open'],
            'resolution_time_hours': [12, 48, 200, None]
        }
        df = pd.DataFrame(data)
        
        result = analyzer._analyze_resolution_time(df)
        
        assert 'average_hours' in result
        assert 'median_hours' in result
        assert 'within_24_hours' in result
        assert result['within_24_hours'] == 1
    
    def test_analyze_labels(self, analyzer):
        """测试标签分析"""
        data = {
            'labels': [['bug', 'help wanted'], ['bug'], ['enhancement', 'bug']]
        }
        df = pd.DataFrame(data)
        
        result = analyzer._analyze_labels(df)
        
        assert 'bug' in result
        assert result['bug'] == 3


class TestPullRequestAnalyzer:
    """Pull Request分析器测试"""
    
    @pytest.fixture
    def mock_client(self):
        """创建模拟客户端"""
        return Mock()
    
    @pytest.fixture
    def analyzer(self, mock_client):
        """创建分析器实例"""
        return PullRequestAnalyzer(mock_client)
    
    def test_analyze_pr_size(self, analyzer):
        """测试PR大小分析"""
        data = {
            'additions': [10, 100, 300, 1000],
            'deletions': [5, 50, 100, 500],
            'changed_files': [1, 5, 10, 50]
        }
        df = pd.DataFrame(data)
        
        result = analyzer._analyze_pr_size(df)
        
        assert 'average_additions' in result
        assert 'size_distribution' in result
        assert result['size_distribution']['small (< 50 lines)'] == 1
    
    def test_analyze_code_review(self, analyzer):
        """测试代码审查分析"""
        data = {
            'comments': [5, 0, 3],
            'review_comments': [10, 0, 5]
        }
        df = pd.DataFrame(data)
        
        result = analyzer._analyze_code_review(df)
        
        assert 'average_review_comments' in result
        assert 'review_rate' in result
        assert result['prs_with_review'] == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
