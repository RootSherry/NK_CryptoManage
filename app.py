from flask import Flask, render_template, request, redirect, url_for, session
from invest import Invest
import json
from datetime import timedelta,datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask import Flask, jsonify
from function import *
import os
import math
import numpy as np
import itertools
import threading

app = Flask(__name__)
# 设置一个安全的密钥，用于保护 session
# 请在生产应用中使用一个难以猜测的随机字符串，并保持秘密
app.secret_key = '66666y'
lock = threading.Lock()
invest_instance = Invest()

# 读取和写入 JSON 文件的函数
def read_json(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)

def write_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))  # 未登录，重定向到登录页面

    username = session['username']  # 从会话中获取当前登录的用户名
    print(session['username'])
    # 读取即将添加的功能
    with open('features.json', 'r', encoding='utf-8') as file:
        upcoming_features = json.load(file)

    # 读取最新的三条更新记录
    updates = []
    if os.path.exists('updates.txt'):
        with open('updates.txt', 'r', encoding='utf-8') as file:
            updates = file.readlines() # 获取最后三行

    return render_template('homepage.html', updates=updates[::-1],username=username, upcoming_features=upcoming_features)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = read_json('users.json')['users']

        if username in users and users[username]['password'] == password:
            session['username'] = username  # 设置 session
            print(session)
            return redirect(url_for('homepage'))  # 登录成功，重定向到 homepage 页面
        else:
            message = "账号密码错误，请重新填写"
            return render_template('message.html', message=message, redirect_url='/login', delay=5)
    else:
        return render_template('login.html')

@app.route('/homepage')
def homepage():
    if 'username' not in session:
        print(session)
        return redirect(url_for('login'))  # 未登录，重定向到登录页面

    username = session['username']  # 从会话中获取当前登录的用户名
    print(session['username'])

    # 读取配置文件以获取当前登录用户的账户列表
    with open('users.json', 'r', encoding='utf-8') as file:
        config = json.load(file)
        user_accounts = config["users"][username]["accounts"]  # 获取当前用户的账户信息
    print(username)

    # 读取即将添加的功能
    with open('features.json', 'r', encoding='utf-8') as file:
        upcoming_features = json.load(file)

    # 读取最新的三条更新记录
    updates = []
    if os.path.exists('updates.txt'):
        with open('updates.txt', 'r', encoding='utf-8') as file:
            updates = file.readlines()  # 获取最后三行


    return render_template('homepage.html', updates=updates[::-1], username=username, accounts=user_accounts,upcoming_features=upcoming_features)


@app.route('/logout')
def logout():
    session.pop('username', None)  # 从 session 中移除 'username'
    return redirect(url_for('login'))  # 重定向到登录页面

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']  # 在实际应用中，密码应该进行散列处理
        all_users = read_json('users.json')

        if username in all_users['users']:
            # 用户名已存在
            message = "用户名已存在。"
            return render_template('message.html', message=message, redirect_url='/register', delay=5)

        all_users['users'][username] = {'password': password, 'accounts': {}}
        write_json('users.json', all_users)

        # 注册成功
        message = "注册成功！正在跳转到登录页面..."
        return render_template('message.html', message=message, redirect_url='/login', delay=5)
    else:
        return render_template('register.html')

@app.route('/api/btc_price')
def btc_price():
    symbol_last_price = fetch_binance_ticker_data('binance', 'spot')
    btc_price = symbol_last_price['BTCUSDT']
    return jsonify({'btcPrice': btc_price})

@app.route('/api/eth_price')
def eth_price():
    symbol_last_price = fetch_binance_ticker_data('binance', 'spot')
    eth_price = symbol_last_price['ETHUSDT']
    return jsonify({'ethPrice': eth_price})

@app.route('/submit', methods=['POST'])
def submit():
    try:
        principal = request.form['principal']
        rate = request.form['rate']
        time = request.form['time']
        result = invest_instance.calculate_investment(principal, rate, time)
        return render_template('result.html', result=result)
    except KeyError:
        return "Form data is missing. Please go back and submit all required fields.", 400


@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    # 获取反馈内容
    feedback = request.form.get('feedback')
    if not feedback:
        flash('反馈内容不能为空。')
        return redirect(url_for('feedbacks'))

    # 获取用户名，如果未登录则为'匿名'
    username = session.get('username', '匿名')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    feedback_entry = f"{timestamp} - {username}: {feedback}\n"

    # 保存反馈到一个文件
    with open('feedbacks.txt', 'a', encoding='utf-8') as file:
        file.write(feedback_entry)

    flash('您的意见已提交，感谢您的反馈！')
    return redirect(url_for('feedbacks'))

@app.route('/feedbacks')
def feedbacks():
    try:
        with open('feedbacks.txt', 'r', encoding='utf-8') as file:
            feedbacks = file.readlines()
    except FileNotFoundError:
        feedbacks = ["暂无意见。"]

    return render_template('feedbacks.html', feedbacks=feedbacks)

# 删除意见箱
@app.route('/delete_feedback', methods=['POST'])
def delete_feedback():
    if 'username' not in session:
        flash('您需要登录才能删除意见。')
        return redirect(url_for('login'))

    feedback_to_delete = request.form['feedback']
    username = session['username']
    print(session['username'])

    if username not in feedback_to_delete:
        flash('您只能删除自己的意见。')
        return redirect(url_for('feedbacks'))

    # 从文件中读取意见，删除指定的意见
    with open('feedbacks.txt', 'r', encoding='utf-8') as file:
        feedbacks = file.readlines()
    feedback_to_delete = feedback_to_delete.strip()
    feedbacks = [f.strip() for f in feedbacks if f.strip() != feedback_to_delete]

    # 将更新后的意见列表写回文件
    with open('feedbacks.txt', 'w', encoding='utf-8') as file:
        for f in feedbacks:
            file.write(f + "\n")

    flash('意见已成功删除。')
    return redirect(url_for('feedbacks'))

@app.route('/query')
def query():
    if 'username' not in session:
        return redirect(url_for('login'))
    print(session['username'])

    # 这里可以根据需要添加其他必要的代码
    return render_template('query.html')

@app.route('/query_balance', methods=['GET', 'POST'])
def query_balance():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    print(session['username'])
    message = ''
    selected_account_name = None

    try:
        # 读取配置文件以获取当前登录用户的账户列表
        with open('users.json', 'r', encoding='utf-8') as file:
            users_config = json.load(file)
        user_accounts = users_config['users'][username]['accounts']

        if request.method == 'POST':
            selected_account_name = request.form.get('account')
            if selected_account_name in user_accounts:
                account_config = user_accounts[selected_account_name]
                message, spot_balance, equity_balance, margin_value_in_u, spot_holdings, equity_holdings, margin_holdings = invest_instance.get_account_balance_message(account_config)
            else:
                message = "选择的账户不存在。"
    except FileNotFoundError:
        message = "配置文件未找到。"
    except json.JSONDecodeError:
        message = "配置文件格式错误。"

    account_names = list(user_accounts.keys())
    return render_template('query_balance.html',
                           accounts=account_names,
                           selected_account=selected_account_name,
                           message=message)


@app.route('/transfer', methods=['GET', 'POST'])
def transfer():
    if 'username' not in session:
        return redirect(url_for('login'))  # 未登录，重定向到登录页面

    username = session['username']  # 从会话中获取用户名
    print(session['username'])
    # 读取配置文件以获取当前登录用户的账户列表
    with open('users.json', 'r', encoding='utf-8') as file:
        config = json.load(file)
        user_accounts = config["users"][username]["accounts"]  # 获取当前用户的账户

    if request.method == 'POST':
        from_account = request.form['from_account']
        to_account = request.form['to_account']
        amount = request.form['amount']
        currency = request.form.get('currency', 'USDT')
        message = invest_instance.perform_transfer(username, from_account, to_account, amount, currency)
        return render_template('transfer_result.html', message=message)
    else:
        return render_template('transfer.html', accounts=user_accounts)


@app.route('/manage', methods=['GET', 'POST'])
def manage_accounts():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    print(session['username'])

    # 读取配置文件以获取当前登录用户的账户列表
    with open('users.json', 'r', encoding='utf-8') as file:
        config = json.load(file)
    user_accounts = config['users'][username]['accounts']

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            # 添加新账户
            new_account_name = request.form.get('new_account_name')
            new_apiKey = request.form.get('new_apiKey')
            new_secret = request.form.get('new_secret')
            new_email = request.form.get('new_email')

            # 检查是否存在同名账户
            if new_account_name in user_accounts:
                return render_template('manage.html', accounts=user_accounts, error="账户名已存在")

            user_accounts[new_account_name] = {
                'apiKey': new_apiKey,
                'secret': new_secret,
                'email': new_email
            }
        elif action == 'update':
            # 更新现有账户信息
            account_name = request.form.get('account_name')
            apiKey = request.form.get('apiKey')
            secret = request.form.get('secret')
            email = request.form.get('email')

            if account_name in user_accounts:
                user_accounts[account_name] = {
                    'apiKey': apiKey,
                    'secret': secret,
                    'email': email
                }
        elif action == 'delete':
            # 删除账户
            account_name = request.form.get('account_name')
            if account_name in user_accounts:
                del user_accounts[account_name]

        # 保存更改到配置文件
        with open('users.json', 'w', encoding='utf-8') as file:
            json.dump(config, file, indent=4)

        return redirect(url_for('manage_accounts'))
    else:
        return render_template('manage.html', accounts=user_accounts)

@app.route('/query_strategy')
def query_strategy():
    username = session.get('username')
    if not username:
        return 'Not logged in', 401
    print(session['username'])
    # 读取 user.json 获取用户的账户信息
    with open('users.json', 'r', encoding='utf-8') as file:
        users_data = json.load(file)
        user_accounts = users_data['users'][username]['accounts'].keys()

    return render_template('query_strategy.html', accounts=user_accounts)


# @app.route('/get_strategy_data', methods=['POST'])
# def get_strategy_data():
#     data = request.form
#     account_name = data['account_name']
#     username = session.get('username')
#
#     # 读取对应账户的 CSV 文件
#     file_path = f'user/{username}/{account_name}.csv'
#     if os.path.exists(file_path):
#         df = pd.read_csv(file_path)
#         # 处理数据，创建图表所需的 JSON 数据
#         chart_data = process_data_for_chart(df)
#         return jsonify({'chart_data': json.dumps(chart_data)})
#     else:
#         return jsonify({'error': 'File not found'}), 404

def process_data_for_chart(df):
    # 处理 DataFrame 数据，准备用于绘图
    # 示例：使用时间和资金曲线
    chart_data = {
        'x': df['time'].tolist(),
        'y': df['Ba'].tolist(),
    }
    return chart_data


@app.route('/get_strategy_data', methods=['POST'])
def get_strategy_data():
    username = session.get('username')
    if not username:
        return 'Not logged in', 401
    print(session['username'])
    account = request.form.get('account_name')
    csv_path = f'user/{username}/data/{account}.csv'
    trans_path = f'user/{username}/data/{account}_transfer.csv'

    if not os.path.exists(csv_path) or not os.path.exists(trans_path):
        return jsonify({'error': 'File not found'}), 404

    # 读取和合并数据
    df1 = pd.read_csv(csv_path)
    df2 = pd.read_csv(trans_path)

    df2 = df2[df2['出入金额'] > 10]
    df2['time'] = pd.to_datetime(df2['time']) + timedelta(hours=1)
    df2['time'] = df2['time'].dt.strftime('%Y-%m-%d %H:%M:%S')

    df1.set_index('time', inplace=True)
    df = pd.concat([df1, df2], keys=['记录'])
    df.sort_values(by='time', inplace=True)
    df.reset_index(inplace=True)
    df.rename(columns={'level_0': 'type'}, inplace=True)
    print(df)
    df['balance'] = df['marBa'].fillna(0) + df['spot'].fillna(0)
    df = df[['time', 'type', 'balance','L_h','S_h']]
    print(df)

    # 计算净值
    df['净值'] = 0
    df['份额'] = 0
    df['当前总市值'] = 0
    df.loc[0, '净值'] = 1
    df.loc[0, '份额'] = df.iloc[0]['balance'] / df.iloc[0]['净值']
    df.loc[0, '当前总市值'] = df.iloc[0]['balance']
    for i in range(1, len(df)):
        if df.iloc[i]['type'] == '记录':
            df.loc[i, '当前总市值'] = df.iloc[i]['balance']
            df.loc[i, '份额'] = df.iloc[i - 1]['份额']
            df.loc[i, '净值'] = df.iloc[i]['当前总市值'] / df.loc[i]['份额']
        elif df.iloc[i]['type'] == '充提':
            reduce_cnt = df.iloc[i]['balance'] / df.iloc[i - 1]['净值']
            df.loc[i, '份额'] = df.loc[i - 1]['份额'] + reduce_cnt
            df.loc[i, '当前总市值'] = df.iloc[i]['balance'] + df.iloc[i - 1]['balance']
            df.loc[i, '净值'] = df.iloc[i]['当前总市值'] / df.iloc[i]['份额']

    # ===2.整合作图
    curve = pd.DataFrame()

    curve['candle_begin_time'] = pd.to_datetime(df['time'])
    curve['资金曲线'] = df['净值']
    curve['多'] = df['L_h']
    curve['空'] = df['S_h']
    curve.set_index(curve['candle_begin_time'], inplace=True)
    del curve['candle_begin_time']

    # 指标字段的顺序
    indicator_order = [
        '累积净值', '年化收益', '年化收益/回撤比', '回撤/年化收益比', '最大回撤',
        '最大回撤开始时间', '最大回撤结束时间', '胜率', '盈亏收益比', '每周期平均收益',
        '盈利周期数', '亏损周期数', '单周期最大盈利', '单周期最大亏损',
        '最大连续盈利周期数', '最大连续亏损周期数'
    ]

    # 调用 plot_log_double 函数获取图形数据
    rtn, chart_data = plot_log_double(curve)
    # 处理非标准 JSON 值并按顺序添加到指标字典中
    indicators = {}
    for key in indicator_order:
        value = rtn[key][0]
        if isinstance(value, (float, int)):
            if math.isinf(value) or math.isnan(value):
                value = str(value)
        indicators[key] = value

    # 处理非标准 JSON 值
    indicators = {k: replace_non_json_values(v) for k, v in rtn.iloc[0].to_dict().items()}

    chart_data['indicators'] = indicators
    chart_data['indicators_order'] = indicator_order
    # chart_data = prepare_json(chart_data)
    return jsonify(chart_data)



def plot_log_double(curve, mdd_std=0.2):
    curve['本周期多空涨跌幅'] = curve['资金曲线'].pct_change().fillna(0)
    curve = curve.reset_index()
    rtn, select_c = cal_ind(curve)
    # 在 select_c 中设置 'candle_begin_time' 为索引
    select_c.set_index('candle_begin_time', inplace=True)
    # 绘制上图所需数据
    condition = (select_c['dd2here'] >= -mdd_std) & (select_c['dd2here'].shift(1) < -mdd_std)
    select_c[f'回撤上穿{mdd_std}次数'] = 0
    select_c.loc[condition, f'回撤上穿{mdd_std}次数'] = 1
    mdd_num = int(select_c[f'回撤上穿{mdd_std}次数'].sum())

    # 绘制下图所需数据
    ret = select_c[['本周期多空涨跌幅']].copy()
    ret['nv'] = (1 + ret['本周期多空涨跌幅']).cumprod()
    ret['dd'] = ret['nv'] / ret['nv'].cummax() - 1

    # 将 rtn (DataFrame) 转换为字典格式以便发送到前端
    indicators = rtn.to_dict(orient='records')[0]
    # print(select_c.columns)

    # 生成绘图所需数据
    chart_data = {
        'time': select_c.index.strftime('%Y-%m-%d %H:%M:%S').tolist(),
        '资金曲线': select_c['资金曲线'].tolist(),
        # '多头': select_c['多'].tolist(),
        # '空头': select_c['空'].tolist(),
        '回撤': (-select_c['dd2here']).tolist(),
        'mdd_num': mdd_num,
        'nv': ret['nv'].tolist(),
        'dd_percentage': (ret['dd'] * 100).tolist(),
        'indicators': indicators  # 添加评价指标数据
    }
    # print(chart_data['nv'])
    return rtn, chart_data

def cal_ind(_select_c):
    """
    函数介绍：计算评价指标
    :param _select_c: 传入的df
    :return: 返回评价指标 和 选币列表
    """

    # 校验是否为空

    if _select_c.empty:
        return None
    select_coin = _select_c.copy()

    # ===计算净值
    results = pd.DataFrame()
    results.loc[0, '累积净值'] = round(select_coin['资金曲线'].iloc[-1], 4)  # 取净值

    # ===计算最大回撤
    select_coin['max2here'] = select_coin['资金曲线'].expanding().max()
    select_coin['dd2here'] = select_coin['资金曲线'] / select_coin['max2here'] - 1
    end_date, max_draw_down = tuple(select_coin.sort_values(by=['dd2here']).iloc[0][['candle_begin_time', 'dd2here']])
    start_date = \
    select_coin[select_coin['candle_begin_time'] <= end_date].sort_values(by='资金曲线', ascending=False).iloc[0][
        'candle_begin_time']
    results.loc[0, '最大回撤'] = format(max_draw_down, '.2%')
    results.loc[0, '最大回撤开始时间'] = str(start_date)
    results.loc[0, '最大回撤结束时间'] = str(end_date)

    # ===统计每个周期
    results.loc[0, '盈利周期数'] = len(select_coin.loc[select_coin['本周期多空涨跌幅'] > 0])
    results.loc[0, '亏损周期数'] = len(select_coin.loc[select_coin['本周期多空涨跌幅'] <= 0])
    results.loc[0, '胜率'] = format(results.loc[0, '盈利周期数'] / len(select_coin), '.2%')
    results.loc[0, '每周期平均收益'] = format(select_coin['本周期多空涨跌幅'].mean(), '.2%')
    results.loc[0, '盈亏收益比'] = round(
        select_coin.loc[select_coin['本周期多空涨跌幅'] > 0]['本周期多空涨跌幅'].mean() /
        select_coin.loc[select_coin['本周期多空涨跌幅'] <= 0]['本周期多空涨跌幅'].mean() * (-1), 4)
    results.loc[0, '单周期最大盈利'] = format(select_coin['本周期多空涨跌幅'].max(), '.2%')
    results.loc[0, '单周期最大亏损'] = format(select_coin['本周期多空涨跌幅'].min(), '.2%')

    # ===连续盈利亏损
    results.loc[0, '最大连续盈利周期数'] = max(
        [len(list(v)) for k, v in itertools.groupby(np.where(select_coin['本周期多空涨跌幅'] > 0, 1, np.nan))])
    results.loc[0, '最大连续亏损周期数'] = max(
        [len(list(v)) for k, v in itertools.groupby(np.where(select_coin['本周期多空涨跌幅'] <= 0, 1, np.nan))])

    # ===计算年化收益
    time_during = select_coin.iloc[-1]['candle_begin_time'] - select_coin.iloc[0]['candle_begin_time']
    total_seconds = time_during.days * 24 * 3600 + time_during.seconds
    if total_seconds == 0:
        annual_return = 0
    else:
        final_r = round(select_coin['资金曲线'].iloc[-1], 4)
        annual_return = pow(final_r, 24 * 3600 * 365 / total_seconds) - 1
    results.loc[0, '年化收益'] = round(annual_return, 4)
    results.loc[0, '年化收益/回撤比'] = round(annual_return / abs(max_draw_down), 4)
    results.loc[0, '回撤/年化收益比'] = round(abs(max_draw_down) / annual_return, 4)

    # ===重新排序
    results = results[['累积净值', '年化收益', '年化收益/回撤比', '回撤/年化收益比', '最大回撤', '最大回撤开始时间',
                       '最大回撤结束时间',
                       '胜率', '盈亏收益比', '每周期平均收益', '盈利周期数', '亏损周期数', '单周期最大盈利',
                       '单周期最大亏损',
                       '最大连续盈利周期数', '最大连续亏损周期数']]

    return results, select_coin

@app.route('/query_transfer')
def query_transfer():
    if 'username' not in session:
        return redirect(url_for('login'))
    print(session['username'])
    username = session['username']
    # 读取当前用户的账户列表
    user_data = read_json('users.json')['users']
    accounts = user_data[username]['accounts'] if username in user_data else []

    return render_template('query_transfer.html', accounts=accounts)


@app.route('/get_transfer_record/<account>')
def get_transfer_record(account):
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    filepath = f'user/{session["username"]}/transfer_records.csv'
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)

        # 首先根据账户筛选记录
        filtered_records = df[(df['转出账户'] == account) | (df['转入账户'] == account)]

        # 然后根据时间筛选记录
        if start_date:
            filtered_records = filtered_records[filtered_records['转账时间'] >= start_date]
        if end_date:
            # 调整结束日期以包括当天的整天
            end_date_adjusted = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            filtered_records = filtered_records[filtered_records['转账时间'] < end_date_adjusted.strftime('%Y-%m-%d %H:%M:%S')]

        top_transfers = filtered_records.nlargest(3, '数量')
        # 这里添加一个print来检查top_transfers的内容
        print("Top transfers:", top_transfers)

        # 币种分类累计
        out_by_currency = filtered_records[filtered_records['转出账户'] == account].groupby('币种')[
            '数量'].sum().to_dict()
        in_by_currency = filtered_records[filtered_records['转入账户'] == account].groupby('币种')[
            '数量'].sum().to_dict()

        # 检查累计转出和转入的输出
        print("Total out by currency:", out_by_currency)
        print("Total in by currency:", in_by_currency)

        return jsonify({
            'records': filtered_records.to_dict(orient='records'),
            'total_out_by_currency': out_by_currency,
            'total_in_by_currency': in_by_currency,
            'top_transfers': top_transfers.to_dict(orient='records')
        })
    else:
        return jsonify({'records': [], 'total_out': 0.0, 'total_in': 0.0, 'top_transfers': []})

@app.route('/query_purchase')
def query_purchase():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    print(session['username'])
    # 读取当前用户的账户列表
    user_data = read_json('users.json')['users']
    accounts = user_data[username]['accounts'] if username in user_data else []

    return render_template('query_purchase.html', accounts=accounts)

@app.route('/get_purchase_record/<account>')
def get_purchase_record(account):
    filepath = f'user/{session["username"]}/purchase_records.csv'
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        # 过滤记录，仅显示选定账户的购买记录
        filtered_records = df[df['账户'] == account]

        # 计算累计购买每种币种的数量、价值和平均买入成本
        total_purchases = filtered_records.groupby('币种').agg({'数量': 'sum', '价值(U)': 'sum'})
        total_purchases['平均买入成本(U)'] = total_purchases['价值(U)'] / total_purchases['数量']

        return jsonify({
            'records': filtered_records.to_dict(orient='records'),
            'total_purchases': total_purchases.reset_index().to_dict(orient='records')
        })
    else:
        return jsonify({'records': [], 'total_purchases': []})

@app.route('/purchase', methods=['GET', 'POST'])
def purchase():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    with lock:
        with open('users.json', 'r', encoding='utf-8') as file:
            config = json.load(file)
        user_accounts = config["users"][username]["accounts"]
        user_portfolios = config["users"][username].get("portfolios", {})

    if request.method == 'POST':
        payment_account = request.form['payment_account']
        portfolio_name = request.form.get('portfolio_name')
        try:
            amount = float(request.form['amount'])
        except ValueError:
            return "Invalid amount", 400

        if portfolio_name and portfolio_name not in user_portfolios:  # 新建组合
            currencies = request.form.getlist('currencies[]')
            ratios = []
            try:
                ratios = [float(r) for r in request.form.getlist('ratios[]')]
            except ValueError:
                return "Invalid ratio", 400

            ratios_sum = sum(ratios)
            print(f"Debug: Ratios sum is {ratios_sum}")  # 调试信息

            if ratios_sum != 1:
                return f"比例之和必须为1，目前只有{ratios_sum}", 400

            portfolio = dict(zip(currencies, ratios))
            user_portfolios[portfolio_name] = portfolio

            with lock:
                with open('users.json', 'w', encoding='utf-8') as file:
                    config["users"][username]["portfolios"] = user_portfolios
                    json.dump(config, file, ensure_ascii=False, indent=4)
        else:  # 选择已有组合
            portfolio_name = request.form['portfolio']
            portfolio = user_portfolios[portfolio_name]

        # 根据组合比例购买币种
        messages = []
        for currency, ratio in portfolio.items():
            purchase_amount = amount * ratio
            message = invest_instance.perform_purchase(username, payment_account, currency, purchase_amount)
            messages.append(message)

        return render_template('purchase_result.html', messages=messages)
    else:
        return render_template('purchase.html', accounts=user_accounts, portfolios=user_portfolios)

@app.route('/save_portfolio', methods=['POST'])
def save_portfolio():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    portfolio_name = request.form['portfolio_name']
    try:
        currencies = json.loads(request.form['currencies'])  # 确保字段名与前端一致
        ratios = [float(r) for r in json.loads(request.form['ratios'])]  # 确保字段名与前端一致
    except (json.JSONDecodeError, ValueError) as e:
        return f"Invalid input: {e}", 400

    # 计算比例之和并检查是否等于1
    ratios_sum = sum(ratios)
    if ratios_sum != 1:
        return f"比例之和必须为1，目前只有{ratios_sum}", 400

    portfolio = dict(zip(currencies, ratios))

    with lock:
        with open('users.json', 'r', encoding='utf-8') as file:
            config = json.load(file)
        if "portfolios" not in config["users"][username]:
            config["users"][username]["portfolios"] = {}
        config["users"][username]["portfolios"][portfolio_name] = portfolio

        with open('users.json', 'w', encoding='utf-8') as file:
            json.dump(config, file, ensure_ascii=False, indent=4)

    return redirect(url_for('purchase'))

@app.route('/delete_portfolio', methods=['POST'])
def delete_portfolio():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    portfolio_name = request.form['portfolio_name']

    with lock:
        with open('users.json', 'r', encoding='utf-8') as file:
            config = json.load(file)
        if portfolio_name in config["users"][username]["portfolios"]:
            del config["users"][username]["portfolios"][portfolio_name]

        with open('users.json', 'w', encoding='utf-8') as file:
            json.dump(config, file, ensure_ascii=False, indent=4)

    return redirect(url_for('purchase'))

@app.route('/summarize_accounts')
def summarize_accounts():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    total_spot_balance = 0
    total_equity_balance = 0
    total_margin_balance = 0
    detailed_message = ""
    combined_spot_holdings = {}
    combined_equity_holdings = {}
    combined_margin_holdings = {}

    try:
        with open('users.json', 'r', encoding='utf-8') as file:
            users_config = json.load(file)
        user_accounts = users_config['users'][username]['accounts']

        # 遍历所有账户，汇总余额并记录持仓细节
        for account_name, account_config in user_accounts.items():
            message, spot_balance, equity_balance, margin_value_in_u, spot_holdings, equity_holdings, margin_holdings = invest_instance.get_account_balance_message(account_config)
            total_spot_balance += spot_balance
            total_equity_balance += equity_balance
            total_margin_balance += margin_value_in_u

            # 更新综合持仓信息
            for asset, (quantity, value) in spot_holdings.items():
                if asset in combined_spot_holdings:
                    combined_spot_holdings[asset]['quantity'] += quantity
                    combined_spot_holdings[asset]['value'] += value
                else:
                    combined_spot_holdings[asset] = {'quantity': quantity, 'value': value}

            for asset, (quantity, value) in equity_holdings.items():
                if asset in combined_equity_holdings:
                    combined_equity_holdings[asset]['quantity'] += quantity
                    combined_equity_holdings[asset]['value'] += value
                else:
                    combined_equity_holdings[asset] = {'quantity': quantity, 'value': value}

            for asset, (quantity, value) in margin_holdings.items():
                if asset in combined_margin_holdings:
                    combined_margin_holdings[asset]['quantity'] += quantity
                    combined_margin_holdings[asset]['value'] += value
                else:
                    combined_margin_holdings[asset] = {'quantity': quantity, 'value': value}

            detailed_message += f"<h2>{account_name} 持仓详情:</h2>" + message

        all_sum = total_spot_balance + total_equity_balance + total_margin_balance

        # 创建汇总消息
        summary_message = f"<p>所有账户的现货总价值：{total_spot_balance:.2f} U</p>" + \
                          f"<p>所有账户的U本位合约总价值：{total_equity_balance:.2f} U</p>" + \
                          f"<p>所有账户的币本位合约总价值：{total_margin_balance:.2f} U</p>" + \
                          f"<p>资产总价值：{all_sum:.2f} U</p>"

        # 排序并创建持仓信息消息
        def create_sorted_message(holdings, title):
            sorted_holdings = sorted(holdings.items(), key=lambda x: x[1]['value'], reverse=True)
            message = f"<h3>{title}：</h3><ul>"
            for asset, data in sorted_holdings:
                message += f"<li>{asset}: {data['quantity']:.4f} (价值: {data['value']:.2f} U)</li>"
            message += "</ul>"
            return message

        combined_spot_message = create_sorted_message(combined_spot_holdings, "综合现货持仓")
        combined_equity_message = create_sorted_message(combined_equity_holdings, "综合U本位合约持仓")
        combined_margin_message = create_sorted_message(combined_margin_holdings, "综合币本位合约持仓")

        # message = summary_message + combined_spot_message + combined_equity_message + combined_margin_message + detailed_message
        message = summary_message + combined_spot_message + combined_equity_message + combined_margin_message 
    except Exception as e:
        message = f"<p>处理过程中出现错误：{str(e)}</p>"

    # 返回一个新的HTML页面或原有页面，显示汇总信息
    return render_template('summarize_accounts.html', message=message)


if __name__ == '__main__':
    app.config.update(
        SESSION_COOKIE_SECURE=False,
        REMEMBER_COOKIE_DURATION=timedelta(days=1)  # 例如，设置为一天
    )
    # app.run(debug=True)  # 使用 adhoc 生成临时的 SSL 证书
    app.run(host='0.0.0.0', port=36125, debug=True)
