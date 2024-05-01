#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import time
import pandas as pd
from datetime import datetime, timedelta
from multiprocessing import Pool
import traceback

from util.commons import robust, robust_


# =====获取数据
# 获取单个币种的1小时数据
def fetch_binance_swap_candle_data(exchange, symbol, run_time, limit=1500):
    try:
        start_time_dt = run_time - timedelta(hours=limit)
        params = {
            'symbol':    symbol, 
            'interval':  '1h', 
            'limit':     limit,
            'startTime': int(time.mktime(start_time_dt.timetuple())) * 1000
        }
        # ===call KLine API
        kline = robust_(exchange.fapiPublic_get_klines, params=params, func_name='fapiPublic_get_klines')
        # 将数据转换为DataFrame
        columns = [
            'candle_begin_time', 
            'open', 
            'high', 
            'low', 
            'close', 
            'volume', 
            'close_time', 
            'quote_volume', 
            'trade_num',
            'taker_buy_base_asset_volume', 
            'taker_buy_quote_asset_volume', 
            'ignore'
        ]
        df = pd.DataFrame(kline, columns=columns, dtype='float')

        # 兼容时区
        utc_offset = int(time.localtime().tm_gmtoff/60/60)
        # 整理数据
        df['candle_begin_time'] = pd.to_datetime(df['candle_begin_time'], unit='ms') + pd.Timedelta(hours=utc_offset)  # 时间转化为东八区
        df['symbol'] = symbol  # 添加symbol列
        columns = [
            'symbol', 
            'candle_begin_time', 
            'open', 
            'high', 
            'low', 
            'close', 
            'volume', 
            'quote_volume',
            'trade_num',
            'taker_buy_base_asset_volume', 
            'taker_buy_quote_asset_volume',
        ]
        df = df[columns]

        df.sort_values(by=['candle_begin_time'], inplace=True)
        df.drop_duplicates(subset=['candle_begin_time'], keep='last', inplace=True)
        # 删除runtime那行的数据，如果有的话
        df = df[df['candle_begin_time'] < run_time]
        df.reset_index(drop=True, inplace=True)
        
        return symbol, df
    except Exception as e:
        print(traceback.format_exc())
        return symbol, None
        

# 并行获取所有币种永续合约数据的1小时K线数据
def fetch_all_binance_swap_candle_data(exchange, symbol_list, run_time, njob1):
    # 创建参数列表
    arg_list = [(exchange, symbol, run_time) for symbol in symbol_list]

    if njob1 == 1:    
        # 调试模式下，循环获取数据
        result = []
        for arg in arg_list:
            (exchange, symbol, run_time) = arg
            res = fetch_binance_swap_candle_data(exchange, symbol, run_time)
            result.append(res)
    else:
        # 多进程获取数据
        with Pool(processes=njob1) as pl:
            # 利用starmap启用多进程信息
            result = pl.starmap(fetch_binance_swap_candle_data, arg_list)
  
    return dict(result)


# 获取当前资金费率
def fetch_fundingrate(exchange):
    data = robust(exchange.fapiPublic_get_premiumindex, func_name='fapiPublic_get_premiumindex')
    data = [[row['time'], row['symbol'], row['lastFundingRate']] for row in data]
    df = pd.DataFrame(data, columns=['candle_begin_time', 'symbol', 'fundingRate'], dtype='float')
    # 处理日期格式
    df['candle_begin_time'] = (df['candle_begin_time']//1000) * 1000
    df['candle_begin_time'] = pd.to_datetime(df['candle_begin_time'], unit='ms')
    df['candle_begin_time'] = df['candle_begin_time'].apply(lambda x: pd.to_datetime(x.to_pydatetime().replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")))
    utc_offset = int(time.localtime().tm_gmtoff/60/60)
    df['candle_begin_time'] = df['candle_begin_time'] + pd.Timedelta(hours=utc_offset) - pd.Timedelta(hours=1)
    df.sort_values(by=['candle_begin_time', 'symbol'], inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


# 获取币安的ticker数据
def fetch_binance_ticker_data(exchange, symbol_type='swap'):
    # 获取所有币种的ticker数据
    if symbol_type == 'swap':
        tickers = retry_wrapper(exchange.fapiPublic_get_ticker_price, func_name='获取所有合约币种的ticker数据')
    else:
        tickers = retry_wrapper(exchange.public_get_ticker_price, func_name='获取所有现货币种的ticker数据')
    tickers = pd.DataFrame(tickers, dtype=float)
    tickers.set_index('symbol', inplace=True)

    return tickers['price']

# ===重试机制
def retry_wrapper(func, params={}, func_name='', retry_times=5, sleep_seconds=5, if_exit=True):
    """
    需要在出错时不断重试的函数，例如和交易所交互，可以使用本函数调用。
    :param func:            需要重试的函数名
    :param params:          参数
    :param func_name:       方法名称
    :param retry_times:     重试次数
    :param sleep_seconds:   报错后的sleep时间
    :param if_exit:         报错是否退出程序
    :return:
    """
    for _ in range(retry_times):
        try:
            result = func(params=params)
            return result
        except Exception as e:
            print(func_name, '报错，报错内容：', str(e), '程序暂停(秒)：', sleep_seconds)
            time.sleep(sleep_seconds)
    else:
        if if_exit:
            raise ValueError(func_name, '报错重试次数超过上限，程序退出。')

def get_spot_position(exchange):
    """
    获取账户净值

    :param exchange:    交易所对象

    :return:
        swap_equity=1000  (表示账户里资金总价值为 1000U )

    """
    # 获取U本位合约账户净值(不包含未实现盈亏)
    position_df = retry_wrapper(exchange.private_get_account, func_name='获取现货账户净值')  # 获取账户净值
    position_df = pd.DataFrame(position_df['balances'], dtype=float)
    position_df = position_df[position_df['free'] != 0]

    position_df.rename(columns={'asset': 'symbol', 'free': '当前持仓量'}, inplace=True)

    # 保留指定字段
    position_df = position_df[['symbol', '当前持仓量']]

    return position_df

def get_spot_position_and_equity(exchange):
    # =获取现货持仓
    spot_position = get_spot_position(exchange)
    # 获取现货最新价格
    spot_price = fetch_binance_ticker_data(exchange, symbol_type='spot')
    if spot_position.empty:
        spot_usdt = 0
        spot_equity = 0
        dust_spot = pd.DataFrame()
    else:
        if 'USDT' in spot_position['symbol'].to_list():
            spot_usdt = spot_position.loc[spot_position['symbol'] == 'USDT', '当前持仓量'].iloc[0]  # 获取当前账号U的数量
        else:
            spot_usdt = 0
        spot_position.loc[spot_position['symbol'] != 'USDT', 'symbol'] = spot_position['symbol'] + 'USDT'  # 追加USDT后缀，方便计算usdt价值
        has_price_spot = list(set(spot_position['symbol'].to_list()) & set(spot_price.index))  # 保留含有USDT报价的现货
        spot_position = spot_position[spot_position['symbol'].isin(has_price_spot)]  # 过滤掉没有报价的现货
        spot_position.set_index('symbol', inplace=True)
        spot_position['当前价格'] = spot_price
        spot_position['仓位价值'] = spot_position['当前持仓量'] * spot_position['当前价格']
        # BNB在现货持仓需要剔除
        if 'BNBUSDT' in spot_position.index:
            # BNB会去购买合约，不会存在现货仓位
            spot_position.drop('BNBUSDT', inplace=True)
        dust_spot = spot_position[spot_position['仓位价值'] < 5]  # 无法下单的碎单
        spot_position = spot_position[spot_position['仓位价值'] > 5]  # 过滤掉一些无法下的碎单，不计入持仓价值中

        spot_equity = spot_position['仓位价值'].sum() + spot_usdt  # 计算当前现货账户总价值，按U计算

    return spot_equity, spot_position, spot_usdt, dust_spot

