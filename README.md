# 📊 A股监控自动提醒系统

> 完全免费 · 无需服务器 · GitHub Actions托管 · 邮件/企业微信推送

## ✨ 功能

- 📡 **实时监控**：每个交易日自动检查持仓
- 🚨 **关键价位提醒**：触发止损/止盈时立即推送
- 🌙 **美股收盘速报**：每晚22:00推送美股科技股情绪，辅助判断次日A股走势
- 📧 **邮件推送**：发送到你的163邮箱
- 💬 **企业微信推送**（可选）：消息直达微信

## 📐 架构

```
GitHub Actions（免费）
    ├─ 9:15 北京时间 → 集合竞价后检查
    ├─ 9:30 北京时间 → 开盘检查
    ├─ 9:45 北京时间 → 开盘后确认
    └─ 22:00 北京时间 → 美股收盘检查
        ↓
    Python脚本（爬行情 + 分析判断）
        ↓
    163邮箱 / 企业微信机器人
        ↓
    📱 你收到提醒 → 手动下单
```

## 🚀 部署步骤（共3步，10分钟）

### 第1步：开启163邮箱SMTP并获取授权码

1. 登录 [163邮箱](https://mail.163.com)
2. 点击右上角 **设置** → **POP3/SMTP/IMAP**
3. 开启 **IMAP/SMTP服务**
4. 会显示一个**授权码**（不是你的邮箱密码！）
5. 复制这个授权码，第3步要用

> ⚠️ 授权码只显示一次，记得保存！

### 第2步：Fork或上传脚本到你的GitHub仓库

**方式A：用现有仓库**
1. 把以下两个文件上传到你的GitHub仓库：
   - `stock_monitor.py`
   - `.github/workflows/monitor.yml`

**方式B：创建新仓库**
1. 前往 [GitHub](https://github.com) → New Repository
2. 仓库名随便取，比如 `stock-monitor`
3. 上传上面两个文件

### 第3步：配置GitHub Secrets（注入邮箱授权码）

1. 进入你的GitHub仓库
2. 点击 **Settings** → **Secrets and variables** → **Actions**
3. 点击 **New repository secret**
4. Name 填：`EMAIL_PASSWORD`
5. Secret 填：第1步获取的**163邮箱授权码**
6. 点击 **Add secret**

### 第4步：手动触发测试

1. 进入仓库 **Actions** 标签页
2. 点击 **A股监控提醒** 工作流
3. 点击 **Run workflow** → 选择 `monitor` 或 `us`
4. 查看运行日志，确认邮件是否收到

---

## ⚙️ 修改持仓配置

编辑 `stock_monitor.py` 中的 `HOLDINGS` 变量：

```python
HOLDINGS = [
    {
        "code": "588000",          # 股票代码
        "name": "科创50ETF",       # 名称
        "exchange": "sh",          # sh=上海 sz=深圳
        "cost": 2.171,            # 成本价
        "shares": 200,            # 持仓数量
        "stop_loss": 2.10,        # 止损价
        "take_profit_1": 2.23,    # 止盈价1
        "take_profit_2": 2.30,    # 止盈价2
    }
]
```

**可以添加多个持仓**，比如：

```python
HOLDINGS = [
    {"code": "588000", "name": "科创50ETF", "exchange": "sh", ...},
    {"code": "159915", "name": "创业板ETF", "exchange": "sz", ...},
]
```

修改后推送到GitHub，自动生效。

---

## 💬 开启企业微信推送（可选）

企业微信推送比邮件更及时，消息直接到微信。

### 创建企业微信群机器人

1. 下载 **企业微信** App（个人也可以注册企业）
2. 创建一个群（可以只拉自己一个人）
3. 群设置 → **群机器人** → **添加机器人**
4. 复制 **Webhook地址**（类似 `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx`）

### 配置到脚本

1. 打开 `stock_monitor.py`
2. 找到 `WECHAT_WEBHOOK = ""`
3. 把Webhook地址填进去
4. 找到 `ENABLE_WECHAT = False`，改为 `ENABLE_WECHAT = True`
5. 推送到GitHub

---

## 📅 定时任务时间表

| 北京时间 | UTC时间 | 任务 |
|----------|---------|------|
| 周一~周五 09:15 | 01:15 | 集合竞价后检查 |
| 周一~周五 09:30 | 01:30 | 开盘检查 |
| 周一~周五 09:45 | 01:45 | 开盘后确认 |
| 周一~周五 22:00 | 14:00 | 美股收盘检查 |

> ⚠️ 国内节假日GitHub Actions不会自动识别，需要手动暂停工作流。

---

## 🔧 常见问题

### Q：邮件收不到？
- 检查163邮箱授权码是否正确（不是邮箱密码）
- 检查GitHub Secrets是否正确配置
- 查看GitHub Actions运行日志有没有报错

### Q：GitHub Actions会不会收费？
- 免费账户每月有2000分钟免费额度，这个脚本每次运行约1分钟，完全够用

### Q：能不能自动下单？
- 不建议。自动下单有风险，且东方财富没有开放API。当前方案是"提醒→手动下单"，安全可靠。

### Q：我想暂停监控？
- 进入GitHub仓库 → Actions → 选择工作流 → 右上角 **Disable workflow**

---

## 📝 文件清单

```
stock_monitor.py              # 主脚本
.github/workflows/monitor.yml # GitHub Actions配置
README.md                    # 本文件
```

---

## 🛠️ 技术栈

- **Python 3.11**：核心逻辑
- **GitHub Actions**：免费定时任务托管
- **新浪财经API**：实时行情数据（免费）
- **163邮箱SMTP**：邮件推送
- **企业微信Webhook**：微信消息推送（可选）

---

> 由锤子爸爸工作室 · 2026-06-25 构建
> 有问题请联系：wqk819@163.com
