#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import time
import pandas as pd
from datetime import datetime, timedelta

from util.commons import robust

# =====获取持仓
# 获取币安账户的实际持仓
def update_symbol_info(exchange, symbol_list):
    # 获取原始数据
    position_risk = robust(exchange.fapiPrivateV2_get_positionrisk, func_name='fapiPrivateV2_get_positionrisk')

    # 将原始数据转化为dataframe
    position_risk = pd.DataFrame(position_risk, dtype='float')

    # 整理数据
    position_risk.rename(columns={'positionAmt': '当前持仓量'}, inplace=True)
    position_risk = position_risk[position_risk['当前持仓量'] != 0]  # 只保留有仓位的币种
    position_risk.set_index('symbol', inplace=True)  # 将symbol设置为index

    # 创建symbol_info
    symbol_info = pd.DataFrame(index=symbol_list, columns=['当前持仓量'])
    symbol_info['当前持仓量'] = position_risk['当前持仓量']
    symbol_info['当前持仓量'].fillna(value=0, inplace=True)

    return symbol_info


def _query_leverage(exchange):
    position_risk = robust(exchange.fapiPrivateV2_get_positionrisk, func_name='fapiPrivateV2_get_positionrisk')
    return dict([(row['symbol'], int(row['leverage'])) for row in position_risk])    


def reset_leverage(exchange, max_leverage=2):
    results = {}

    leverage_info = _query_leverage(exchange)
    for symbol, leverage in leverage_info.items():
        if leverage!=max_leverage:
            #设置杠杆
            robust(
                exchange.fapiPrivate_post_leverage, 
                params={'symbol': symbol, 'leverage': max_leverage}, 
                func_name='fapiPrivate_post_leverage'
            )

    time.sleep(5)

    leverage_info = _query_leverage(exchange)
    for symbol, leverage in leverage_info.items():
        if leverage!=max_leverage:
            raise RuntimeError(symbol, 'default leverage not equal', max_leverage)

    print('All symbols max_leverage is', max_leverage)






