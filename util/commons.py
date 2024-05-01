#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import time
import pandas as pd
import numpy  as np
from datetime import datetime, timedelta


def robust_(func, params={}, func_name='', retry_times=5, sleep_seconds=5):
    for _ in range(retry_times):
        try:
            return func(params=params)
        except Exception as e:
            if _ == (retry_times - 1):
                print('call ' + func_name + ' error!!! params: ', params, 'reason:', str(e))
                os._exit(0)
            time.sleep(sleep_seconds)


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
                if error_code in (-2022, ):
                    raise RuntimeError('call ' + func_name + ' error!!! params: ', params, 'reason:', str(e))

            if _ == (retry_times - 1):
                raise RuntimeError('call ' + func_name + ' error!!! params: ', params, 'reason:', str(e))

            time.sleep(sleep_seconds)

    
# =====辅助功能函数
# ===下次运行时间，和课程里面讲的函数是一样的
def next_run_time(time_interval, ahead_seconds=5, cheat_seconds=100):
    """
    根据time_interval，计算下次运行的时间，下一个整点时刻。
    目前只支持分钟和小时。
    :param time_interval: 运行的周期，15m，1h
    :param ahead_seconds: 预留的目标时间和当前时间的间隙
    :return: 下次运行的时间
    案例：
    15m  当前时间为：12:50:51  返回时间为：13:00:00
    15m  当前时间为：12:39:51  返回时间为：12:45:00
    10m  当前时间为：12:38:51  返回时间为：12:40:00
    5m  当前时间为：12:33:51  返回时间为：12:35:00

    5m  当前时间为：12:34:51  返回时间为：12:40:00

    30m  当前时间为：21日的23:33:51  返回时间为：22日的00:00:00

    30m  当前时间为：14:37:51  返回时间为：14:56:00

    1h  当前时间为：14:37:51  返回时间为：15:00:00

    """
    if time_interval.endswith('m') or time_interval.endswith('h'):
        pass
    elif time_interval.endswith('T'):
        time_interval = time_interval.replace('T', 'm')
    elif time_interval.endswith('H'):
        time_interval = time_interval.replace('H', 'h')
    else:
        print('time_interval格式不符合规范。程序exit')
        exit()
    
    ti = pd.to_timedelta(time_interval)
    now_time      = datetime.now()
    this_midnight = now_time.replace(hour=0, minute=0, second=0, microsecond=0)
    min_step      = timedelta(minutes=1)

    target_time = now_time.replace(second=0, microsecond=0)

    while True:
        target_time = target_time + min_step
        delta = target_time - this_midnight
        if delta.seconds % ti.seconds == 0 and (target_time - now_time).seconds >= ahead_seconds:
            # 当符合运行周期，并且目标时间有足够大的余地，默认为60s
            break
    if cheat_seconds != 0:
        target_time = target_time - timedelta(seconds=cheat_seconds)

    print('程序下次运行的时间：', target_time, '\n')

    return target_time


# ===依据时间间隔, 自动计算并休眠到指定时间
def sleep_until_run_time(time_interval, ahead_time=1, if_sleep=True, cheat_seconds=120):
    """
    根据next_run_time()函数计算出下次程序运行的时候，然后sleep至该时间
    :param if_sleep:
    :param time_interval:
    :param ahead_time:
    :return:
    """
    # 计算下次运行时间
    run_time = next_run_time(time_interval, ahead_time, cheat_seconds)
    # sleep
    if if_sleep:
        time.sleep(max(0, (run_time - datetime.now()).seconds))
        while True:  # 在靠近目标时间时
            if datetime.now() > run_time:
                break
    return run_time

