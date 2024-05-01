#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import math
import ccxt

from util.commons import robust
import platform



# 是否开启调试模式
Debug = False
proxy = {}
# 如果使用代理 注意替换IP和Port
# proxy  = {"http":  "http://127.0.0.1:23457", "https": "http://127.0.0.1:23457"}
# 并行取K线进程数
njob1  = 1
# 并行计算因子进程数
njob2  = 1
# 总资金杠杆数
trade_ratio = 1
# 最小可用K线数(如果不足该币种不参与交易)
min_kline_size = 999
# 币种黑名单(不参与交易)
black_list = []
# ===拆单配置
# 每次最大下单金额
max_one_order_amount = 1000
# 拆单后暂停时间(单位: 秒)
twap_interval = 2

# 资金费率文件名
fundingrate_filename = 'fundingRate.pkl'
# ===策略配置

class QuantConfig:
	def __init__(self, proxy, njob1, njob2, trade_ratio, min_kline_size, black_list,
			max_one_order_amount, twap_interval,  debug=False):
		self._initialize    	  = False
		self.proxy 		    	  = proxy
		self.njob1 		    	  = njob1
		self.njob2 		    	  = njob2
		self.trade_ratio          = trade_ratio
		self.min_kline_size 	  = min_kline_size
		self.black_list 	      = black_list
		self.max_one_order_amount = max_one_order_amount
		self.twap_interval 		  = twap_interval
		self.debug 		    	  = debug

	def _init_exchange(self):
		self.exchange = ccxt.binance({
			'timeout':   30000,
			'rateLimit': 10,
			'enableRateLimit': False,
			'options': {
			    'adjustForTimeDifference': True,  # ←---- resolves the timestamp
			    'recvWindow': 10000,
			},
		})
		self.exchange.proxies = self.proxy

	def initialize(self):
		if not self._initialize:
			self._init_exchange()
			self._initialize = True

	def load_market(self):
		exchange = self.exchange
		# 获取账户净值
		exchange_info = robust(exchange.fapiPublic_get_exchangeinfo, func_name='fapiPublic_get_exchangeinfo')  
		_symbol_list  = [x['symbol'] for x in exchange_info['symbols'] if x['status'] == 'TRADING']
		symbol_list   = [symbol for symbol in _symbol_list if symbol.endswith('USDT')]

		_temp_list = []
		for symbol in symbol_list:
			if symbol in ['COCOSUSDT', 'BTCSTUSDT', 'DREPUSDT', 'SUNUSDT']:
				continue
			if symbol.endswith(('DOWNUSDT', 'UPUSDT', 'BULLUSDT', 'BEARUSDT')):
				continue
			# 处理黑名单
			if symbol in self.black_list:
				continue
			_temp_list.append(symbol)
		self.symbol_list = _temp_list

		min_qty = {}
		price_precision = {}
		min_notional = {}

		for x in exchange_info['symbols']:
			_symbol = x['symbol']

			for _filter in x['filters']:
				if _filter['filterType'] == 'PRICE_FILTER':
					price_precision[_symbol] = int(math.log(float(_filter['tickSize']), 0.1))
				elif _filter['filterType'] == 'LOT_SIZE':
					min_qty[_symbol] = int(math.log(float(_filter['minQty']), 0.1))
				elif _filter['filterType'] == 'MIN_NOTIONAL':
					min_notional[_symbol] = float(_filter['notional'])

		self.min_qty = min_qty
		self.price_precision = price_precision
		self.min_notional = min_notional


quant = QuantConfig( proxy, njob1, njob2, trade_ratio, min_kline_size, black_list,
	max_one_order_amount, twap_interval, debug=Debug)

if platform.system() != 'Linux' and (quant.njob1 != 1 or quant.njob2 != 1):
	quant._init_exchange()

