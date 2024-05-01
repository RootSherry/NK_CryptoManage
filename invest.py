import os
import json
import ccxt
import csv
import time
from datetime import datetime
from decimal import Decimal
from function import *

# 定义全局代理配置
proxy = {}
# proxy = {
#     "http": "http://127.0.0.1:23457",
#     "https": "http://127.0.0.1:23457"
# }
class Invest:
    def calculate_investment(self, principal, rate, time):
        """计算简单利息"""
        # 确保输入是数字
        principal = float(principal)
        rate = float(rate)
        time = float(time)

        # 计算利息
        interest = principal * (rate / 100) * time
        return interest

    def perform_transfer(self, username, from_account, to_account, amount, currency='USDT'):
        # 初始化 transfer_message 为空字符串
        transfer_message = ""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 读取配置文件
        with open(os.path.join(script_dir, 'users.json'), 'r', encoding='utf-8') as file:
            config = json.load(file)

        # 获取当前用户的账户信息
        user_accounts = config["users"][username]["accounts"]

        # 获取转出和转入账户的apiKey和secret
        from_api_key = user_accounts[from_account]["apiKey"]
        from_secret_key = user_accounts[from_account]["secret"]
        to_api_key = user_accounts[to_account]["apiKey"]
        to_secret_key = user_accounts[to_account]["secret"]

        # 根据用户名设置CSV文件的路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        user_dir = os.path.join(script_dir, f"user/{username}")
        os.makedirs(user_dir, exist_ok=True)  # 创建用户目录，如果不存在
        csv_file = os.path.join(user_dir, 'transfer_records.csv')

        # 获取当前时间
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 定义要记录的数据，包括当前时间
        transfer_data = {
            '转账时间': current_time,  # 添加转账时间
            '转出账户': from_account,
            '转入账户': to_account,
            '币种': currency,
            '数量': amount,
        }

        # 创建转出账户的exchange对象
        from_exchange = ccxt.binance({
            'apiKey': from_api_key,
            'secret': from_secret_key,
            'timeout': 30000,
            'rateLimit': 10,
            'enableRateLimit': False,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 10000,
            }
        })
        from_exchange.proxies = proxy
        # 使用Root账户的apiKey和secret进行中间转账
        root_api_key = user_accounts["Root"]["apiKey"]
        root_secret_key = user_accounts["Root"]["secret"]
        root_exchange = ccxt.binance({
            'apiKey': root_api_key,
            'secret': root_secret_key,
            'timeout': 30000,
            'rateLimit': 10,
            'enableRateLimit': False,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 10000,
            }
        })
        root_exchange.proxies=proxy
        # 执行原有的转账操作
        params = {
            'fromEmail': user_accounts[from_account]["email"],
            'fromAccountType': 'SPOT',
            'toEmail': user_accounts[to_account]["email"],
            'toAccountType': 'SPOT',
            'asset': currency,
            'amount': float(amount),
        }

        # 创建转入账户的exchange对象
        to_exchange = ccxt.binance({
            'apiKey': to_api_key,
            'secret': to_secret_key,
            'timeout': 30000,
            'rateLimit': 10,
            'enableRateLimit': False,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 10000,
            }
        })
        to_exchange.proxies=proxy
        try:

            # 检查账户余额
            amount = float(amount) 
            spot_usdt_amount = get_spot_balance(from_exchange, currency)
            if spot_usdt_amount < amount:
                transfer_amount = amount - spot_usdt_amount
                transfer_future_to_spot(from_exchange, currency, transfer_amount, 2)
                # spot_usdt_amount = get_spot_balance(exchange, 'USDT')  # 更新余额
                transfer_message = f"现货余额不足，从合约到现货账户转账：{transfer_amount} {currency}\n"
            # 从合约账户转账到现货账户
            else:
                transfer_message = f"现货账户余额足够：{amount} {currency}\n"

            # transfer_future_to_spot(from_exchange, currency, amount, 2)
            # transfer_message = f"合约到现货账户转账成功：{amount} {currency}\n"
            time.sleep(5)
        except Exception as e:
            return f"合约到现货账户转账失败：{str(e)}"

        try:
            # 执行原有的转账操作
            res = root_exchange.sapiPostSubAccountUniversalTransfer(params=params)
            transfer_message += f"中间转账成功：从 {from_account} 到 {to_account} {amount} {currency}，详情：{res}\n"
        except Exception as e:
            return transfer_message + f"中间转账失败：{str(e)}"

        try:
            # 将资金从目标账户的现货账户转回合约账户
            transfer_future_to_spot(to_exchange, currency, amount, 1)
            transfer_message += f"现货到合约账户转账成功：{amount} {currency}"
        except Exception as e:
            transfer_message += f"现货到合约账户转账失败：{str(e)}"
            return transfer_message

        # 将转账信息写入CSV文件
        with open(csv_file, 'a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=transfer_data.keys())
            if file.tell() == 0:  # 如果文件是空的，写入表头
                writer.writeheader()
            writer.writerow(transfer_data)

        return transfer_message

    def get_account_balance_message(self, account_config):
        # 创建交易所实例
        exchange = ccxt.binance({
            'apiKey': account_config['apiKey'],
            'secret': account_config['secret'],
            'timeout': 30000,
            'rateLimit': 10,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 10000,
            }
        })
        exchange.proxies = proxy

        # try:
        # 获取U本位合约账户余额
        swap_balance = exchange.fapiPrivateV2_get_account()
        # print('牛的',swap_balance)
        equity = calculate_non_zero_wallet_assets(swap_balance)

        assets = exchange.dapiPrivateGetAccount()['assets']

        # print(equity)
        # 获取现货账户余额
        spot_balances = get_all_spot_balances(exchange)

        # 获取所有币种对应的U价格
        symbol_last_price = fetch_binance_ticker_data(exchange, symbol_type='spot')
        print(symbol_last_price)
        # 格式化余额信息
        message = "<h3>现货账户持仓：</h3><ul>"
        total_spot_value_in_u = 0
        for asset, quantity in spot_balances.items():
            if asset == "USDT":
                asset_value_in_u = quantity  # 直接使用USDT的数量作为价值
            elif asset + "USDT" in symbol_last_price:
                asset_value_in_u = quantity * symbol_last_price[asset + "USDT"]
            else:
                continue  # 如果没有对应的USDT交易对，跳过该币种
            total_spot_value_in_u += asset_value_in_u
            message += f"<li>{asset}: {quantity:.4f} (价值: {asset_value_in_u:.2f} U)</li>"

        message += f"</ul><p>现货账户总价值：{total_spot_value_in_u:.2f} U</p>"

        message += "<h3>U本位合约账户持仓：</h3><ul>"
        total_equity_value_in_u = 0
        for asset, quantity in equity.items():
            if asset == "USDT":
                asset_value_in_u = quantity
            elif asset + "USDT" in symbol_last_price:
                asset_value_in_u = quantity * symbol_last_price[asset + "USDT"]
            else:
                continue
            total_equity_value_in_u += asset_value_in_u
            message += f"<li>{asset}: {quantity:.4f} (价值: {asset_value_in_u:.2f} U)</li>"

        message += f"</ul><p>U本位合约账户总价值：{total_equity_value_in_u:.2f} U</p>"

        # 初始化 HTML 消息和总价值计算
        message += "<h3>币本位合约账户持仓：</h3><ul>"
        total_margin_value_in_u = 0.0

        for asset in assets:
            # 解析保证金余额和资产名称
            margin_balance = float(asset['marginBalance'])
            asset_name = asset['asset']

            # 筛选出 marginBalance 不为 0 的资产
            if margin_balance != 0.0:
                # 假设所有资产价值直接以 U（比如 USDT）为单位
                asset_value_in_u = margin_balance * symbol_last_price[asset_name + "USDT"]  # 如果需要，这里可以添加逻辑来转换资产价值到 U

                total_margin_value_in_u += asset_value_in_u
                message += f"<li>{asset_name}: {margin_balance:.4f} (价值: {asset_value_in_u:.2f} U)</li>"

        message += f"</ul><p>币本位合约账户总价值：{total_margin_value_in_u:.2f} U</p>"

        return message, total_spot_value_in_u, total_equity_value_in_u, total_margin_value_in_u
        # except Exception as e:
        #     return f"<p>获取账户余额时发生错误: {str(e)}</p>"


    def perform_purchase(self, username, payment_account, purchase_currency, amount):
        try:
            amount = float(amount)  # 确保amount是浮点数
            # 读取用户的账户信息
            with open('users.json', 'r', encoding='utf-8') as file:
                users = json.load(file)["users"]

            # 检查用户名和账户是否存在
            if username not in users or payment_account not in users[username]["accounts"]:
                return f"用户 {username} 或账户 {payment_account} 不存在。"

            # 获取账户配置
            account_config = users[username]["accounts"][payment_account]
            apiKey = account_config["apiKey"]
            secret = account_config["secret"]

            # 创建交易所实例
            exchange = ccxt.binance({
                'apiKey': apiKey,
                'secret': secret,
                'timeout': 30000,
                'rateLimit': 10,
                'enableRateLimit': False,
                'options': {
                    'adjustForTimeDifference': True,
                    'recvWindow': 10000,
                }
            })
            exchange.proxies = proxy

            messages = []  # 用于收集每个步骤的消息

            # 检查账户余额
            spot_usdt_amount = get_spot_balance(exchange, 'USDT')
            if spot_usdt_amount < amount:
                transfer_amount = amount - spot_usdt_amount
                transfer_future_to_spot(exchange, 'USDT', transfer_amount, 2)
                spot_usdt_amount = get_spot_balance(exchange, 'USDT')  # 更新余额
                messages.append(f"USDT数量不足，从U本位账户转移了 {transfer_amount}U 到现货账户。")

            # 检查购买币种的初始余额
            initial_balance = get_spot_balance(exchange, purchase_currency)
            initial_USDT = get_spot_balance(exchange, 'USDT')

            # 购买操作
            crypto_pair = purchase_currency + 'USDT'  # 拼接交易对
            buy_result = spot_buy_quote(exchange, crypto_pair, amount)

            # 检查购买币种的新余额
            new_balance = get_spot_balance(exchange, purchase_currency)
            new_USDT = get_spot_balance(exchange, 'USDT')

            # 计算实际购买的数量
            actual_cost = initial_USDT-new_USDT
            actual_purchase_amount = new_balance - initial_balance
            messages.append(f"购买了 {actual_purchase_amount}个 {purchase_currency}。")

            # 计算购买的单价
            purchase_price = actual_cost / actual_purchase_amount if actual_purchase_amount else 0
            messages.append(f"买入价格：{purchase_price}U。")

            # CSV 文件的路径更改为 /user/{username}/purchase_records.csv
            # 根据用户名设置CSV文件的路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
            csv_dir = os.path.join(script_dir, f"user/{username}")
            if not os.path.exists(csv_dir):
                os.makedirs(csv_dir)  # 创建文件夹
            csv_file = os.path.join(csv_dir, 'purchase_records.csv')

            # 获取当前时间
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 更新要记录的数据，加入实际购买数量和单价
            purchase_data = {
                '购买时间': current_time,
                '账户': payment_account,
                '币种': purchase_currency,
                '数量': actual_purchase_amount,
                '价值(U)': actual_cost,
                '价格(U)': purchase_price,
                '操作': '买入'  # 新增“操作”列
            }

            if not os.path.isfile(csv_file):
                with open(csv_file, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.DictWriter(file, fieldnames=purchase_data.keys())
                    writer.writeheader()

            # 写入CSV文件
            with open(csv_file, 'a', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=purchase_data.keys())
                writer.writerow(purchase_data)

            # 转移ETH、BTC、USDT
            spot_balances_after_purchase = get_all_spot_balances(exchange)
            assets_to_transfer = ['ETH', 'BTC', 'USDT']
            for asset in assets_to_transfer:
                if asset in spot_balances_after_purchase:
                    transfer_amount = spot_balances_after_purchase[asset]
                    if transfer_amount > 0:
                        transfer_future_to_spot(exchange, asset, transfer_amount, 1)
                        messages.append(f"将 {transfer_amount} {asset} 从现货账户转移到U本位合约账户。")

            # 汇总并返回消息
            final_message = "\n".join(messages)
            return f"购买成功完成!\n{final_message}"

        except Exception as e:
            return f"购买过程中发生错误: {str(e)}"


