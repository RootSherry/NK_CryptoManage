#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import time
import pandas as pd
from datetime import datetime, timedelta

def calculate_anchored_total_wallet_balance(balance, anchored_btc_price, anchored_eth_price,anchored_bnb_price):
    # 从balance字典中提取资产信息
    assets = balance['assets']

    # 初始化各资产价值
    btc_value = 0
    eth_value = 0
    bnb_value = 0
    usdt_value = 0

    # 遍历资产并计算各资产价值
    for asset in assets:
        if asset['asset'] == 'BTC':
            btc_value = float(asset['walletBalance']) * anchored_btc_price
        elif asset['asset'] == 'ETH':
            eth_value = float(asset['walletBalance']) * anchored_eth_price
        elif asset['asset'] == 'BNB':
            bnb_value = float(asset['walletBalance']) * anchored_bnb_price# 假设BNB的价格为1，否则需要提供BNB的实际价格
        elif asset['asset'] == 'USDT':
            usdt_value = float(asset['walletBalance'])

    # 计算锚定价格下的totalWalletBalance
    anchored_total_wallet_balance = btc_value + eth_value + bnb_value + usdt_value
    return anchored_total_wallet_balance

# 计算每个策略分配的资金
def cal_strategy_trade_usdt(strategy_list, trade_usdt):
    df = pd.DataFrame()
    # 策略的个数
    strategy_num = len(strategy_list)
    # 遍历策略
    for strategy in strategy_list:
        c_factor    = strategy['c_factor']
        hold_period = strategy['hold_period']
        select_coin_num = strategy['select_coin_num']

        offset_num = int(hold_period[:-1])
        balance = trade_usdt/strategy_num/2/offset_num/select_coin_num
        for offset in range(offset_num):
            df.loc[f'{c_factor}_{hold_period}_{offset}H', '策略分配资金'] = balance

    df.reset_index(inplace=True)
    df.rename(columns={'index': 'key'}, inplace=True)

    return df






