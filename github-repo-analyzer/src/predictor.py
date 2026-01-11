"""
趋势预测模块

使用统计方法和机器学习对项目趋势进行预测
"""

import os
import json
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import math

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@dataclass
class PredictionResult:
    """预测结果数据类"""
    metric_name: str
    current_value: float
    predicted_values: List[float]
    prediction_dates: List[str]
    confidence_interval: Tuple[float, float]
    trend: str  # 'increasing', 'decreasing', 'stable'
    trend_strength: float  # 0-1
    model_used: str


class SimpleMovingAverage:
    """简单移动平均预测"""
    
    def __init__(self, window_size: int = 3):
        self.window_size = window_size
    
    def predict(self, data: List[float], periods: int = 3) -> List[float]:
        """预测未来periods个周期的值"""
        if len(data) < self.window_size:
            return [sum(data) / len(data)] * periods if data else [0] * periods
        
        predictions = []
        working_data = data.copy()
        
        for _ in range(periods):
            # 计算最近window_size个值的平均
            recent = working_data[-self.window_size:]
            pred = sum(recent) / len(recent)
            predictions.append(pred)
            working_data.append(pred)
        
        return predictions


class ExponentialSmoothing:
    """指数平滑预测"""
    
    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
    
    def predict(self, data: List[float], periods: int = 3) -> List[float]:
        """预测未来periods个周期的值"""
        if not data:
            return [0] * periods
        
        # 计算平滑值
        smoothed = data[0]
        for value in data[1:]:
            smoothed = self.alpha * value + (1 - self.alpha) * smoothed
        
        # 预测
        return [smoothed] * periods


class LinearRegression:
    """线性回归预测"""
    
    def fit_predict(self, data: List[float], periods: int = 3) -> Tuple[List[float], float, float]:
        """
        拟合数据并预测
        
        Returns:
            (predictions, slope, intercept)
        """
        if len(data) < 2:
            return [data[0] if data else 0] * periods, 0, data[0] if data else 0
        
        n = len(data)
        x = list(range(n))
        
        # 计算均值
        x_mean = sum(x) / n
        y_mean = sum(data) / n
        
        # 计算斜率和截距
        numerator = sum((x[i] - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return [y_mean] * periods, 0, y_mean
        
        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        
        # 预测
        predictions = []
        for i in range(periods):
            pred = slope * (n + i) + intercept
            predictions.append(max(0, pred))  # 确保非负
        
        return predictions, slope, intercept
    
    def calculate_r_squared(self, data: List[float], slope: float, intercept: float) -> float:
        """计算R²决定系数"""
        if len(data) < 2:
            return 0
        
        n = len(data)
        y_mean = sum(data) / n
        
        # 计算总平方和
        ss_tot = sum((y - y_mean) ** 2 for y in data)
        if ss_tot == 0:
            return 1
        
        # 计算残差平方和
        ss_res = sum((data[i] - (slope * i + intercept)) ** 2 for i in range(n))
        
        return 1 - (ss_res / ss_tot)


class HoltWinters:
    """Holt-Winters 双指数平滑（趋势+水平）"""
    
    def __init__(self, alpha: float = 0.5, beta: float = 0.5):
        self.alpha = alpha
        self.beta = beta
    
    def predict(self, data: List[float], periods: int = 3) -> List[float]:
        """预测未来periods个周期的值"""
        if len(data) < 2:
            return [data[0] if data else 0] * periods
        
        # 初始化
        level = data[0]
        trend = data[1] - data[0]
        
        # 更新
        for i in range(1, len(data)):
            prev_level = level
            level = self.alpha * data[i] + (1 - self.alpha) * (level + trend)
            trend = self.beta * (level - prev_level) + (1 - self.beta) * trend
        
        # 预测
        predictions = []
        for i in range(1, periods + 1):
            pred = level + i * trend
            predictions.append(max(0, pred))
        
        return predictions


class TrendPredictor:
    """趋势预测器"""
    
    def __init__(self):
        self.sma = SimpleMovingAverage()
        self.exp = ExponentialSmoothing()
        self.lr = LinearRegression()
        self.hw = HoltWinters()
    
    def analyze_trend(self, data: List[float]) -> Tuple[str, float]:
        """
        分析数据趋势
        
        Returns:
            (trend_direction, trend_strength)
        """
        if len(data) < 2:
            return 'stable', 0.0
        
        # 使用线性回归斜率判断趋势
        _, slope, intercept = self.lr.fit_predict(data, 1)
        r_squared = self.lr.calculate_r_squared(data, slope, intercept)
        
        # 计算相对斜率（相对于数据均值）
        mean_value = sum(data) / len(data) if data else 1
        relative_slope = slope / mean_value if mean_value != 0 else 0
        
        # 判断趋势方向
        if relative_slope > 0.05:
            direction = 'increasing'
        elif relative_slope < -0.05:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        # 趋势强度（基于R²和相对斜率）
        strength = min(1.0, abs(relative_slope) * r_squared * 10)
        
        return direction, strength
    
    def predict(self, data: List[float], periods: int = 6, 
                method: str = 'auto') -> PredictionResult:
        """
        预测未来趋势
        
        Args:
            data: 历史数据
            periods: 预测周期数
            method: 预测方法 ('sma', 'exp', 'linear', 'holt_winters', 'auto')
        """
        if not data:
            return PredictionResult(
                metric_name='unknown',
                current_value=0,
                predicted_values=[0] * periods,
                prediction_dates=[],
                confidence_interval=(0, 0),
                trend='stable',
                trend_strength=0,
                model_used='none'
            )
        
        # 分析趋势
        trend, trend_strength = self.analyze_trend(data)
        
        # 选择预测方法
        if method == 'auto':
            # 根据数据特征自动选择
            if len(data) < 5:
                method = 'sma'
            elif trend_strength > 0.5:
                method = 'holt_winters'
            else:
                method = 'linear'
        
        # 执行预测
        if method == 'sma':
            predictions = self.sma.predict(data, periods)
            model_name = 'Simple Moving Average'
        elif method == 'exp':
            predictions = self.exp.predict(data, periods)
            model_name = 'Exponential Smoothing'
        elif method == 'linear':
            predictions, _, _ = self.lr.fit_predict(data, periods)
            model_name = 'Linear Regression'
        elif method == 'holt_winters':
            predictions = self.hw.predict(data, periods)
            model_name = 'Holt-Winters'
        else:
            predictions = self.sma.predict(data, periods)
            model_name = 'Simple Moving Average'
        
        # 计算置信区间
        confidence_interval = self._calculate_confidence_interval(data, predictions)
        
        return PredictionResult(
            metric_name='',  # 由调用者设置
            current_value=data[-1] if data else 0,
            predicted_values=predictions,
            prediction_dates=[],  # 由调用者设置
            confidence_interval=confidence_interval,
            trend=trend,
            trend_strength=trend_strength,
            model_used=model_name
        )
    
    def _calculate_confidence_interval(self, data: List[float], 
                                       predictions: List[float]) -> Tuple[float, float]:
        """计算置信区间"""
        if len(data) < 2:
            avg = predictions[0] if predictions else 0
            return (avg * 0.8, avg * 1.2)
        
        # 使用历史数据的标准差
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        std_dev = math.sqrt(variance)
        
        # 95%置信区间（约2个标准差）
        pred_mean = sum(predictions) / len(predictions) if predictions else 0
        lower = pred_mean - 2 * std_dev
        upper = pred_mean + 2 * std_dev
        
        return (max(0, lower), upper)


class ProjectHealthPredictor:
    """项目健康度预测器"""
    
    def __init__(self):
        self.predictor = TrendPredictor()
    
    def predict_project_health(self, analysis_result: Dict, 
                               periods: int = 6) -> Dict:
        """
        预测项目未来健康状况
        
        Args:
            analysis_result: 分析结果
            periods: 预测周期数（月）
        """
        predictions = {}
        
        # 1. 预测Commit趋势
        commit_data = analysis_result.get('commit_analysis', {})
        monthly_commits = commit_data.get('monthly_distribution', {}).get('distribution', {})
        
        if monthly_commits:
            commit_values = list(monthly_commits.values())
            commit_pred = self.predictor.predict(commit_values, periods)
            commit_pred.metric_name = 'commits'
            predictions['commit_trend'] = self._result_to_dict(commit_pred)
        
        # 2. 预测活跃度趋势
        activity_score = self._calculate_activity_scores(analysis_result)
        if activity_score:
            activity_pred = self.predictor.predict(activity_score, periods)
            activity_pred.metric_name = 'activity'
            predictions['activity_trend'] = self._result_to_dict(activity_pred)
        
        # 3. 生成综合预测
        predictions['overall_prediction'] = self._generate_overall_prediction(predictions)
        predictions['risk_assessment'] = self._assess_risks(predictions)
        predictions['recommendations'] = self._generate_recommendations(predictions)
        
        return predictions
    
    def _calculate_activity_scores(self, data: Dict) -> List[float]:
        """计算历史活跃度分数序列"""
        commit_data = data.get('commit_analysis', {})
        monthly = commit_data.get('monthly_distribution', {}).get('distribution', {})
        
        if not monthly:
            return []
        
        # 简化计算：基于月度commit数量计算活跃度分数
        max_commits = max(monthly.values()) if monthly.values() else 1
        scores = []
        for count in monthly.values():
            score = (count / max_commits) * 100
            scores.append(score)
        
        return scores
    
    def _result_to_dict(self, result: PredictionResult) -> Dict:
        """将预测结果转换为字典"""
        return {
            'metric': result.metric_name,
            'current_value': result.current_value,
            'predicted_values': [round(v, 2) for v in result.predicted_values],
            'confidence_interval': {
                'lower': round(result.confidence_interval[0], 2),
                'upper': round(result.confidence_interval[1], 2)
            },
            'trend': result.trend,
            'trend_strength': round(result.trend_strength, 2),
            'model': result.model_used
        }
    
    def _generate_overall_prediction(self, predictions: Dict) -> Dict:
        """生成综合预测"""
        commit_trend = predictions.get('commit_trend', {})
        activity_trend = predictions.get('activity_trend', {})
        
        # 综合趋势判断
        trends = []
        if commit_trend:
            trends.append(commit_trend.get('trend', 'stable'))
        if activity_trend:
            trends.append(activity_trend.get('trend', 'stable'))
        
        # 判断整体趋势
        if trends.count('increasing') > trends.count('decreasing'):
            overall = 'positive'
            outlook = '项目整体呈上升趋势，发展前景良好'
        elif trends.count('decreasing') > trends.count('increasing'):
            overall = 'negative'
            outlook = '项目活跃度有所下降，需要关注'
        else:
            overall = 'neutral'
            outlook = '项目发展平稳，处于稳定期'
        
        return {
            'overall_trend': overall,
            'outlook': outlook,
            'confidence': 'medium'
        }
    
    def _assess_risks(self, predictions: Dict) -> List[Dict]:
        """评估风险"""
        risks = []
        
        commit_trend = predictions.get('commit_trend', {})
        
        # 检查Commit下降风险
        if commit_trend.get('trend') == 'decreasing':
            risks.append({
                'level': 'medium',
                'type': 'activity_decline',
                'description': 'Commit活动呈下降趋势',
                'suggestion': '建议吸引更多贡献者参与项目'
            })
        
        # 检查活跃度风险
        activity_trend = predictions.get('activity_trend', {})
        if activity_trend:
            predicted_values = activity_trend.get('predicted_values', [])
            if predicted_values and min(predicted_values) < 30:
                risks.append({
                    'level': 'high',
                    'type': 'low_activity',
                    'description': '预测未来活跃度可能较低',
                    'suggestion': '建议增加项目推广和社区互动'
                })
        
        return risks
    
    def _generate_recommendations(self, predictions: Dict) -> List[str]:
        """生成建议"""
        recommendations = []
        
        overall = predictions.get('overall_prediction', {})
        
        if overall.get('overall_trend') == 'positive':
            recommendations.append("保持当前发展节奏，继续吸引新贡献者")
            recommendations.append("考虑发布新版本来维持社区热度")
        elif overall.get('overall_trend') == 'negative':
            recommendations.append("分析活跃度下降原因，制定改进计划")
            recommendations.append("增加与社区的互动，及时响应Issues和PRs")
            recommendations.append("考虑添加新功能来吸引用户关注")
        else:
            recommendations.append("维护好现有功能的稳定性")
            recommendations.append("定期发布更新保持项目活力")
        
        return recommendations
    
    def print_prediction_report(self, predictions: Dict, repo_name: str = ""):
        """打印预测报告"""
        console.print(Panel(
            f"[bold]📈 {repo_name} 趋势预测报告[/bold]",
            border_style="blue"
        ))
        
        # Commit趋势
        commit_trend = predictions.get('commit_trend', {})
        if commit_trend:
            trend_icon = "📈" if commit_trend['trend'] == 'increasing' else "📉" if commit_trend['trend'] == 'decreasing' else "➡️"
            console.print(f"\n[cyan]Commit趋势:[/cyan] {trend_icon} {commit_trend['trend'].upper()}")
            console.print(f"  当前值: {commit_trend['current_value']:.0f}")
            console.print(f"  预测值: {', '.join([f'{v:.0f}' for v in commit_trend['predicted_values']])}")
            console.print(f"  置信区间: [{commit_trend['confidence_interval']['lower']:.0f}, {commit_trend['confidence_interval']['upper']:.0f}]")
            console.print(f"  预测模型: {commit_trend['model']}")
        
        # 综合预测
        overall = predictions.get('overall_prediction', {})
        if overall:
            console.print(f"\n[bold]综合预测:[/bold] {overall['outlook']}")
        
        # 风险评估
        risks = predictions.get('risk_assessment', [])
        if risks:
            console.print("\n[bold yellow]⚠️ 风险评估:[/bold yellow]")
            for risk in risks:
                level_color = 'red' if risk['level'] == 'high' else 'yellow'
                console.print(f"  [{level_color}]• {risk['description']}[/{level_color}]")
                console.print(f"    建议: {risk['suggestion']}")
        
        # 建议
        recommendations = predictions.get('recommendations', [])
        if recommendations:
            console.print("\n[bold green]💡 建议:[/bold green]")
            for rec in recommendations:
                console.print(f"  • {rec}")


class SeasonalAnalyzer:
    """季节性分析器"""
    
    def analyze_seasonality(self, monthly_data: Dict[str, int]) -> Dict:
        """
        分析数据的季节性特征
        
        Args:
            monthly_data: 月度数据字典 {'YYYY-MM': count}
        """
        if not monthly_data:
            return {'has_seasonality': False}
        
        # 按月份汇总
        month_totals = {i: [] for i in range(1, 13)}
        
        for date_str, count in monthly_data.items():
            try:
                month = int(date_str.split('-')[1])
                month_totals[month].append(count)
            except (ValueError, IndexError):
                continue
        
        # 计算各月平均
        month_avgs = {}
        for month, values in month_totals.items():
            if values:
                month_avgs[month] = sum(values) / len(values)
        
        if not month_avgs:
            return {'has_seasonality': False}
        
        # 计算变异系数
        avg_values = list(month_avgs.values())
        mean = sum(avg_values) / len(avg_values)
        if mean == 0:
            return {'has_seasonality': False}
        
        variance = sum((x - mean) ** 2 for x in avg_values) / len(avg_values)
        cv = math.sqrt(variance) / mean  # 变异系数
        
        # 找出高峰和低谷月份
        sorted_months = sorted(month_avgs.items(), key=lambda x: x[1], reverse=True)
        peak_months = [m for m, v in sorted_months[:3]]
        low_months = [m for m, v in sorted_months[-3:]]
        
        # 判断是否有明显季节性（CV > 0.2认为有季节性）
        has_seasonality = cv > 0.2
        
        month_names = ['', '一月', '二月', '三月', '四月', '五月', '六月',
                      '七月', '八月', '九月', '十月', '十一月', '十二月']
        
        return {
            'has_seasonality': has_seasonality,
            'coefficient_of_variation': round(cv, 3),
            'monthly_averages': {month_names[m]: round(v, 1) for m, v in month_avgs.items()},
            'peak_months': [month_names[m] for m in peak_months],
            'low_months': [month_names[m] for m in low_months],
            'pattern_description': self._describe_pattern(peak_months, has_seasonality)
        }
    
    def _describe_pattern(self, peak_months: List[int], has_seasonality: bool) -> str:
        """描述季节性模式"""
        if not has_seasonality:
            return "活动分布相对均匀，无明显季节性"
        
        # 检查是否集中在特定季节
        winter = [12, 1, 2]
        spring = [3, 4, 5]
        summer = [6, 7, 8]
        fall = [9, 10, 11]
        
        if all(m in winter for m in peak_months[:2]):
            return "活动高峰集中在冬季"
        elif all(m in spring for m in peak_months[:2]):
            return "活动高峰集中在春季"
        elif all(m in summer for m in peak_months[:2]):
            return "活动高峰集中在夏季"
        elif all(m in fall for m in peak_months[:2]):
            return "活动高峰集中在秋季"
        else:
            return "存在季节性波动，但无明显的季节性集中"


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, sensitivity: float = 2.0):
        """
        Args:
            sensitivity: 异常检测敏感度（标准差倍数）
        """
        self.sensitivity = sensitivity
    
    def detect_anomalies(self, data: List[float], labels: List[str] = None) -> Dict:
        """
        检测数据中的异常值
        
        Args:
            data: 数据列表
            labels: 对应的标签（如日期）
        """
        if len(data) < 3:
            return {'anomalies': [], 'has_anomalies': False}
        
        # 计算统计量
        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return {'anomalies': [], 'has_anomalies': False}
        
        # 检测异常
        anomalies = []
        for i, value in enumerate(data):
            z_score = (value - mean) / std_dev
            if abs(z_score) > self.sensitivity:
                anomaly = {
                    'index': i,
                    'value': value,
                    'z_score': round(z_score, 2),
                    'type': 'spike' if z_score > 0 else 'drop',
                    'severity': 'high' if abs(z_score) > 3 else 'medium'
                }
                if labels and i < len(labels):
                    anomaly['label'] = labels[i]
                anomalies.append(anomaly)
        
        return {
            'anomalies': anomalies,
            'has_anomalies': len(anomalies) > 0,
            'statistics': {
                'mean': round(mean, 2),
                'std_dev': round(std_dev, 2),
                'threshold': round(mean + self.sensitivity * std_dev, 2)
            }
        }
    
    def detect_trend_break(self, data: List[float]) -> Dict:
        """检测趋势断点"""
        if len(data) < 6:
            return {'trend_breaks': [], 'has_breaks': False}
        
        breaks = []
        window = 3
        
        for i in range(window, len(data) - window):
            # 计算前后窗口的平均值
            before_avg = sum(data[i-window:i]) / window
            after_avg = sum(data[i:i+window]) / window
            
            # 计算变化率
            if before_avg != 0:
                change_rate = (after_avg - before_avg) / before_avg
                
                # 超过50%的变化认为是趋势断点
                if abs(change_rate) > 0.5:
                    breaks.append({
                        'index': i,
                        'before_avg': round(before_avg, 2),
                        'after_avg': round(after_avg, 2),
                        'change_rate': round(change_rate * 100, 1),
                        'direction': 'up' if change_rate > 0 else 'down'
                    })
        
        return {
            'trend_breaks': breaks,
            'has_breaks': len(breaks) > 0
        }
