import time, os, sys, ccxt, platform
import pandas as pd
from datetime import datetime
from datetime import timedelta
import dataframe_image as dfi
import traceback
import json
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# os配置 自动返回上级目录文件夹
_ = os.path.abspath(os.path.dirname(__file__))  # 返回当前文件路径
root_path = os.path.abspath(os.path.join(_, '../'))  # 返回根目录文件夹
sys.path.append(root_path)
# 在上级目录下继续导包
from function import  robust,fetch_binance_ticker_data
from api.position import update_symbol_info
from api.market import *
from util.commons import sleep_until_run_time
from binance import quant
# from replay_curve_1 import replay_curve_1
# from replay_curve import replay_curve


# pandas配置，方便print显示
pd_display_rows = 50
pd_display_cols = 100
pd_display_width = 5000
pd.set_option('display.max_rows', pd_display_rows)
pd.set_option('display.min_rows', pd_display_rows)
pd.set_option('display.max_columns', pd_display_cols)
pd.set_option('display.width', pd_display_width)
pd.set_option('display.max_colwidth', pd_display_width)
pd.set_option('display.unicode.ambiguous_as_wide', True)
pd.set_option('display.unicode.east_asian_width', True)
pd.set_option('expand_frame_repr', False)

# 警告抑制
import warnings
from warnings import simplefilter

pd.set_option('mode.chained_assignment', None)  # setcopywarning
warnings.filterwarnings("ignore")  # UserWarning
simplefilter(action='ignore', category=FutureWarning)  # FutureWarning


# 系统编码适配
# if platform.system() != 'Linux': sys.stdout.reconfigure(encoding='utf-8')


def run(symbol_list, exchange, run_time,username ,script_dir, key):
    """
    "assets": [
    {
        "asset": "USDT",        //资产
        "walletBalance": "23.72469206",  //余额
        "unrealizedProfit": "0.00000000",  // 未实现盈亏
        "marginBalance": "23.72469206",  // 保证金余额
        "maintMargin": "0.00000000",    // 维持保证金
        "initialMargin": "0.00000000",  // 当前所需起始保证金
        "positionInitialMargin": "0.00000000",  // 持仓所需起始保证金(基于最新标记价格)
        "openOrderInitialMargin": "0.00000000", // 当前挂单所需起始保证金(基于最新标记价格)
        "crossWalletBalance": "23.72469206",  //全仓账户余额
        "crossUnPnl": "0.00000000" // 全仓持仓未实现盈亏
        "availableBalance": "23.72469206",       // 可用余额
        "maxWithdrawAmount": "23.72469206",     // 最大可转出余额
        "marginAvailable": true,   // 是否可用作联合保证金
        "updateTime": 1625474304765  //更新时间
    },
    """

    # ===读取合约划转信息

    exchange_time = robust(exchange.fapiPublicGetTime, func_name='fapiPublicGetTime')  # 获取交易所时间
    timestamp = int(exchange_time['serverTime']) / 1000  # 毫秒级时间戳
    dt_object = datetime.fromtimestamp(timestamp)
    _dt_object = dt_object - timedelta(hours=1)  # 提前到上一小时
    s_time = int(_dt_object.timestamp() * 1000)
    # 准备参数
    params = {
        "asset": 'USDT',
        "startTime": s_time,
        "timestamp": int(round(time.time() * 1000)),
    }
    # 获取划转信息(取上一小时到当前时间的划转记录)
    account_info = exchange.sapi_get_futures_transfer(params=params)
    if account_info['total'] == 0 or account_info['total'] == '0':  # {'total': '0'}
        deposit = 0
        tranId = None
        status = None
    else:  # {'total': '1', 'rows': [{'timestamp': '1687291307000', 'asset': 'USDT', 'amount': '1', 'type': '2', 'status': 'CONFIRMED', 'tranId': '138990186568'}]}
        temp_df = pd.DataFrame(account_info['rows'])
        temp_df['direction'] = temp_df['type'].apply(
            lambda x: 1 if (x == '1' or x == 1) else (-1 if (x == '2' or x == 2) else 0))  # 入金为1，出金为-1
        temp_df['deposit'] = temp_df['direction'] * temp_df['amount'].astype('float')
        deposit = temp_df.iloc[-1]['deposit']  # 最后一次出入金 数量
        tranId = int(temp_df.iloc[-1]['tranId'])  # 最后一次出入金 操作ID
        status = str(temp_df.iloc[-1]['status'])  # 最后一次出入金 状态

    # ===U本位合约账户信息
    response = robust(exchange.fapiPrivateV2GetAccount, func_name='fapiPrivateV2GetAccount')
    response = pd.DataFrame(response['assets'])

    # 计算通过eth联合保证金模式下的保证金
    # 获取现货币种的最新价格
    symbol_last_price = fetch_binance_ticker_data(exchange, symbol_type='spot')
    anchored_eth_price = symbol_last_price['ETHUSDT']
    eth_value = float(response[response['asset'] == 'ETH']['walletBalance']) * anchored_eth_price
    anchored_btc_price = symbol_last_price['BTCUSDT']
    btc_value = float(response[response['asset'] == 'BTC']['walletBalance']) * anchored_btc_price
    anchored_bnb_price = symbol_last_price['BNBUSDT']
    bnb_value = float(response[response['asset'] == 'BNB']['walletBalance']) * anchored_bnb_price
    response = response[response['asset'] == 'USDT']
    walletBalance = float(response['walletBalance'])
    unrealizedProfit = float(response['unrealizedProfit'])
    marginBalance = float(response['marginBalance']) + eth_value + btc_value + bnb_value

    spot_equity, spot_position, spot_usdt, dust_spot = get_spot_position_and_equity(exchange)

    # ===获取账户实际持仓
    symbol_info = update_symbol_info(exchange, symbol_list)
    symbol_info = symbol_info[symbol_info['当前持仓量'] != 0]
    symbol_info.reset_index(inplace=True)
    symbol_info.columns = ['symbol', '当前持仓量']

    # ===计算持仓价值
    symbol_last_price = fetch_binance_ticker_data(exchange)
    symbol_last_price = pd.DataFrame(symbol_last_price)
    symbol_last_price.reset_index(inplace=True)
    symbol_last_price.columns = ['symbol', '最新价格']
    merged_df = symbol_info.merge(symbol_last_price, on='symbol', how='inner')
    merged_df['持仓价值'] = merged_df['当前持仓量'] * merged_df['最新价格']

    # ===计算多空持仓价值,杠杆率,多头持仓和空头持仓
    total_usdt = merged_df['持仓价值'].abs().sum()
    long_usdt = merged_df[merged_df['持仓价值'] > 0]['持仓价值'].sum()
    short_usdt = merged_df[merged_df['持仓价值'] < 0]['持仓价值'].sum()
    leverage = total_usdt / marginBalance  # 杠杆率 = (多头+空头) / 保证金余额（回测是这么算的）
    long_hold_symbol = ' '.join(merged_df[merged_df['持仓价值'] > 0]['symbol'].apply(str))
    short_hold_symbol = ' '.join(merged_df[merged_df['持仓价值'] < 0]['symbol'].apply(str))

    # ===保存到csv文件（净值数据）
    data1 = [
        {'time': pd.to_datetime(run_time), 'Ba': walletBalance, 'UnRePro': unrealizedProfit, 'marBa': marginBalance,
         'Leg_Ra': leverage, 'Pos_Val': total_usdt, 'L_Val': long_usdt, 'S_Val': short_usdt,
         'L_h': long_hold_symbol, 'S_h': short_hold_symbol,'spot':spot_equity , 'ac': key},
    ]

    df = pd.DataFrame(data1)

    # script_dir = os.path.dirname(os.path.abspath(__file__))  # 返回根目录文件夹
    filepath = os.path.join(script_dir, f'user/{username}/data/{key}.csv')
    hold_pic_path = os.path.join(script_dir, f'user/{username}/data/{key}.png')


    if not os.path.exists(filepath):
        df.to_csv(filepath, mode='w', header=True, index=False)
        dfi.export(df.tail(), hold_pic_path, table_conversion='matplotlib')  # 导出图片

        # send_wechat_work_img(hold_pic_path, url=url)  # 发送图片
    else:
        old_df = pd.read_csv(filepath)
        # old_df['ac']=key
        # old_df=old_df[['time','Ba','UnRePro','marBa','Leg_Ra','Pos_Val','L_Val','S_Val','L_h','S_h','ac']]
        new_df = pd.concat([old_df, df], ignore_index=True)
        new_df['time'] = pd.to_datetime(new_df['time'])
        new_df.sort_values(by='time', inplace=True)
        new_df.drop_duplicates(subset='time', keep='last', inplace=True)
        new_df.reset_index(drop=True, inplace=True)
        new_df.to_csv(filepath, mode='w', header=True, index=False)
        dfi.export(new_df.tail(), hold_pic_path, table_conversion='matplotlib')  # 导出图片
        # send_wechat_work_img(hold_pic_path, url=url)  # 发送图片
    print('1.', filepath, ' csv入库成功~')

    # ===保存到pkl文件（持仓数据）
    dict2 = {pd.to_datetime(run_time): merged_df}
    filepath1 = os.path.join(script_dir, f'user/{username}/data/{key}.pkl')
    if not os.path.exists(filepath1):
        pd.to_pickle(dict2, filepath1)
    else:
        dict1 = pd.read_pickle(filepath1)
        new_dict = {**dict1, **dict2}
        pd.to_pickle(new_dict, filepath1)
    print('2.', filepath1, ' pkl入库成功~')

    # ===保存到csv文件（充提记录）
    data3 = [
        {'time': pd.to_datetime(run_time) - timedelta(minutes=30), '出入金额': deposit, '操作ID': tranId,
         '订单状态': status},
    ]
    df = pd.DataFrame(data3)  # 转换为DataFrame
    # 判断csv文件是否存在
    filepath2 = os.path.join(script_dir, f'user/{username}/data/{key}_transfer.csv')
    if not os.path.exists(filepath2):
        df.to_csv(filepath2, mode='w', header=True, index=False)  # 新建csv文件
    else:
        old_df = pd.read_csv(filepath2)
        new_df = pd.concat([old_df, df], ignore_index=True)  # 合并新旧数据
        new_df['time'] = pd.to_datetime(new_df['time'])
        new_df.sort_values(by='操作ID', inplace=True)  # 按照操作ID排序
        new_df.drop_duplicates(subset='操作ID', keep='last', inplace=True)  # 去重，保留最后出现的重复项
        new_df.sort_values(by='time', inplace=True)  # 按照time排序
        new_df.drop_duplicates(subset='time', keep='last', inplace=True)  # 去重，保留最后出现的重复项
        new_df.reset_index(drop=True, inplace=True)  # 重置index索引
        new_df.to_csv(filepath2, mode='w', header=True, index=False)  # 写入csv文件
    print('3.', filepath2, ' csv入库成功~')
    k=key
    # replay_curve_1(k,username)
    # replay_curve(k)


def get_exchange(proxy=None, apiKey=None, secret=None):
    """创建交易所对象"""
    exchange = ccxt.binance({
        'apiKey': apiKey,
        'secret': secret,
        'timeout': 30000,
        'rateLimit': 10,
        'enableRateLimit': False,
        'options': {
            'adjustForTimeDifference': True,
            'recvWindow': 10000,
        },
    })
    if proxy: exchange.proxies = proxy
    return exchange


def load_account_config(config_file):
    """
    Load account configurations for all users from a JSON file.
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as file:
            config = json.load(file)
        # 返回所有用户的账户信息
        return config.get('users', {})
    except Exception as e:
        print(f"Error loading config file: {e}")
        return {}



if __name__ == '__main__':
    # ===初始化,加载市场,加载配置
    quant.initialize()
    quant.load_market()
    symbol_list = quant.symbol_list

    while True:
        try:
            # 加载配置文件
            script_dir = os.path.dirname(os.path.abspath(__file__))  # 返回根目录文件夹

            config_file = os.path.join(script_dir, 'users.json')  # JSON文件的路径
            users_dict = load_account_config(config_file)

            run_time = sleep_until_run_time('1h', if_sleep=True, cheat_seconds=-180)  # 生产
            # run_time = datetime.strptime('2024-01-26 03:30:00', "%Y-%m-%d %H:%M:%S")

            # 遍历每个用户及其账户
            for username, user_info in users_dict.items():
                print(username)
                account_dict = user_info.get('accounts', {})
                # 定义需要检查的基础路径
                base_path = os.path.join(script_dir, f'user/{username}')
                data_path = os.path.join(base_path, 'data')
                output_path = os.path.join(base_path, 'output')

                # 检查data目录是否存在，如果不存在则创建
                if not os.path.exists(data_path):
                    os.makedirs(data_path)

                # 检查output目录是否存在，如果不存在则创建
                if not os.path.exists(output_path):
                    os.makedirs(output_path)

                for account_name, account_info in account_dict.items():
                    print(account_name)
                    try:
                        apiKey = account_info['apiKey']
                        secret = account_info['secret']
                        proxy = None  # 生产环境
                        # proxy = {"http": "http://127.0.0.1:23457", "https": "http://127.0.0.1:23457"}  # 测试环境
                        exchange = get_exchange(proxy, apiKey, secret)  # 创建交易所对象)
                        run(symbol_list, exchange, run_time, username, script_dir, key=account_name)  # 启动主进程

                    except Exception as account_error:
                        print(f"账户 {account_name} 处理时发生错误: {account_error}")
                        # 可以在这里添加更多错误处理逻辑，如记录错误信息等

        except Exception as e:
            print('系统出错, 10s之后重新运行, 出错原因:')
            error_message = traceback.format_exc()
            print(error_message)  # 输出详细异常信息
            time.sleep(10)
        else:
            print('-' * 75, '\n', 'else被执行了, 休眠10秒进入下一次循环!')
            time.sleep(10)
            print()
        exit()
