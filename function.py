import pandas as pd
import time
import matplotlib.pyplot as plt
import io
import base64
import json
import math

def replenish_bnb(exchange, balance, amount_t=10):
    if amount_t == 0:
        return

    min_bnb = 0.001  # 该参数在BNB达到 10000 USDT之前有效
    amount_bnb = float(balance[balance['asset'] == 'BNB']['balance'].iloc[0])
    print(f"当前账户剩余{amount_bnb} BNB")  # 合约账户

    if amount_bnb < min_bnb:
        spot_bnb_amount = get_spot_balance(exchange, 'BNB')  # 现货账户
        print(f"当前现货账户持有{spot_bnb_amount} BNB")

        if spot_bnb_amount < min_bnb:
            print("从现货市场买入10 USDT等值BNB并转入合约账户")

            spot_usdt_amount = get_spot_balance(exchange, 'USDT')
            if spot_usdt_amount < amount_t:
                transfer_future_to_spot(exchange, 'USDT', amount_t - spot_usdt_amount)
            spot_buy_quote(exchange, 'BNBUSDT', amount_t)

            time.sleep(2)

            retry = 0
            # 如果获取到现货账户BNB持仓扔小于最小BNB量，说明币安账户未更新，在行情剧烈波动的情况下存在这种情况
            # 睡眠20秒后重新获取BNB现货账户余额，重试15次（5分钟）后仍未更新则放弃
            while spot_bnb_amount < min_bnb and retry < 3:
                spot_bnb_amount = get_spot_balance(exchange, 'BNB')
                if spot_bnb_amount > min_bnb:
                    break
                else:
                    retry += 1
                    time.sleep(3)

        transfer_spot_to_future(exchange, 'BNB', spot_bnb_amount)
        print(f"成功买入{spot_bnb_amount} BNB并转入U本位合约账户")


def get_spot_balance(exchange, asset):
    """
    获取现货账户指定币种持仓
    :param exchange:
    :param asset:
    :return:
    """
    account = robust(exchange.private_get_account, func_name='private_get_account')
    # print(account)
    balance = account['balances']
    balance = pd.DataFrame(balance)
    # 如果子账号没有使用过现货账户，此处会返回空值
    if balance.empty:
        return 0.0

    amount = float(balance[balance['asset'] == asset]['free'])
    # print(f'查询到现货账户有{amount} {asset}')
    return amount


def transfer_future_to_spot(exchange, asset, amount, type):
    params = {
        'type': type,  # 1：现货至u本位合约；2：u本位合约至现货
        'asset': asset,
        'amount': amount,
    }
    return robust(exchange.sapiPostFuturesTransfer, params=params, func_name='sapiPostFuturesTransfer')


def get_all_spot_balances(exchange):
    """
    获取所有现货账户的持仓
    :param exchange:
    :return:
    """
    account = robust(exchange.private_get_account, func_name='private_get_account')
    balances = account['balances']
    balances_df = pd.DataFrame(balances)

    # 如果子账号没有使用过现货账户，此处会返回空值
    if balances_df.empty:
        return {}

    all_balances = {}
    for index, row in balances_df.iterrows():
        asset = row['asset']
        amount = float(row['free'])
        if amount != 0.0:  # 过滤掉数量为0的币种
            # print(f'查询到现货账户有{amount} {asset}')
            all_balances[asset] = amount

    return all_balances

def fetch_binance_ticker_data(exchange, symbol_type='swap'):
    # 获取所有币种的ticker数据
    if symbol_type == 'swap':
        tickers = retry_wrapper(exchange.fapiPublic_get_ticker_price, func_name='获取所有合约币种的ticker数据')
    else:
        tickers = retry_wrapper(exchange.public_get_ticker_price, func_name='获取所有现货币种的ticker数据')
    # print(tickers)

    # 创建 DataFrame
    tickers_df = pd.DataFrame(tickers)
    # 将 price 列转换为浮点数
    tickers_df['price'] = tickers_df['price'].astype(float)
    tickers_df.set_index('symbol', inplace=True)

    return tickers_df['price']


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
def spot_buy_quote(exchange, symbol, quote_amount):
    params = {
        'symbol': symbol,
        'side': 'BUY',
        'type': 'MARKET',
        'quoteOrderQty': quote_amount
    }
    return robust(exchange.privatePostOrder, params=params, func_name='privatePostOrder')


def robust(func, params={}, func_name='', retry_times=5, sleep_seconds=5):
    for _ in range(retry_times):
        try:
            return func(params=params)
        except Exception as e:
            import ccxt
            import json
            if isinstance(e, ccxt.ExchangeError):
                msg = str(e).replace('binance', '').strip()
                error_code = json.loads(msg)['code']
                # {'code': -2022, 'msg': 'ReduceOnly Order is rejected.'}
                if error_code in (-2022,):
                    raise RuntimeError('call ' + func_name + ' error!!! params: ', params, 'reason:', str(e))

            if _ == (retry_times - 1):
                raise RuntimeError('call ' + func_name + ' error!!! params: ', params, 'reason:', str(e))

            time.sleep(sleep_seconds)

def calculate_non_zero_wallet_assets(balance):
    # 从balance字典中提取资产信息
    assets = balance['assets']
    # print(assets)
    # 创建一个空字典来存储非零资产数量
    non_zero_assets = {}

    # 遍历资产并统计非零资产的数量
    for asset in assets:
        # print(asset)
        asset_balance = float(asset['marginBalance'])
        if asset_balance != 0:
            non_zero_assets[asset['asset']] = asset_balance
    # print("non_zero:")
    # print(non_zero_assets)

    return non_zero_assets

def create_chart():
    # 这里应该是您生成图表的代码
    # 为了简化，我将创建一个简单的图表
    plt.figure()
    plt.plot([1, 2, 3], [4, 5, 6])
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()
    return plot_url

def replace_non_json_values(value):
    if isinstance(value, float):
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        if math.isnan(value):
            return "NaN"
    return value


if __name__=='__main__':
    create_chart()