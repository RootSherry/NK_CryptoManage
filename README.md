# NK_CryptoManage
一款加密货币的投资和管理平台。

A cryptocurrency investment and management platform.
# 平台功能

### **主页：**![image.png](https://bbs-quantclass-cn-1253788117.file.myqcloud.com/public/attachments/2024/01/26/DaY0O4fUnGk7hQeiBDiw7aoOOdlLaq4CI1C1e83f.png?imageMogr2/thumbnail/500x500 "219024")

### 购买：

- 可以选择不同的账户使用USDT进行购买操祚
- 购买操作会优先使用现货账户中的USDT。如果USDT资金不足，系统会自动从U本位合约账户中划转补充。购买完成后，系统将现货账户中的BTC、ETH、USDT转入U本位合约账户充当策略保证金，其他币种保留在现货账户。
- 使用说明写在了界面上
- 可以在查询界面中，查询不同账号的购买记录、买入总量以及平均买入成本

![c35f95505dc8b0ae6e69543c2d170ec.jpg](https://bbs-quantclass-cn-1253788117.file.myqcloud.com/public/attachments/2024/01/26/ku7klsv8RrtdXsqoqsa26PGfd5D4UlyxK0wds8tT.jpg?imageMogr2/thumbnail/500x500 "219025")![image.png](https://bbs-quantclass-cn-1253788117.file.myqcloud.com/public/attachments/2024/01/26/EnJuS74FAXBUsFrpPLGoJHZuaohg7GSd4bRJ6JmR.png?imageMogr2/thumbnail/500x500 "219026")

### 转账：

- 在不同子母账户之前进行转账操作，只支持BTC、USDT、ETH、BNB（可自行代码添加）
- 转账操作会优先使用转出账户的现货余额。如果余额不足，系统会自动从U本位合约账户中划转补充。转入账户收到资金后，会自动将其转入U本位合约账户中用作U本位策略保证金。
- 可以在查询界面中，查询不同账号在自定义时间内的转账记录
- 必须填写主账号，且命名为Root，否则无法完成转账操作。(在管理界面中添加主账号)
  ![image.png](https://bbs-quantclass-cn-1253788117.file.myqcloud.com/public/attachments/2024/01/26/GmsQ01xXjN9D6e7arIGP8la8boDuEVeyMfI34U92.png?imageMogr2/thumbnail/500x500 "219028")![image.png](https://bbs-quantclass-cn-1253788117.file.myqcloud.com/public/attachments/2024/01/26/iUtfNi5Pf1afP95F2OCFZqmZfE96vx4IQm75Rge9.png?imageMogr2/thumbnail/500x500 "219029")

### 查询：

除了前面提到的查询购买记录和转账记录，还可以：

- 查询账户余额，包含现货和U本位账户中的币种数量以及价值
- 查询策略表现，可以查询不同账户的实盘资金曲线，以及曲线评价。评价方式对标中性f1框架，大家可以自行对比实盘与回测是否表现一致。数据记录的方式参考了潇老板的帖子[【复盘系统，V2升级版本】基金净值法，出入J记录维护 - 量化小论坛 (quantclass.cn)](https://bbs.quantclass.cn/thread/25619)，但是没有使用基金净值法。就是说，加减仓会影响实盘资金曲线。刻意采用这种方式，是为了回撤加仓跑出一条漂亮的实盘曲线，心里看着爽（俗称骗自己），看不到回撤实盘更容易坚持，适合心灵脆弱的老板。想要不受加减仓影响需要自行稍作修改。

![image.png](https://bbs-quantclass-cn-1253788117.file.myqcloud.com/public/attachments/2024/01/26/AzSn3QbbAZ5HdxPjvrG9JjBEnYSpXjIw7XzRnd26.png?imageMogr2/thumbnail/500x500 "219030")![image.png](https://bbs-quantclass-cn-1253788117.file.myqcloud.com/public/attachments/2024/01/26/bdd9ise1ezReYPcE0BpGyLMZoy7BLzXsY1kfuDjA.png?imageMogr2/thumbnail/500x500 "219031")
![image.png](https://bbs-quantclass-cn-1253788117.file.myqcloud.com/public/attachments/2024/01/26/95yOsBVVX8j4fGqyxejhfqfWiYrnu8H072xVBJix.png?imageMogr2/thumbnail/500x500 "219032")

### 管理：

在这个界面添加账户API和邮箱，填错了可以在“更新账户”中修改，不要了可以直接删除，不需要在代码中填config
![image.png](https://bbs-quantclass-cn-1253788117.file.myqcloud.com/public/attachments/2024/01/26/5YZRx0KhYKgb49P15nh3JWOc1prv7JBqhra8dsEw.png?imageMogr2/thumbnail/500x500 "219034")

# 使用说明

直接运行附件中的app.py文件即可。

在平台里自行注册账号填写api信息即可使用。

要使用查询资金曲线功能还需运行curve_run.py文件。
