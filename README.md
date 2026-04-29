<h1>A股量化分析系统</h1>
<p>一个完整的 A 股量化分析 Web 应用，支持股票行情分析、风险指标计算、技术指标分析、GARCH 波动率建模、策略回测等功能。</p>
<h2>功能特性</h2>
<ul>
<li><strong>数据获取</strong>: 支持 AKShare (免费) 和 Tushare 两种数据源，自动降级</li>
<li><strong>行情分析</strong>: 收盘价走势、成交量、累计收益率、价格分位数</li>
<li><strong>风险指标</strong>: 最大回撤、VaR、CVaR、Sharpe/Sortino/Calmar 比率</li>
<li><strong>基准比较</strong>: Alpha、Beta、信息比率、跟踪误差、捕获率</li>
<li><strong>OLS/CAPM</strong>: 市场模型回归分析</li>
<li><strong>时间序列检验</strong>: ADF、KPSS、Ljung-Box、ARCH-LM 检验</li>
<li><strong>GARCH 模型</strong>: GARCH(1,1)、EGARCH、GJR-GARCH 波动率建模</li>
<li><strong>技术指标</strong>: MA、MACD、RSI、KDJ、布林带、ATR</li>
<li><strong>基本面分析</strong>: PE/PB/ROE/毛利率等财务指标</li>
<li><strong>策略回测</strong>: 双均线、RSI、布林带策略回测</li>
<li><strong>综合评分</strong>: 8 维度量化评分系统</li>
<li><strong>报告导出</strong>: HTML、Markdown、JSON、CSV 格式</li>
</ul>
<h2>安装</h2>
<h3>方式一：使用安装脚本 (推荐)</h3>
<pre><code># Windows
双击运行 setup.bat

# 或命令行
cd stock_quant_analyzer
setup.bat
</code></pre>
<h3>方式二：手动安装</h3>
<pre><code>cd stock_quant_analyzer
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
</code></pre>
<h2>运行</h2>
<h3>Windows</h3>
<pre><code># 方式一：双击「A股量化分析系统.bat」（推荐，首次自动安装环境）
# 方式二：双击「A股量化分析系统.exe」（GUI 启动器）
# 方式三：命令行
cd stock_quant_analyzer
.venv\Scripts\activate
streamlit run app.py
</code></pre>
<h3>Linux / 云服务器</h3>
<pre><code>cd stock_quant_analyzer
chmod +x start_linux.sh
./start_linux.sh
</code></pre>
<p>首次运行会自动创建虚拟环境并安装依赖。之后访问 http://localhost:8501</p>
<p><strong>后台运行（云服务器推荐）</strong>：</p>
<pre><code>nohup ./start_linux.sh &gt; streamlit.log 2&gt;&amp;1 &amp;
# 查看日志
tail -f streamlit.log
# 停止
pkill -f streamlit
</code></pre>
<p><strong>自定义端口</strong>：</p>
<pre><code># 编辑 start_linux.sh，修改最后一行的端口
.venv/bin/python -m streamlit run app.py --server.port 8080 --server.address 0.0.0.0
</code></pre>
<p>浏览器将自动打开 http://localhost:8501</p>
<h2>配置</h2>
<h3>Tushare Token</h3>
<p>方式一：在 Web 界面侧边栏输入 Token（推荐）</p>
<p>方式二：创建 <code>.env</code> 文件</p>
<pre><code>cp .env.example .env
# 编辑 .env 文件，填入你的 Tushare Token
</code></pre>
<h3>配置文件</h3>
<p><code>config.yaml</code> 包含默认参数配置：</p>
<pre><code>default:
  benchmark: &#34;000300&#34;  # 默认基准指数 (沪深300)
  rf_annual: 0.02      # 无风险利率 2%
  trading_days: 252    # 年交易日数
</code></pre>
<h2>使用说明</h2>
<ol>
<li>在侧边栏输入股票名称和代码（如 &#34;延江股份&#34; / &#34;300658&#34;）</li>
<li>选择分析区间（默认近 3 年）</li>
<li>选择基准指数（默认沪深300）</li>
<li>选择数据源（默认自动选择）</li>
<li>配置高级参数（可选）</li>
<li>点击「开始分析」按钮</li>
<li>查看各 Tab 页面的分析结果</li>
<li>在「报告导出」Tab 导出报告</li>
</ol>
<h2>项目结构</h2>
<pre><code>stock_quant_analyzer/
├── app.py                    # Streamlit 主界面
├── requirements.txt          # 依赖清单
├── config.yaml              # 默认配置
├── .env.example             # 环境变量模板
├── src/
│   ├── config.py            # 配置管理
│   ├── data/                # 数据获取层
│   │   ├── akshare_fetcher.py
│   │   ├── tushare_fetcher.py
│   │   ├── data_manager.py  # 统一入口
│   │   └── validators.py    # 数据校验
│   ├── analysis/            # 分析模块
│   │   ├── preprocessing.py
│   │   ├── performance.py
│   │   ├── risk_metrics.py
│   │   └── ... (14个模块)
│   ├── visualization/       # 可视化
│   │   ├── charts.py        # Plotly 图表
│   │   └── style.py         # 样式配置
│   ├── report/              # 报告生成
│   │   ├── generator.py
│   │   └── templates/
│   └── utils/               # 工具函数
├── tests/                   # 测试文件
├── outputs/                 # 输出目录
└── data_cache/              # 数据缓存
</code></pre>
<h2>常见问题</h2>
<h3>Q: 数据获取失败怎么办？</h3>
<p>A:</p>
<ol>
<li>检查股票代码是否正确</li>
<li>检查网络连接</li>
<li>尝试切换数据源</li>
<li>若使用 Tushare，确认 Token 有效且有足够积分</li>
</ol>
<h3>Q: 为什么某些基本面数据缺失？</h3>
<p>A: 部分股票的基本面数据可能不完整，或数据源接口返回异常。程序会自动标记缺失数据。</p>
<h3>Q: GARCH 模型不收敛怎么办？</h3>
<p>A:</p>
<ol>
<li>确保数据量足够（建议 &gt; 500 个交易日）</li>
<li>尝试切换分布假设（normal/t）</li>
<li>模型不收敛时程序会自动降级到滚动波动率</li>
</ol>
<h3>Q: 结果和其他软件不同？</h3>
<p>A: 不同软件的计算方法可能略有差异：</p>
<ul>
<li>收益率计算方法（简单 vs 对数）</li>
<li>年化系数（252 vs 250 vs 260）</li>
<li>复权方式差异</li>
</ul>
<h2>免责声明</h2>
<p>本系统基于历史数据自动生成分析报告，仅供学习和研究参考，不构成任何投资建议。投资者应独立判断并承担投资风险。历史表现不代表未来收益。</p>
<h2>许可证</h2>
<p>MIT License</p>
