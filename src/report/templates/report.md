<h1>{{ meta.stock_name }}({{ meta.stock_code }}) 量化分析报告</h1>
<h2>基本信息</h2>
<ul>
<li><strong>分析区间</strong>: {{ meta.start_date }} ~ {{ meta.end_date }}</li>
<li><strong>基准指数</strong>: {{ meta.benchmark }}</li>
<li><strong>数据源</strong>: {{ meta.data_source }}</li>
<li><strong>生成时间</strong>: {{ generated_at }}</li>
</ul>
<hr>
<p>{% set sections = [
(&#34;performance&#34;, &#34;行情表现分析&#34;),
(&#34;return_distribution&#34;, &#34;收益率分布分析&#34;),
(&#34;risk_metrics&#34;, &#34;风险指标分析&#34;),
(&#34;benchmark_comparison&#34;, &#34;基准比较分析&#34;),
(&#34;ols_capm&#34;, &#34;OLS/CAPM 回归分析&#34;),
(&#34;time_series_tests&#34;, &#34;时间序列检验&#34;),
(&#34;garch&#34;, &#34;GARCH 波动率模型&#34;),
(&#34;technical_indicators&#34;, &#34;技术指标分析&#34;),
(&#34;fundamental&#34;, &#34;基本面分析&#34;),
(&#34;liquidity&#34;, &#34;流动性分析&#34;),
(&#34;backtesting&#34;, &#34;策略回测&#34;),
(&#34;score&#34;, &#34;综合评分&#34;),
] %}</p>
<p>{% for key, title in sections %}
{% set r = results.get(key, {}) %}
{% if r and r.get(&#34;success&#34;) %}</p>
<h2>{{ loop.index }}. {{ title }}</h2>
<p>{% if r.get(&#34;interpretation&#34;) %}
{{ r.interpretation }}
{% endif %}</p>
<p>{% set data = r.get(&#34;data&#34;, {}) %}
{% if data %}
| 指标 | 值 |
|------|-----|
{% for k, v in data.items() %}
{% if v is not mapping and v is not sequence %}
| {{ k }} | {{ v }} |
{% endif %}
{% endfor %}
{% endif %}</p>
<hr>
<p>{% endif %}
{% endfor %}</p>
<p>{% set conclusion = results.get(&#34;conclusion&#34;, {}) %}
{% if conclusion %}</p>
<h2>核心结论</h2>
<p>{% for s in conclusion.get(&#34;summary&#34;, []) %}</p>
<ul>
<li>{{ s }}
{% endfor %}</li>
</ul>
<p>{% if conclusion.get(&#34;strengths&#34;) %}</p>
<h3>优点</h3>
<p>{% for s in conclusion.strengths %}</p>
<ul>
<li>{{ s }}
{% endfor %}
{% endif %}</li>
</ul>
<p>{% if conclusion.get(&#34;risks&#34;) %}</p>
<h3>风险点</h3>
<p>{% for s in conclusion.risks %}</p>
<ul>
<li>{{ s }}
{% endfor %}
{% endif %}</li>
</ul>
<p>{% if conclusion.get(&#34;limitations&#34;) %}</p>
<h3>局限性</h3>
<p>{% for s in conclusion.limitations %}</p>
<ul>
<li>{{ s }}
{% endfor %}
{% endif %}
{% endif %}</li>
</ul>
<hr>
<h2>免责声明</h2>
<p>本报告基于历史数据自动生成，仅供学习和研究参考，不构成任何投资建议。投资者应独立判断并承担投资风险。历史表现不代表未来收益。</p>
<p>本报告使用的模型和指标均有其假设前提和局限性，实际投资决策应结合更多因素综合考量。</p>
