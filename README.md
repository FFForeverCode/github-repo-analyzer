# GitHub 仓库分析工具

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

使用 PyGithub 分析热门开源项目的 commit 模式、贡献者活跃度等指标的工具。

## 📋 功能特性

- **📈 Commit 分析**
  - 每小时/每天/每月 commit 分布
  - 代码变更统计（增加/删除行数）
  - 提交频率分析
  - 连续提交天数统计

- **👥 贡献者分析**
  - 贡献者数量和分布
  - 贡献集中度（基尼系数）
  - 帕累托分析（二八定律）
  - 公司和地理位置分布

- **📬 Issue 分析**
  - Issue 状态分布（Open/Closed）
  - 解决时间统计
  - 标签分布
  - 创建者统计

- **🔀 Pull Request 分析**
  - PR 状态分布（合并/打开/关闭）
  - 合并时间统计
  - 代码审查统计
  - PR 大小分布

- **🎨 可视化**
  - 自动生成多种统计图表
  - 活动热力图
  - HTML 格式的交互式报告

## 🚀 快速开始

### 环境要求

- Python 3.8+
- GitHub Personal Access Token

### 安装

1. 克隆仓库

```bash
git clone https://github.com/your-username/github-repo-analyzer.git
cd github-repo-analyzer
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 配置 GitHub Token

```bash
# 复制示例配置文件
cp .env.example .env

# 编辑 .env 文件，填入你的 GitHub Token
# GITHUB_TOKEN=your_github_token_here
```

获取 Token：GitHub Settings → Developer settings → Personal access tokens → Generate new token

### 使用方法

#### 分析仓库

```bash
# 基本用法
python src/main.py analyze facebook/react

# 指定分析参数
python src/main.py analyze tensorflow/tensorflow --days 180 --max-commits 500

# 完整参数
python src/main.py analyze vuejs/vue \
    --days 365 \
    --max-commits 1000 \
    --max-contributors 100 \
    --max-issues 500 \
    --max-prs 300 \
    --output output
```

#### 搜索仓库

```bash
# 搜索热门仓库
python src/main.py search "machine learning" --limit 10 --sort stars

# 按语言搜索
python src/main.py search "web framework language:python" --sort forks
```

#### 查看仓库信息

```bash
python src/main.py info facebook/react
```

#### 查看 API 限制

```bash
python src/main.py rate-limit
```

### 命令行参数

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--days` | `-d` | 365 | 分析的时间范围（天数） |
| `--max-commits` | `-c` | 1000 | 最大获取的 commit 数量 |
| `--max-contributors` | `-u` | 100 | 最大获取的贡献者数量 |
| `--max-issues` | `-i` | 500 | 最大获取的 issue 数量 |
| `--max-prs` | `-p` | 300 | 最大获取的 PR 数量 |
| `--no-issues` | | False | 不分析 issues |
| `--no-prs` | | False | 不分析 pull requests |
| `--no-charts` | | False | 不生成图表 |
| `--output` | `-o` | output | 输出目录 |
| `--token` | `-t` | | GitHub Token |

## 📊 输出示例

### 生成的文件

```
output/
├── facebook_react_report.html    # HTML 报告
├── facebook_react_report.json    # JSON 数据
├── facebook_react_hourly.png     # 每小时commit分布图
├── facebook_react_weekday.png    # 工作日commit分布图
├── facebook_react_monthly_commits.png  # 每月趋势图
├── facebook_react_top_authors.png      # Top 贡献者柱状图
├── facebook_react_heatmap.png    # 活动热力图
└── ...
```

### HTML 报告预览

报告包含：
- 仓库基本信息（Stars、Forks、语言等）
- Commit 模式分析
- 贡献者活跃度分析
- Issue 统计分析
- Pull Request 分析
- 可视化图表

## 🏗️ 项目结构

```
github-repo-analyzer/
├── src/                             # 核心代码目录
│   ├── __init__.py
│   ├── main.py                      # 命令行入口
│   ├── config.py                    # 配置管理
│   ├── github_client.py             # GitHub API 客户端
│   ├── analyzer.py                  # 数据分析逻辑
│   ├── visualizer.py                # 图表生成
│   └── report_generator.py          # HTML 报告生成
├── tests/                           # 单元测试
│   ├── __init__.py
│   ├── test_config.py
│   └── test_analyzer.py
├── output/                          # 分析结果输出目录
├── requirements.txt                 # Python 依赖列表
├── .env.example                     # 环境变量模板
├── .gitignore               # Git 忽略文件
└── README.md                # 说明文档
```

## 🧪 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_config.py -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

## 📝 API 使用说明

### 作为库使用

```python
from src.github_client import GitHubClient
from src.analyzer import RepoAnalyzer
from src.visualizer import ChartGenerator
from src.report_generator import ReportGenerator

# 初始化客户端
client = GitHubClient(token="your_token")

# 执行分析
analyzer = RepoAnalyzer(client)
result = analyzer.full_analysis(
    repo_name="facebook/react",
    days=365,
    max_commits=1000
)

# 生成图表
chart_gen = ChartGenerator(output_dir="output")
charts = chart_gen.generate_all_charts(result, "facebook/react")

# 生成报告
report_gen = ReportGenerator(output_dir="output")
html_path = report_gen.generate_html_report(result, charts)
```

### 单独使用分析器

```python
from src.github_client import GitHubClient
from src.analyzer import CommitAnalyzer

client = GitHubClient(token="your_token")
commit_analyzer = CommitAnalyzer(client)

# 只分析 commit 模式
result = commit_analyzer.analyze_commit_patterns(
    repo_name="facebook/react",
    days=180,
    max_commits=500
)

print(f"总 Commit 数: {result['total_commits']}")
print(f"峰值提交时间: {result['hourly_distribution']['peak_hour']}:00")

## ⚠️ 注意事项

1. **API 限制**：GitHub API 有速率限制，未认证用户每小时 60 次，认证用户每小时 5000 次
2. **大型仓库**：分析大型仓库可能需要较长时间，建议适当调整 `max_commits` 等参数
3. **网络问题**：如遇网络问题，工具会自动重试3 次
4. **Token 权限**：建议为 Token 勾选 repo 和 read:org 权限

## 🔧 技术栈

- **PyGithub**: GitHub API 封装
- **Pandas**: 数据处理
- **Matplotlib/Seaborn**: 数据可视化
- **Click**: 命令行工具
- **Rich**: 终端美化
- **Jinja2**: HTML 模板

## 📄 许可证
本项目基于 MIT 许可证开源，详见项目中 LICENSE 文件。
