# NK_CryptoManage
一款加密货币的投资和管理平台。

A cryptocurrency investment and management platform.


平台功能基于币安交易所，需要使用币安账号的api.
## 安装说明

1. 克隆仓库


首先，您需要从GitHub克隆仓库到本地计算机。打开终端（在Linux/macOS）或命令提示符/PowerShell（在Windows）并运行以下命令：

```python
git clone https://github.com/RootSherry/NK_CryptoManage.git
cd NK_CryptoManage
```

3. 创建虚拟环境

   
创建一个新的虚拟环境：
```python
conda create -n quant python=3.8
```

3. 安装依赖

   
项目的依赖在 requirements.txt 文件中列出。安装这些依赖，请确保您的虚拟环境已激活，然后执行：
```python
pip install -r requirements.txt
```
4. 运行平台


一旦依赖安装完成，您就可以启动平台了。
```python
python3 app.py
```
在平台里自行注册账号填写api信息即可使用。

要使用查询资金曲线功能还需运行curve_run.py文件。
```python
python3 curve_run.py
```
# 平台功能

### 主页：
<img width="1454" alt="image" src="https://github.com/RootSherry/NK_CryptoManage/assets/121684306/765b4fb3-b6b3-480c-819b-8ec5826ccc5f">


### 购买：

- 可以选择不同的账户使用USDT进行购买操祚
- 购买操作会优先使用现货账户中的USDT。如果USDT资金不足，系统会自动从U本位合约账户中划转补充。购买完成后，系统将现货账户中的BTC、ETH、USDT转入U本位合约账户充当策略保证金，其他币种保留在现货账户。
- 使用说明写在了界面上
- 可以在查询界面中，查询不同账号的购买记录、买入总量以及平均买入成本

<img width="1718" alt="image" src="https://github.com/RootSherry/NK_CryptoManage/assets/121684306/1bcb9dbd-6eb9-42aa-b44e-279a7b05cf3e">
<img width="1370" alt="image" src="https://github.com/RootSherry/NK_CryptoManage/assets/121684306/32399f39-15de-4bb8-bc95-471fa5344037">


### 转账：

- 在不同子母账户之前进行转账操作，只支持BTC、USDT、ETH、BNB（可自行代码添加）
- 转账操作会优先使用转出账户的现货余额。如果余额不足，系统会自动从U本位合约账户中划转补充。转入账户收到资金后，会自动将其转入U本位合约账户中用作U本位策略保证金。
- 可以在查询界面中，查询不同账号在自定义时间内的转账记录
- 必须填写主账号，且命名为Root，否则无法完成转账操作。(在管理界面中添加主账号)
<img width="1716" alt="image" src="https://github.com/RootSherry/NK_CryptoManage/assets/121684306/bdfd4af6-ddf0-4e87-88b0-19a8d9072443">
<img width="1376" alt="image" src="https://github.com/RootSherry/NK_CryptoManage/assets/121684306/f070c58d-ccd8-47ad-a22a-b4f7a5b76729">



### 查询：

除了前面提到的查询购买记录和转账记录，还可以：

- 查询账户余额，包含现货和U本位账户中的币种数量以及价值
- 查询策略表现，可以查询不同账户的实盘资金曲线，以及曲线评价。加减仓会影响实盘资金曲线。刻意采用这种方式，是为了回撤加仓跑出一条漂亮的实盘曲线，心里看着爽（俗称骗自己），看不到回撤实盘更容易坚持，适合心灵脆弱的人。想要不受加减仓影响需要自行稍作修改。

<img width="1706" alt="image" src="https://github.com/RootSherry/NK_CryptoManage/assets/121684306/72065b39-abda-4521-b173-a3e27ab53f23">
<img width="484" alt="image" src="https://github.com/RootSherry/NK_CryptoManage/assets/121684306/4be772a9-4c73-4a5e-89d3-d1966b9ba4b9">
<img width="1585" alt="image" src="https://github.com/RootSherry/NK_CryptoManage/assets/121684306/6c7b681a-d202-414d-bba3-b16c54fe7f19">




### 管理：

在这个界面添加账户API和邮箱，填错了可以在“更新账户”中修改，不要了可以直接删除，不需要在代码中填config
<img width="516" alt="image" src="https://github.com/RootSherry/NK_CryptoManage/assets/121684306/15be5761-7cd1-49c6-afdc-9cdf6a57abb5">


