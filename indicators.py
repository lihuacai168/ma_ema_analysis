import pandas as pd
import numpy as np

def calculate_ma(data, period):
    """
    计算简单移动平均线 (MA)
    :param data: 价格数据 (Series)
    :param period: 周期
    :return: MA值
    """
    return data.rolling(window=period).mean()

def calculate_ema(data, period):
    """
    计算指数移动平均线 (EMA)
    :param data: 价格数据 (Series)
    :param period: 周期
    :return: EMA值
    """
    return data.ewm(span=period, adjust=False).mean()

def detect_crossover(short_line, long_line, tolerance=0.01):
    """
    检测均线交叉点
    :param short_line: 短期均线
    :param long_line: 长期均线
    :param tolerance: 容差百分比，默认1%
    :return: 交叉点信息DataFrame
    """
    crossovers = []
    
    for i in range(1, len(short_line)):
        if pd.isna(short_line.iloc[i]) or pd.isna(long_line.iloc[i]) or \
           pd.isna(short_line.iloc[i-1]) or pd.isna(long_line.iloc[i-1]):
            continue
            
        current_short = short_line.iloc[i]
        current_long = long_line.iloc[i]
        prev_short = short_line.iloc[i-1]
        prev_long = long_line.iloc[i-1]
        
        # 计算交叉点的相对差异
        current_diff = abs(current_short - current_long) / current_long
        
        # 检测金叉（短期均线向上穿越长期均线）
        if (prev_short <= prev_long and current_short > current_long and 
            current_diff <= tolerance):
            crossovers.append({
                'index': i,
                'type': 'golden_cross',
                'short_value': current_short,
                'long_value': current_long,
                'difference_pct': current_diff * 100
            })
        
        # 检测死叉（短期均线向下穿越长期均线）
        elif (prev_short >= prev_long and current_short < current_long and 
              current_diff <= tolerance):
            crossovers.append({
                'index': i,
                'type': 'death_cross',
                'short_value': current_short,
                'long_value': current_long,
                'difference_pct': current_diff * 100
            })
    
    return pd.DataFrame(crossovers)

def add_all_indicators(df, ma_periods=[20, 60, 120], ema_periods=[20, 60, 120]):
    """
    为K线数据添加所有技术指标
    :param df: K线数据DataFrame
    :param ma_periods: MA周期列表
    :param ema_periods: EMA周期列表
    :return: 添加指标后的DataFrame
    """
    result_df = df.copy()
    
    # 添加MA指标
    for period in ma_periods:
        result_df[f'MA_{period}'] = calculate_ma(result_df['close'], period)
    
    # 添加EMA指标
    for period in ema_periods:
        result_df[f'EMA_{period}'] = calculate_ema(result_df['close'], period)
    
    return result_df

def detect_line_convergence(df, tolerance=0.01):
    """
    检测6条均线的密集区域 - 当所有均线之间的差异都在容差范围内时
    :param df: 包含MA和EMA指标的DataFrame
    :param tolerance: 容差百分比，默认1%
    :return: 均线密集点信息DataFrame
    """
    convergences = []
    
    # 定义所有均线
    all_lines = ['MA_20', 'EMA_20', 'MA_60', 'EMA_60', 'MA_120', 'EMA_120']
    
    # 确保所有列都存在
    if not all(col in df.columns for col in all_lines):
        return pd.DataFrame()
    
    for i in range(len(df)):
        # 跳过包含NaN的行
        if any(pd.isna(df[col].iloc[i]) for col in all_lines):
            continue
        
        # 获取当前时刻所有均线的值
        current_values = [df[col].iloc[i] for col in all_lines]
        
        # 计算所有均线之间的最大差异百分比
        min_value = min(current_values)
        max_value = max(current_values)
        
        if min_value > 0:  # 避免除零错误
            max_diff_pct = (max_value - min_value) / min_value
            
            # 如果所有均线都在容差范围内，标记为密集区域
            if max_diff_pct <= tolerance:
                # 计算平均价格作为标记位置
                avg_price = sum(current_values) / len(current_values)
                
                # 根据当前价格位置判断趋势类型
                current_close = df['close'].iloc[i]
                
                # 简单判断：如果收盘价在均线上方，标记为多头密集；否则为空头密集
                if current_close > avg_price:
                    convergence_type = 'bullish_convergence'
                else:
                    convergence_type = 'bearish_convergence'
                
                convergences.append({
                    'index': i,
                    'type': convergence_type,
                    'avg_price': avg_price,
                    'max_diff_pct': max_diff_pct,
                    'convergence_strength': 1 - (max_diff_pct / tolerance)  # 越接近0差异，强度越高
                })
    
    return pd.DataFrame(convergences)

def find_all_crossovers(df, tolerance=0.01):
    """
    找出均线密集区域 - 检测6条均线密集的位置
    :param df: 包含MA和EMA指标的DataFrame
    :param tolerance: 容差百分比
    :return: 均线密集点的字典
    """
    crossovers = {}
    
    # 使用新的6线密集检测逻辑
    convergences = detect_line_convergence(df, tolerance)
    if not convergences.empty:
        crossovers['LINE_CONVERGENCE'] = convergences
    
    return crossovers