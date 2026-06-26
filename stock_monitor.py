#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股监控提醒脚本
功能：监控持仓标的，触发关键价位时发送邮件/企业微信提醒
作者：锤子爸爸工作室
日期：2026-06-25
"""

import requests
import smtplib
import json
import os
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime
import time

# ============ 配置区 ============

# 持仓配置（可自行修改）
HOLDINGS = [
    {
        "code": "588000",          # 科创50ETF华夏
        "name": "科创50ETF",
        "exchange": "sh",          # sh=上海 sz=深圳
        "cost": 2.171,            # 成本价
        "shares": 200,            # 持仓数量
        "stop_loss": 2.10,        # 止损价
        "take_profit_1": 2.23,    # 止盈价1（卖100股）
        "take_profit_2": 2.30,    # 止盈价2（清仓）
    }
]

# 邮件配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.163.com",
    "smtp_port": 465,
    "sender": "wqk819@163.com",       # 发件人（你的163邮箱）
    "password": "",                    # 邮箱授权码（需手动填写）
    "receiver": "wqk819@163.com",     # 收件人
}

# 企业微信机器人Webhook（可选，填了就同时推企业微信）
WECHAT_WEBHOOK = ""

# 提醒开关
ENABLE_EMAIL = True
ENABLE_WECHAT = False   # 填了WECHAT_WEBHOOK后改为True

# ============ 数据获取 ============

def get_stock_realtime(code, exchange):
    """
    获取实时行情（新浪财经免费API）
    返回：{"price": 最新价, "open": 今开, "high": 最高, "low": 最低, "pre_close": 昨收}
    """
    # 新浪API格式：sh588000 或 sz399006
    symbol = f"{exchange}{code}"
    url = f"https://hq.sinajs.cn/list={symbol}"
    
    try:
        resp = requests.get(url, timeout=10, headers={"Referer": "https://finance.sina.com.cn"})
        resp.encoding = "gbk"
        content = resp.text
        
        if "var hq_str" not in content:
            print(f"❌ 获取 {symbol} 数据失败：{content}")
            return None
        
        # 解析数据：名称,今开,昨收,最新价,最高,最低,...
        data_str = content.split('"')[1]
        fields = data_str.split(",")
        
        if len(fields) < 32:
            print(f"⚠️ {symbol} 数据字段不足")
            return None
        
        return {
            "name": fields[0],
            "open": float(fields[1]) if fields[1] else 0,
            "pre_close": float(fields[2]) if fields[2] else 0,
            "price": float(fields[3]) if fields[3] else 0,
            "high": float(fields[4]) if fields[4] else 0,
            "low": float(fields[5]) if fields[5] else 0,
            "time": fields[31] if len(fields) > 31 else "",
        }
    except Exception as e:
        print(f"❌ 获取 {symbol} 异常：{e}")
        return None


def get_us_stock(symbol="SOXL"):
    """
    获取美股数据（东方财富API）
    SOXL=3倍半导体ETF，用来判断美股科技股情绪
    """
    # 用新浪美股API
    url = f"https://hq.sinajs.cn/list=gb_{symbol.lower()}"
    try:
        resp = requests.get(url, timeout=10, headers={"Referer": "https://finance.sina.com.cn"})
        resp.encoding = "gbk"
        content = resp.text
        
        if "var hq_str" not in content:
            return None
        
        data_str = content.split('"')[1]
        fields = data_str.split(",")
        
        if len(fields) < 10:
            return None
        
        return {
            "symbol": symbol,
            "price": float(fields[1]) if fields[1] else 0,
            "change_pct": float(fields[2]) if fields[2] else 0,
            "name": fields[0],
        }
    except Exception as e:
        print(f"❌ 获取美股 {symbol} 异常：{e}")
        return None


# ============ 分析判断 ============

def analyze_holding(holding, market_data):
    """
    分析持仓，判断是否触发提醒
    返回：{"action": 操作建议, "reason": 原因, "urgency": 紧急程度}
    """
    price = market_data["price"]
    cost = holding["cost"]
    shares = holding["shares"]
    
    float_pnl = (price - cost) * shares
    float_pnl_pct = (price - cost) / cost * 100
    
    result = {
        "code": holding["code"],
        "name": holding["name"],
        "price": price,
        "cost": cost,
        "float_pnl": float_pnl,
        "float_pnl_pct": float_pnl_pct,
        "action": "持有",
        "reason": "",
        "urgency": "normal",   # normal / high / critical
    }
    
    # 止损判断（最高优先级）
    if price <= holding["stop_loss"]:
        result["action"] = "🚨 止损卖出"
        result["reason"] = f"跌破止损线 {holding['stop_loss']} 元"
        result["urgency"] = "critical"
        return result
    
    # 止盈判断
    if price >= holding["take_profit_2"]:
        result["action"] = "🎯 全部止盈"
        result["reason"] = f"达到清仓止盈线 {holding['take_profit_2']} 元"
        result["urgency"] = "high"
        return result
    
    if price >= holding["take_profit_1"]:
        result["action"] = "🎯 部分止盈"
        result["reason"] = f"达到止盈线 {holding['take_profit_1']} 元，建议卖出100股"
        result["urgency"] = "high"
        return result
    
    # 开盘判断（需要open数据）
    open_price = market_data.get("open", 0)
    if open_price > 0:
        gap_pct = (open_price - market_data["pre_close"]) / market_data["pre_close"] * 100
        if gap_pct > 1:
            result["action"] = "📈 高开观察"
            result["reason"] = f"高开 {gap_pct:.2f}%，可等冲高止盈"
            result["urgency"] = "normal"
        elif gap_pct < -1:
            result["action"] = "📉 低开警惕"
            result["reason"] = f"低开 {abs(gap_pct):.2f}%，关注是否止损"
            result["urgency"] = "high"
    
    return result


# ============ 推送模块 ============

def send_email(subject, content):
    """发送163邮箱"""
    if not ENABLE_EMAIL:
        print("📧 邮件推送已关闭")
        return
    
    password = EMAIL_CONFIG.get("password", "")
    if not password:
        print("⚠️ 邮箱授权码未配置，跳过邮件发送")
        print("   请前往 163邮箱 → 设置 → POP3/SMTP → 开启并获取授权码")
        return
    
    try:
        msg = MIMEText(content, "plain", "utf-8")
        msg["From"] = Header(EMAIL_CONFIG["sender"], "utf-8")
        msg["To"] = Header(EMAIL_CONFIG["receiver"], "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        
        server = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
        server.login(EMAIL_CONFIG["sender"], password)
        server.sendmail(EMAIL_CONFIG["sender"], [EMAIL_CONFIG["receiver"]], msg.as_string())
        server.quit()
        print(f"✅ 邮件已发送到 {EMAIL_CONFIG['receiver']}")
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")


def send_wechat(content):
    """发送企业微信机器人消息"""
    if not ENABLE_WECHAT or not WECHAT_WEBHOOK:
        print("💬 企业微信推送已关闭")
        return
    
    try:
        data = {
            "msgtype": "text",
            "text": {"content": content}
        }
        resp = requests.post(WECHAT_WEBHOOK, json=data, timeout=10)
        result = resp.json()
        if result.get("errcode") == 0:
            print("✅ 企业微信消息已发送")
        else:
            print(f"❌ 企业微信发送失败：{result}")
    except Exception as e:
        print(f"❌ 企业微信发送异常：{e}")


def format_report(results, trigger_type="常规监控"):
    """格式化报告内容"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    lines = [
        f"📊 【A股监控提醒】{trigger_type}",
        f"时间：{now}",
        "=" * 40,
    ]
    
    for r in results:
        pnl_sign = "+" if r["float_pnl"] >= 0 else ""
        pct_sign = "+" if r["float_pnl_pct"] >= 0 else ""
        
        lines += [
            f"",
            f"📌 {r['name']}（{r['code']}）",
            f"   现价：{r['price']:.3f}  成本：{r['cost']:.3f}",
            f"   浮盈：{pnl_sign}{r['float_pnl']:.1f}元（{pct_sign}{r['float_pnl_pct']:.2f}%）",
            f"   👉 {r['action']}",
            f"   💡 {r['reason']}",
        ]
        
        if r["urgency"] == "critical":
            lines.append("   ⚠️⚠️⚠️ 紧急情况，请立即处理！")
    
    lines += [
        "",
        "=" * 40,
        "📱 以上为自动监控提醒，请手动下单。",
        "💡 修改持仓配置请编辑 HOLDINGS 变量。",
    ]
    
    return "\n".join(lines)


# ============ 主流程 ============

def run_monitor(trigger_type="常规监控"):
    """执行一次完整监控"""
    print(f"\n{'='*50}")
    print(f"🚀 开始监控 - {trigger_type} - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*50}")
    
    results = []
    
    for holding in HOLDINGS:
        print(f"\n📡 获取 {holding['name']}（{holding['exchange']}{holding['code']}）行情...")
        market_data = get_stock_realtime(holding["code"], holding["exchange"])
        
        if not market_data or market_data["price"] == 0:
            print(f"⚠️ {holding['name']} 无有效行情数据，跳过")
            continue
        
        print(f"   ✅ 现价：{market_data['price']:.3f}  今开：{market_data['open']:.3f}")
        
        analysis = analyze_holding(holding, market_data)
        results.append(analysis)
    
    if not results:
        print("❌ 没有有效数据，不发送提醒")
        return
    
    # 生成报告
    report = format_report(results, trigger_type)
    print(f"\n📄 报告预览：\n{report}")
    
    # 判断是否需要推送（关键价位触发时才推，避免刷屏）
        # 每次运行都推送邮件
    is_urgent = any(r["urgency"] in ["high", "critical"] for r in results)
    
    if is_urgent:
        print("\n📤 触发关键价位，发送紧急提醒...")
        subject = f"🚨【A股提醒】{results[0]['name']} {results[0]['action']}"
    else:
        print("\n📧 发送常规监控邮件...")
        subject = f"📊【A股监控】{results[0]['name']} 现价{results[0]['price']:.3f}"
    
    send_email(subject, report)
    send_wechat(report)

        # 如果是GitHub Actions运行，日志就是最好的记录


def run_us_market_check():
    """美股收盘后检查（晚上22:00执行）"""
    print(f"\n{'='*50}")
    print(f"🌙 美股收盘检查 - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*50}")
    
    symbols = ["SOXL", "SOXS", "TQQQ", "SQQQ"]   # 半导体杠杆ETF，反映科技股情绪
    lines = ["📡 【美股收盘速报】", f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
    
    for sym in symbols:
        data = get_us_stock(sym)
        if data:
            sign = "+" if data["change_pct"] >= 0 else ""
            lines.append(f"   {data['symbol']}：{data['price']:.2f}（{sign}{data['change_pct']:.2f}%）")
        else:
            lines.append(f"   {sym}：获取失败")
    
    lines += [
        "",
        "💡 解读：",
        "   SOXL大涨 → 明天A股科技/半导体高开概率大",
        "   SOXL大跌 → 明天A股科技/半导体低开概率大",
        "   建议明天9:15查看集合竞价再决定操作。",
    ]
    
    report = "\n".join(lines)
    print(f"\n{report}")
    
    # 美股检查一律推送
    subject = "【美股收盘】科技股情绪参考"
    send_email(subject, report)
    send_wechat(report)


# ============ 入口 ============

if __name__ == "__main__":
    import sys
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "monitor"
    
    if mode == "monitor":
        run_monitor("手动触发")
    elif mode == "us":
        run_us_market_check()
    elif mode == "auto":
        # 自动判断当前时间，选择合适的监控模式
        hour = datetime.now().hour
        if hour >= 21 or hour <= 4:
            run_us_market_check()
        else:
            run_monitor("定时触发")
    else:
        print(f"未知模式：{mode}")
        print("用法：python monitor.py [monitor|us|auto]")
