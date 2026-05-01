# A股智能选股筛选报告

**生成时间**: {{ generated_at }}

## 1. 筛选概况

- 筛选前股票数量: {{ result.total_before }}
- 筛选后股票数量: {{ result.total_after }}

## 2. 筛选条件

{% for stage in result.stage_results %}
- **{{ stage.name }}**: {{ stage.count_before }} → {{ stage.count_after }} (剔除 {{ stage.removed }})
{% endfor %}

## 3. 候选股票列表

| 排名 | 代码 | 名称 | 行业 | 收盘价 | PE(TTM) | 20日收益 | 综合评分 |
|------|------|------|------|--------|---------|----------|----------|
{% for _, row in candidates.head(50).iterrows() %}
| {{ loop.index }} | {{ row.get('stock_code', '') }} | {{ row.get('stock_name', '') }} | {{ row.get('industry', '') }} | {{ "%.2f"|format(row.get('latest_close', 0)) }} | {{ "%.2f"|format(row.get('pe_ttm', 0)) }} | {{ "%.2f"|format(row.get('ret_20d', 0) * 100) }}% | {{ "%.1f"|format(row.get('total_score', 0)) }} |
{% endfor %}

## 4. 免责声明

**免责声明**: 本报告仅供学习和辅助分析使用，不构成任何投资建议。股票市场存在风险，投资需谨慎。过去的业绩不代表未来表现。本系统不推荐买入、卖出或持有任何股票。
