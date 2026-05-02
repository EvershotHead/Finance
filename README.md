# A股智能选股与多因子深度分析系统 (StockAnalyzer)

> 本项目是 [Finance](https://github.com/EvershotHead/Finance) 仓库的 `StockAnalyzer` 分支。

## 功能介绍

本系统包含两大核心模块，整合在同一个 Streamlit 多页面应用中：

### 模块一：智能选股与多因子筛选系统

从全市场几千只 A 股中，通过多因子筛选、评分排序，帮用户找到候选股票。

- 全 A 股股票池获取和管理
- 批量行情数据获取和本地缓存
- 8 种预设筛选模板（风险厌恶型、价值低估型、成长质量型、短线强势型等）
- 自定义多级筛选条件（估值、收益、风险、流动性、基本面、技术）
- 多因子评分系统（收益、风险、流动性、估值、质量、成长、技术）
- 入选原因和风险提示自动生成
- 候选股票批量对比（雷达图、柱状图）
- 导出 CSV/Excel/JSON/Markdown/HTML 报告
- 点击"一键深度分析"跳转到单股深度分析页面

### 模块二：单股深度分析

对选定股票进行全方位深度量化分析，包含 13 个分析维度：

- 行情表现分析（累计收益、年化收益、波动率）
- 收益率分布分析（正态性检验、QQ 图）
- 风险指标分析（VaR、CVaR、最大回撤、Sharpe/Sortino/Calmar）
- 基准比较分析（与沪深300等指数对比）
- OLS/CAPM 回归分析
- 时间序列检验（ADF、Ljung-Box、ARCH 效应）
- GARCH 波动率模型
- 技术指标分析（MA、MACD、RSI、布林带、ATR）
- 基本面分析（财务指标、盈利能力）
- 流动性分析（成交额、换手率）
- 策略回测（双均线、RSI、布林带策略）
- 综合评分（0-100 分多维度评分）
- 报告导出（JSON/Markdown/HTML/CSV）

## 安装

```bash
cd StockAnalyzer
pip install -r requirements.txt
```

### 可选依赖

- **DuckDB**: `pip install duckdb` — 用于高效查询 feature store
- **Tushare**: `pip install tushare` — 可选数据源，需要配置 token

## 运行

```bash
streamlit run app.py
```

运行后在浏览器中打开，使用左侧导航栏选择功能页面。

## 数据源配置

### AKShare（默认）

无需额外配置，直接使用。AKShare 提供免费的 A 股行情数据。

### Tushare（可选）

1. 注册 [Tushare Pro](https://tushare.pro/) 获取 token
2. 在项目根目录创建 `.env` 文件：
   ```
   TUSHARE_TOKEN=your_token_here
   ```
3. 或者设置环境变量 `TUSHARE_TOKEN`

## 使用指南

### 1. 更新本地数据

首次使用需要更新数据：

1. 进入"智能选股"页面
2. 在左侧边栏点击"一键完整更新"
3. 等待数据获取完成（首次可能需要几分钟）

### 2. 使用预设筛选

1. 在侧边栏选择"预设模板"
2. 选择模板（如"风险厌恶型"、"价值低估型"等）
3. 调整基础参数（股票池、Top N 等）
4. 点击"运行筛选"

### 3. 使用自定义筛选

1. 在侧边栏选择"自定义筛选"
2. 设置估值、收益、风险、流动性等筛选条件
3. 点击"运行筛选"

### 4. 查看结果

- **筛选总览**: 漏斗图、行业分布、评分分布
- **候选股票**: 详细表格、入选原因、风险提示
- **风险收益**: 散点图、排行
- **估值基本面**: PE/PB 分布、ROE 对比
- **批量对比**: 选择多只股票进行雷达图对比

### 5. 导出结果

在"导出"标签页可以下载：
- CSV 文件
- Excel 文件
- JSON 数据
- Markdown 报告
- HTML 报告

### 6. 深度分析

在候选股票列表中，点击"一键深度分析"按钮跳转到单股深度分析页面。

深度分析页面功能：
- 自动填入从选股页面传来的股票代码和名称
- 点击"开始分析"运行全部分析模块
- 通过 13 个 Tab 查看分析结果
- 支持导出分析报告
- 点击"返回选股"回到智能选股页面

## 项目结构

```
StockAnalyzer/
├── app.py                          # 主入口
├── pages/                          # Streamlit 页面
│   ├── 1_📊_单股深度分析.py        # 单股深度分析（整合 FinanceWeb）
│   ├── 2_🔍_智能选股.py            # 智能选股与多因子筛选
│   ├── 3_⚖️_批量对比.py            # 多股对比
│   └── 4_📄_筛选报告.py            # 筛选报告导出
├── src/                            # 选股系统源码
│   ├── data/                       # 数据获取层
│   │   ├── akshare_fetcher.py      # AKShare 接口
│   │   ├── tushare_fetcher.py      # Tushare 接口（可选）
│   │   ├── data_manager.py         # 统一数据管理
│   │   ├── universe_manager.py     # 股票池管理
│   │   ├── batch_fetcher.py        # 批量获取
│   │   └── data_quality.py         # 数据清洗
│   ├── storage/                    # 存储层
│   │   ├── parquet_store.py        # Parquet 读写
│   │   ├── duckdb_store.py         # DuckDB 查询
│   │   └── feature_store.py        # Feature Store
│   ├── screener/                   # 筛选引擎
│   │   ├── factor_library.py       # 因子计算库
│   │   ├── feature_engineering.py  # 特征工程
│   │   ├── filter_dsl.py           # 筛选 DSL
│   │   ├── screening_engine.py     # 筛选引擎
│   │   ├── scoring.py              # 评分系统
│   │   ├── presets.py              # 预设模板
│   │   ├── explanations.py         # 原因/风险解释
│   │   └── comparison.py           # 对比逻辑
│   ├── jobs/                       # 更新任务
│   ├── visualization/              # 选股可视化
│   ├── report/                     # 选股报告
│   └── utils/                      # 工具函数
├── finweb_src/                     # 深度分析源码（原 FinanceWeb）
│   ├── config.py                   # 深度分析配置
│   ├── data/                       # 数据获取层（独立）
│   │   ├── data_manager.py         # 数据管理器
│   │   ├── akshare_fetcher.py      # AKShare 接口
│   │   ├── tushare_fetcher.py      # Tushare 接口
│   │   ├── validators.py           # 代码验证
│   │   └── cache.py                # 数据缓存
│   ├── analysis/                   # 分析模块（16 个）
│   │   ├── performance.py          # 行情表现
│   │   ├── risk_metrics.py         # 风险指标
│   │   ├── ols_capm.py             # OLS/CAPM
│   │   ├── volatility_models.py    # GARCH 模型
│   │   ├── technical_indicators.py # 技术指标
│   │   ├── fundamental.py          # 基本面
│   │   ├── liquidity.py            # 流动性
│   │   ├── backtesting.py          # 策略回测
│   │   ├── scoring.py              # 综合评分
│   │   └── ...                     # 更多分析模块
│   ├── visualization/              # 深度分析可视化
│   ├── report/                     # 报告生成
│   │   ├── generator.py            # 报告生成器
│   │   ├── interpretation.py       # 结论解读
│   │   └── templates/              # 报告模板
│   └── utils/                      # 工具函数
├── configs/                        # 选股配置文件
│   ├── factor_config.yaml          # 因子参数
│   ├── screener_presets.yaml       # 预设模板
│   └── scoring_weights.yaml        # 评分权重
├── config.yaml                     # 深度分析配置
├── data/                           # 本地数据目录
│   ├── raw/                        # 原始数据
│   ├── clean/                      # 清洗数据
│   ├── feature_store/              # 选股因子
│   └── screen_results/             # 筛选结果
├── outputs/                        # 输出目录
│   ├── screener_exports/           # 选股导出
│   ├── screener_reports/           # 选股报告
│   ├── json/                       # 深度分析 JSON
│   ├── reports/                    # 深度分析报告
│   └── data/                       # 深度分析数据
├── tests/                          # 测试
├── requirements.txt                # 依赖清单
├── .env.example                    # 环境变量模板
└── README.md                       # 本文件
```

## 架构说明

### 双命名空间设计

本项目采用双命名空间设计，将选股系统和深度分析系统完全隔离：

- `src/` — 选股系统的源码，所有导入使用 `from src.xxx`
- `finweb_src/` — 深度分析系统的源码（原 FinanceWeb），所有导入使用 `from finweb_src.xxx`

两个命名空间拥有独立的数据获取层、分析引擎和可视化模块，互不干扰。

### 数据独立

- 选股系统和深度分析系统各自独立获取数据
- 选股系统的数据存储在 `data/` 目录
- 深度分析系统的数据缓存在 `data_cache/` 目录
- 两个系统的数据互不影响

### 页面导航

```
app.py (主页)
├── 智能选股 (pages/2) ──[一键深度分析]──→ 单股深度分析 (pages/1)
│                                              │
│                                              ←──[返回选股]──┘
├── 批量对比 (pages/3)
└── 筛选报告 (pages/4)
```

## 常见问题

### 为什么没有筛选结果？

- 可能数据未更新，请先点击"一键完整更新"
- 筛选条件过严，尝试放宽条件
- 某些财务数据可能缺失，降低"最小数据质量分数"

### 为什么某些财务字段为空？

- AKShare 免费接口对部分财务数据有限制
- 资金流数据目前接口不稳定，可能不可用
- 系统会自动降低缺失数据股票的质量评分

### 为什么数据更新较慢？

- 全市场 5000+ 只股票的数据需要逐个获取
- 系统内置限流机制避免被封
- 可以使用"限制更新数量"进行调试
- 首次更新后，后续更新会使用缓存

### 为什么结果和证券软件不同？

- 数据源可能不同（AKShare vs 证券软件）
- 复权方式可能不同
- 计算窗口和方法可能有差异
- 本系统仅供参考，以证券软件数据为准

## 数据限制

- 数据来源于 AKShare/Tushare，可能存在延迟
- 部分财务数据可能不完整
- 资金流数据接口不稳定
- 历史数据默认 3 年，可在配置中修改
- 所有分析基于历史数据，不代表未来表现

## 免责声明

**本系统仅供学习和辅助分析使用，不构成任何投资建议。**

- 股票市场存在风险，投资需谨慎
- 过去的业绩不代表未来表现
- 本系统不推荐买入、卖出或持有任何股票
- 所有筛选结果和分析报告仅供参考
- 投资决策应基于个人风险承受能力和专业判断
