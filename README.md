# A股智能选股与多因子筛选系统 (StockFilter)

> 本项目是 [Finance](https://github.com/EvershotHead/Finance) 仓库的 `StockFilter` 分支。

## 功能介绍

本系统包含两大核心模块：

1. **智能选股与多因子筛选系统** — 从全市场几千只 A 股中，通过多因子筛选、评分排序，帮用户找到候选股票
2. **单股深度分析** — 对选定股票进行行情、收益率、风险、OLS/CAPM/GARCH、技术指标、基本面等深度分析

### 智能选股功能

- 全 A 股股票池获取和管理
- 批量行情数据获取和本地缓存
- 8 种预设筛选模板（风险厌恶型、价值低估型、成长质量型、短线强势型等）
- 自定义多级筛选条件（估值、收益、风险、流动性、基本面、技术）
- 多因子评分系统（收益、风险、流动性、估值、质量、成长、技术）
- 入选原因和风险提示自动生成
- 候选股票批量对比（雷达图、柱状图）
- 导出 CSV/Excel/JSON/Markdown/HTML 报告
- 点击"一键深度分析"跳转到单股分析页面

## 安装

```bash
cd stock_quant_analyzer
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

## 项目结构

```
stock_quant_analyzer/
├── app.py                          # 主入口
├── pages/                          # Streamlit 页面
│   ├── 1_📊_单股深度分析.py
│   ├── 2_🔍_智能选股.py
│   ├── 3_⚖️_批量对比.py
│   └── 4_📄_筛选报告.py
├── src/
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
│   ├── visualization/              # 可视化
│   ├── report/                     # 报告生成
│   └── utils/                      # 工具函数
├── configs/                        # 配置文件
│   ├── factor_config.yaml          # 因子参数
│   ├── screener_presets.yaml       # 预设模板
│   └── scoring_weights.yaml        # 评分权重
├── data/                           # 本地数据
│   ├── raw/                        # 原始数据
│   ├── clean/                      # 清洗数据
│   ├── feature_store/              # 选股因子
│   └── screen_results/             # 筛选结果
└── tests/                          # 测试
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

### 为什么资金流数据不可用？

- 资金流数据接口不稳定，系统会标记"资金流数据暂不可用"
- 这不影响主要筛选功能

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

## 后续扩展方向

- [ ] 单股深度分析模块（OLS/CAPM/GARCH）
- [ ] 定时任务自动更新数据
- [ ] 更多因子（行业因子、事件因子）
- [ ] 因子回测功能
- [ ] 机器学习选股模型
- [ ] 实时行情推送
- [ ] 多市场支持（港股、美股）
