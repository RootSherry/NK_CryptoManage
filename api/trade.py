#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import time
import pandas as pd
import numpy  as np
from datetime import datetime, timedelta
from util.commons import robust


# 计算实际下单量
def cal_order_amount_old(symbol_info, select_coin, strategy_trade_usdt):
	select_coin = pd.merge(left=select_coin, right=strategy_trade_usdt, how='left')
	select_coin['目标下单量'] = select_coin['策略分配资金'] / select_coin['close'] * select_coin['方向']

	# 对下单量进行汇总
	symbol_info['目标下单量'] = select_coin.groupby('symbol')[['目标下单量']].sum()
	symbol_info['目标下单量'].fillna(value=0, inplace=True)
	symbol_info['目标下单份数'] = select_coin.groupby('symbol')[['方向']].sum()
	symbol_info['实际下单量'] = symbol_info['目标下单量'] - symbol_info['当前持仓量']

	# 删除实际下单量为0的币种
	symbol_info = symbol_info[symbol_info['实际下单量'] != 0]
	return symbol_info


# =====计算实际下单量
def cal_order_amount(symbol_info, select_coin, strategy_trade_usdt):
	select_coin = pd.merge(left=select_coin, right=strategy_trade_usdt, how='left').fillna(0)
	select_coin['目标下单量'] = select_coin['策略分配资金'] / select_coin['close'] * select_coin['方向']

	# 对下单量进行汇总
	symbol_info['目标下单量'] = select_coin.groupby('symbol')[['目标下单量']].sum()
	symbol_info['目标下单量'].fillna(value=0, inplace=True)
	symbol_info['目标下单份数'] = select_coin.groupby('symbol')[['方向']].sum()
	symbol_info['实际下单量'] = symbol_info['目标下单量'] - symbol_info['当前持仓量']

	select_coin.sort_values('candle_begin_time',inplace=True)
	symbol_info['close'] = select_coin.groupby('symbol')[['close']].last()
	symbol_info['实际下单资金'] = symbol_info['实际下单量'] * symbol_info['close']
	del symbol_info['close']

	symbol_info = symbol_info[symbol_info['实际下单量'] != 0]

	return symbol_info



def get_twap_symbol_info_list(symbol_info, Max_one_order_amount):
	'''
	对超额订单进行拆分,并进行调整,尽可能每批中子订单、每批订单让多空平衡
	:param symbol_info 原始下单信息
	:param Max_one_order_amount:单次下单最大金额
	'''
	df_long  = symbol_info[symbol_info['实际下单量'] >= 0].copy()
	df_short = symbol_info[symbol_info['实际下单量'] <  0].copy()
	df_long['下单金额排名']  = df_long['实际下单资金'].rank(ascending=False,method='first')
	df_short['下单金额排名'] = df_short['实际下单资金'].rank(method='first')
	symbol_info = pd.concat([df_long, df_short]).sort_values(['下单金额排名','实际下单资金'], ascending=[True, False])

	twap_symbol_info_list = [symbol_info.copy()]
	num         = 0
	is_twap     = True if max(abs(symbol_info['实际下单资金'])) > Max_one_order_amount else False
	safe_amount = 0.1 * Max_one_order_amount

	while is_twap:
		symbol_info    = twap_symbol_info_list[num]
		add_order_list = []
		drop_list      = []
		for i in range(symbol_info.shape[0]):
			symbol = symbol_info.index[i]
			# 第 i 行
			order  = symbol_info.iloc[i:i+1]

			# order.iat[0, 4] 实际下单资金
			_real_amount = order.iat[0, 4]
			if abs(_real_amount) > Max_one_order_amount:
				ratio     = (Max_one_order_amount - safe_amount)/abs(_real_amount)
				add_order = order.copy()
				add_order[['当前持仓量', '目标下单量', '目标下单份数', '实际下单量', '实际下单资金']] = add_order[['当前持仓量', '目标下单量', '目标下单份数', '实际下单量', '实际下单资金']] * (1 - ratio)
				# symbol_info.iloc[i, :-1]   第 i 行
				symbol_info.iloc[i, :-1] = symbol_info.iloc[i,:-1] * ratio
				add_order_list.append(add_order)

		symbol_info.drop(drop_list, inplace=True)
		twap_symbol_info_list[num] = symbol_info.copy()
		add_df  = pd.concat(add_order_list)
		twap_symbol_info_list.append(add_df.copy())
		is_twap = True if max(abs(add_df['实际下单资金'])) > Max_one_order_amount else False
		num += 1

	#print(f'Twap批次: {len(twap_symbol_info_list)}\n')

	# 以下代码块主要功能为调整不同批次间的多空平衡问题，资金量不是特别大的老板可以注释掉
	'''*******************************************************************************'''
	bl = []
	for x in twap_symbol_info_list:
		bl.append([
			round(abs(x['实际下单资金']).sum(), 1),
			round(x['实际下单资金'].sum(),1)
		])

	_summary_df = pd.DataFrame(bl, columns=['下单金额', '多空失衡金额'])
	is_adjust   = False

	for j in range(len(twap_symbol_info_list)):
		adjust_df     = pd.DataFrame()
		main_order_df = twap_symbol_info_list[j].copy()

		for i in range(5, 25, 1):
			if abs(main_order_df.iloc[:int(len(main_order_df)*(i-2)/i)]['实际下单资金'].sum()) > 1300:
				adjust_df     = main_order_df.iloc[int(len(main_order_df)*(i-2)/i):]
				main_order_df = main_order_df.iloc[:int(len(main_order_df)*(i-2)/i)]
				#print((i-2)/i, f'\n第 {j+1} 批twap订单需要调整\n')
				is_adjust = True
				twap_symbol_info_list[j] = main_order_df.copy()
				break
			else:
				continue

		for i in range(adjust_df.shape[0]):
			temp = [x['实际下单资金'].sum() for x in twap_symbol_info_list[j+1:]]

			if temp:
				max_ind = temp.index(max(temp))
				min_ind = temp.index(min(temp))

				if adjust_df.iat[i, 4] < 0:
					twap_symbol_info_list[max_ind+j+1] = twap_symbol_info_list[max_ind+j+1].append(adjust_df.iloc[i:i+1])
				else:
					twap_symbol_info_list[min_ind+j+1] = twap_symbol_info_list[min_ind+j+1].append(adjust_df.iloc[i:i+1])
			else:
				pass

	if is_adjust:
		bl = []
		for x in twap_symbol_info_list:
			bl.append([round(abs(x['实际下单资金']).sum(),1),round(x['实际下单资金'].sum(),1)])
		summary_df = pd.DataFrame(bl,columns=['下单金额','多空失衡金额'])

	'''*******************************************************************************'''
	all_df = pd.concat(twap_symbol_info_list)

	# 多空分离，该计算可能误报
	try:
		assert abs(all_df['目标下单份数'].sum()) < 1e-6
	except Exception as e:
		print(abs(all_df['目标下单份数'].sum()))
		# print('Twap订单生产出错')

	return twap_symbol_info_list


# 下单
def place_order(exchange, symbol_info, symbol_last_price, min_qty, price_precision, min_notional):
	for symbol, row in symbol_info.dropna(subset=['实际下单量']).iterrows():
		try:
			if symbol not in min_qty:
				continue

			# 计算下单量：按照最小下单量向下取整
			quantity = row['实际下单量']
			quantity = float(f'{quantity:.{min_qty[symbol]}f}')
			# 检测是否需要开启只减仓
			reduce_only = np.isnan(row['目标下单份数']) or row['目标下单量'] * quantity < 0

			quantity = abs(quantity)  # 下单量取正数
			if quantity == 0:
				print(symbol, quantity, '实际下单量为0，不下单')
				continue

			# 计算下单方向、价格
			if row['实际下单量'] > 0:
				side = 'BUY'
				#price = symbol_last_price[symbol] * 1.02
				price = symbol_last_price[symbol] * 1.015
			else:
				side = 'SELL'
				#price = symbol_last_price[symbol] * 0.98
				price = symbol_last_price[symbol] * 0.985

			# 对下单价格这种最小下单精度
			price = float(f'{price:.{price_precision[symbol]}f}')

			if symbol not in price_precision:
				continue

			if quantity * price < min_notional.get(symbol, 5) and not reduce_only:
				print('quantity * price < 5')
				quantity = 0
				continue

			# 下单参数
			params = {
				'symbol': 		 symbol,
				'side': 		 side,
				'type': 		 'LIMIT',
				'price': 		 price,
				'quantity':      quantity,
				'clientOrderId': str(time.time()),
				'timeInForce':   'GTC',
				'reduceOnly':    reduce_only
			}
			# 下单
			print('下单参数：', params)
			open_order = robust(exchange.fapiPrivate_post_order, params=params, func_name='fapiPrivate_post_order')
			print('下单完成，下单信息：', open_order, '\n')
		except Exception as e:
			print(e)
			continue







