import requests
import pandas as pd
from datetime import datetime, timedelta
import time

class BinanceClient:
    def __init__(self):
        self.base_url = "https://api.binance.com"
    
    def get_klines(self, symbol, interval='1h', limit=500, start_time=None, end_time=None):
        """
        获取K线数据
        :param symbol: 交易对符号，如 'BTCUSDT'
        :param interval: 时间间隔 1m,3m,5m,15m,30m,1h,2h,4h,6h,8h,12h,1d,3d,1w,1M
        :param limit: 返回数据条数，默认500，最大1000
        :param start_time: 开始时间戳（毫秒）
        :param end_time: 结束时间戳（毫秒）
        """
        endpoint = "/api/v3/klines"
        url = self.base_url + endpoint
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
            
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # 转换为DataFrame
            df = pd.DataFrame(data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 数据类型转换
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            # 时间转换
            df['datetime'] = pd.to_datetime(df['open_time'], unit='ms')
            df['date'] = df['datetime'].dt.date
            
            return df
            
        except requests.exceptions.RequestException as e:
            print(f"请求错误: {e}")
            return None
        except Exception as e:
            print(f"数据处理错误: {e}")
            return None
    
    def get_symbol_info(self, symbol):
        """获取交易对信息"""
        endpoint = "/api/v3/exchangeInfo"
        url = self.base_url + endpoint
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            for symbol_info in data['symbols']:
                if symbol_info['symbol'] == symbol:
                    return symbol_info
            return None
            
        except Exception as e:
            print(f"获取交易对信息错误: {e}")
            return None