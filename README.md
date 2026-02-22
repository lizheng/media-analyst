# media-analyst

MediaCrawler 的 Streamlit Web UI 包装器，提供友好的可视化界面来配置和运行爬虫任务。

## 功能特性

- **多平台支持**: 小红书、抖音、快手、B站、微博、贴吧、知乎
- **多种爬取模式**: 搜索模式、详情模式、作者模式
- **数据解析**: 自动解析爬取的 JSON 数据，支持去重和预览
- **实时输出**: 查看爬虫运行日志和进度
- **URL 提取**: 从抖音分享文本中提取视频链接

## 快速开始

### 环境要求

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) 包管理器

### 安装

```bash
# 克隆仓库
git clone <repository-url>
cd media-analyst

# 安装依赖
uv sync

# 安装 prek git hooks（可选但推荐）
uv tool install prek
prek install
```

### 配置 MediaCrawler 路径

首次运行时需要配置 MediaCrawler 路径：

```bash
# 方式1: 在 UI 中设置（侧边栏"MediaCrawler 路径"）
# 方式2: 使用环境变量
export MEDIA_CRAWLER_PATH=/path/to/MediaCrawler
```

### 运行应用

```bash
# 启动 Streamlit 服务
uv run streamlit run src/media_analyst/ui/app.py

# 访问 http://localhost:8501
```

## 开发指南

### 项目结构

```
media-analyst/
├── src/media_analyst/
│   ├── core/           # 业务逻辑层（纯函数，无副作用）
│   │   ├── models.py   # Pydantic 数据模型
│   │   ├── params.py   # CLI 参数构建
│   │   ├── config.py   # 配置常量
│   │   ├── parser.py   # 数据解析
│   │   └── url_parser.py  # URL 提取
│   ├── shell/          # IO 层（副作用封装）
│   │   └── runner.py   # 爬虫进程管理
│   └── ui/             # 界面层
│       ├── app.py      # 主应用
│       ├── parser_page.py  # 数据解析页面
│       └── persistence.py  # 配置持久化
└── tests/              # 测试
    ├── unit/           # 单元测试
    ├── integration/    # 集成测试
    ├── ui/             # UI 测试
    └── real_crawler/   # 端到端测试
```

### 架构原则

**Functional Core, Imperative Shell (FCIS)**:
- `core/` 层包含纯函数，无副作用，易于测试
- `shell/` 层封装所有 IO 操作（文件、网络、进程）
- `ui/` 层处理用户交互，调用 Core 和 Shell

### 代码质量工具

项目使用 **prek**（Rust 版 pre-commit）作为 Git Hook：

```bash
# 安装 prek
uv tool install prek

# 安装 hooks
prek install

# 查看配置的 hooks
prek list

# 手动运行
prek run --all-files
```

**Hooks 内容**:
- **Ruff**: 代码 linting 和自动修复
- **Ruff Format**: 代码格式化
- **Pytest**: 运行单元测试、集成测试和 UI 测试

### 本地开发命令

```bash
# 代码检查
uv run ruff check .

# 自动修复
uv run ruff check . --fix

# 格式化
uv run ruff format .

# 运行测试（分层）
uv run pytest tests/unit -v          # 单元测试（最快）
uv run pytest tests/integration -v   # 集成测试
uv run pytest tests/ui -v            # UI 测试

# 运行所有测试
uv run pytest tests/unit tests/integration tests/ui -v

# 覆盖率报告
uv run pytest tests/unit tests/integration tests/ui --cov --cov-report=term
```

### 提交代码

```bash
# 正常提交流程（hooks 自动运行）
git add .
git commit -m "feat: add new feature"

# 跳过 hooks（仅在紧急情况下使用）
git commit --no-verify -m "hotfix"
```

## 技术栈

- **UI**: Streamlit
- **数据验证**: Pydantic v2
- **测试**: pytest + streamlit.testing
- **包管理**: uv
- **代码质量**: Ruff + prek

## 许可证

[许可证信息]
