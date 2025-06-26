import dash
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta

from binance_client import BinanceClient
from indicators import add_all_indicators, find_all_crossovers

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# 初始化Binance客户端
binance_client = BinanceClient()

# 获取所有交易对
print("正在获取交易对列表...")
all_symbols = binance_client.get_all_symbols()
symbol_options = [{'label': f"{symbol['baseAsset']}/USDT ({symbol['symbol']})", 'value': symbol['symbol']} 
                  for symbol in all_symbols]
print(f"已获取 {len(symbol_options)} 个交易对")

# 定义布局
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("加密货币K线图 - MA/EMA双均线分析", className="text-center mb-4"),
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("交易对设置", className="card-title"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("交易对:"),
                            dcc.Dropdown(
                                id="symbol-dropdown",
                                options=symbol_options,
                                value="SOLUSDT",
                                searchable=True,
                                placeholder="搜索交易对...",
                                clearable=False,
                                style={'fontSize': '14px'}
                            )
                        ], width=4),
                        dbc.Col([
                            dbc.Label("时间间隔:"),
                            dcc.Dropdown(
                                id="interval-dropdown",
                                options=[
                                    {'label': '1小时', 'value': '1h'},
                                    {'label': '4小时', 'value': '4h'},
                                    {'label': '1天', 'value': '1d'},
                                    {'label': '1周', 'value': '1w'}
                                ],
                                value='4h'
                            )
                        ], width=3),
                        dbc.Col([
                            dbc.Label("数据条数:"),
                            dbc.Input(
                                id="limit-input",
                                type="number",
                                value=600,
                                min=50,
                                max=1000
                            )
                        ], width=3),
                        dbc.Col([
                            dbc.Label("密集容差(%):"),
                            dbc.Input(
                                id="tolerance-input",
                                type="number",
                                value=3.0,
                                min=0.1,
                                max=10.0,
                                step=0.1
                            )
                        ], width=2)
                    ]),
                    html.Br(),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("更新图表", id="update-button", color="primary", className="me-2"),
                            dbc.Button("重置", id="reset-button", color="secondary")
                        ])
                    ])
                ])
            ])
        ], width=12)
    ], className="mb-4"),
    
    dbc.Row([
        dbc.Col([
            dcc.Loading(
                id="loading",
                children=[
                    dcc.Graph(id="kline-chart", style={'height': '1000px'})
                ],
                type="default",
            )
        ], width=12)
    ]),
    
    dbc.Row([
        dbc.Col([
            html.Div(id="crossover-info", className="mt-3")
        ], width=12)
    ])
], fluid=True)

# 重置按钮回调
@callback(
    [Output('symbol-dropdown', 'value'),
     Output('interval-dropdown', 'value'),
     Output('limit-input', 'value'),
     Output('tolerance-input', 'value')],
    [Input('reset-button', 'n_clicks')],
    prevent_initial_call=True
)
def reset_inputs(n_clicks):
    if n_clicks:
        return "SOLUSDT", "4h", 600, 3.0
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update

@callback(
    [Output('kline-chart', 'figure'),
     Output('crossover-info', 'children')],
    [Input('symbol-dropdown', 'value'),
     Input('interval-dropdown', 'value'),
     Input('limit-input', 'value'),
     Input('tolerance-input', 'value'),
     Input('update-button', 'n_clicks')]
)
def update_chart(symbol, interval, limit, tolerance, update_clicks):
    # 如果参数为None，使用默认值
    if symbol is None:
        symbol = "SOLUSDT"
    if interval is None:
        interval = "4h"
    if limit is None:
        limit = 600
    if tolerance is None:
        tolerance = 3.0
    
    try:
        # 获取K线数据
        df = binance_client.get_klines(symbol, interval, limit)
        if df is None or df.empty:
            return go.Figure(), dbc.Alert("无法获取数据，请检查交易对名称", color="danger")
        
        # 添加技术指标
        df = add_all_indicators(df)
        
        # 检测交叉点
        crossovers = find_all_crossovers(df, tolerance/100)
        
        # 创建单一图表 - 只显示K线
        fig = go.Figure()
        
        # 添加K线图
        fig.add_trace(
            go.Candlestick(
                x=df['datetime'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='K线',
                increasing_line_color='#00ff00',
                decreasing_line_color='#ff0000'
            )
        )
        
        # 添加MA线
        colors_ma = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        for i, period in enumerate([20, 60, 120]):
            col_name = f'MA_{period}'
            if col_name in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df['datetime'],
                        y=df[col_name],
                        mode='lines',
                        name=f'MA{period}',
                        line=dict(color=colors_ma[i], width=2)
                    )
                )
        
        # 添加EMA线
        colors_ema = ['#FF9FF3', '#54A0FF', '#5F27CD']
        for i, period in enumerate([20, 60, 120]):
            col_name = f'EMA_{period}'
            if col_name in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df['datetime'],
                        y=df[col_name],
                        mode='lines',
                        name=f'EMA{period}',
                        line=dict(color=colors_ema[i], width=2, dash='dash')
                    )
                )
        
        # 添加均线密集区域背景色
        for pair_name, convergences_df in crossovers.items():
            if not convergences_df.empty:
                # 将连续的密集区域合并
                bullish_zones = []
                bearish_zones = []
                
                current_bullish_start = None
                current_bearish_start = None
                
                for i, (_, convergence) in enumerate(convergences_df.iterrows()):
                    conv_time = df.iloc[convergence['index']]['datetime']
                    
                    if convergence['type'] == 'bullish_convergence':
                        # 处理空头区域结束
                        if current_bearish_start is not None:
                            bearish_zones.append((current_bearish_start, prev_time))
                            current_bearish_start = None
                        
                        # 开始或继续多头区域
                        if current_bullish_start is None:
                            current_bullish_start = conv_time
                    
                    else:  # bearish_convergence
                        # 处理多头区域结束
                        if current_bullish_start is not None:
                            bullish_zones.append((current_bullish_start, prev_time))
                            current_bullish_start = None
                        
                        # 开始或继续空头区域
                        if current_bearish_start is None:
                            current_bearish_start = conv_time
                    
                    prev_time = conv_time
                
                # 处理最后的区域
                if current_bullish_start is not None:
                    bullish_zones.append((current_bullish_start, prev_time))
                if current_bearish_start is not None:
                    bearish_zones.append((current_bearish_start, prev_time))
                
                # 添加多头密集背景
                for start_time, end_time in bullish_zones:
                    fig.add_vrect(
                        x0=start_time, x1=end_time,
                        fillcolor="rgba(0, 102, 255, 0.1)",
                        layer="below",
                        line_width=0,
                        annotation_text="多头密集",
                        annotation_position="top left",
                        annotation=dict(font_size=10, font_color="blue")
                    )
                
                # 添加空头密集背景
                for start_time, end_time in bearish_zones:
                    fig.add_vrect(
                        x0=start_time, x1=end_time,
                        fillcolor="rgba(255, 102, 0, 0.1)",
                        layer="below",
                        line_width=0,
                        annotation_text="空头密集",
                        annotation_position="top left",
                        annotation=dict(font_size=10, font_color="orange")
                    )
        
        
        # 计算Y轴范围，确保所有均线都可见
        all_ma_values = []
        for period in [20, 60, 120]:
            ma_col = f'MA_{period}'
            ema_col = f'EMA_{period}'
            if ma_col in df.columns:
                all_ma_values.extend(df[ma_col].dropna().tolist())
            if ema_col in df.columns:
                all_ma_values.extend(df[ema_col].dropna().tolist())
        
        # 添加K线的高低点
        all_ma_values.extend(df['high'].tolist())
        all_ma_values.extend(df['low'].tolist())
        
        if all_ma_values:
            y_min = min(all_ma_values) * 0.98  # 留出2%的边距
            y_max = max(all_ma_values) * 1.02  # 留出2%的边距
        else:
            y_min = None
            y_max = None

        # 更新布局
        fig.update_layout(
            title=f'{symbol} - {interval} K线图分析',
            xaxis_rangeslider_visible=False,
            height=1000,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            xaxis_title="时间",
            yaxis_title="价格",
            yaxis=dict(
                range=[y_min, y_max] if y_min and y_max else None,
                autorange=True,
                fixedrange=False
            ),
            xaxis=dict(
                autorange=True,
                fixedrange=False
            )
        )
        
        # 生成均线密集信息
        crossover_info = []
        total_convergences = 0
        
        for pair_name, convergences_df in crossovers.items():
            if not convergences_df.empty:
                total_convergences += len(convergences_df)
                bullish_convergences = len(convergences_df[convergences_df['type'] == 'bullish_convergence'])
                bearish_convergences = len(convergences_df[convergences_df['type'] == 'bearish_convergence'])
                
                # 构建最近密集信息
                recent_convergence = convergences_df.iloc[-1]
                convergence_type_name = "多头密集" if recent_convergence['type'] == 'bullish_convergence' else "空头密集"
                recent_info = f"最近密集: {convergence_type_name} (强度: {recent_convergence['convergence_strength']:.1%})"
                
                crossover_info.append(
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("均线密集区域", className="card-title"),
                            html.P([
                                f"多头密集: {bullish_convergences} 次 | 空头密集: {bearish_convergences} 次",
                                html.Br(),
                                recent_info
                            ])
                        ])
                    ], color="primary", outline=True, className="mb-2")
                )
        
        if total_convergences == 0:
            crossover_info = [dbc.Alert("在当前设置下未检测到均线密集区域", color="info")]
        else:
            crossover_info.insert(0, 
                dbc.Alert(f"总共检测到 {total_convergences} 个均线密集区域", color="success")
            )
        
        return fig, crossover_info
        
    except Exception as e:
        error_fig = go.Figure()
        error_fig.add_annotation(
            text=f"错误: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return error_fig, dbc.Alert(f"发生错误: {str(e)}", color="danger")

if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)