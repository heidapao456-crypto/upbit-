import os
import time
import hmac
import hashlib
import requests
import threading
import numpy as np
import pandas as pd

# ================= 配置 =================
# Discord Webhooks
DISCORD_WEBHOOK_BINGX = "https://discord.com/api/webhooks/1410621268297912413/7d53-mjxPw0Az4y8TOeIWC7Axd4y9J3AsSwnGk93U93aATqkGXEXm_UROHpeTb8kTIwU"
DISCORD_WEBHOOK_UPBIT = "https://discord.com/api/webhooks/1410605627549552660/irVKGqHysnuEWm0LTQ5MODk8OJh0iVziEjarfsnIJmWYE2nSUdrFBnq2PfZFZxM8LN-b"

# BingX 配置
BINGX_SYMBOLS = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]  # 监控交易对
INTERVALS = {"60": "1小时", "240": "4小时", "1440": "日线"}  # K线周期
POLL_INTERVAL = 60  # 每60秒检查一次

# Upbit 配置
ETHERSCAN_API_KEY = "EDBDUQ59YZIIPTR4Z6C38TZR39TIENM3D5"
UPBIT_WALLETS_ETH = ["0x59c5d1c13bfefe0f63f01f596f331d0b17b6c23f"]  # Upbit 钱包地址
# ========================================


# ============ 工具函数 ============
def send_discord_message(webhook_url: str, message: str):
    try:
        requests.post(webhook_url, json={"content": message}, timeout=5)
    except Exception as e:
        print("❌ Discord 发送失败:", e)

# ============ BingX 监控 ============
def fetch_bingx_klines(symbol: str, interval: str, limit: int = 100):
    url = f"https://open-api.bingx.com/openApi/spot/v1/market/kline?symbol={symbol}&interval={interval}&limit={limit}"
    r = requests.get(url, timeout=5).json()
    data = r.get("data", [])
    if not data:
        return None
    df = pd.DataFrame(data, columns=["openTime","open","high","low","close","volume","closeTime"])
    df["close"] = df["close"].astype(float)
    return df

def compute_indicators(prices):
    ema12 = prices.ewm(span=12).mean()
    ema26 = prices.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    delta = prices.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=14).mean()
    avg_loss = pd.Series(loss).rolling(window=14).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return ema12.iloc[-1], ema26.iloc[-1], macd.iloc[-1], signal.iloc[-1], rsi.iloc[-1]

def monitor_bingx():
    while True:
        try:
            for symbol in BINGX_SYMBOLS:
                for interval, name in INTERVALS.items():
                    df = fetch_bingx_klines(symbol, interval)
                    if df is None: continue
                    ema12, ema26, macd, signal, rsi = compute_indicators(df["close"])

                    price = df["close"].iloc[-1]
                    message = None

                    if ema12 > ema26 and macd > signal and rsi < 70:
                        message = f"🚨 BingX 多头信号\n交易对: {symbol}\n周期: {name}\n📈 BUY\n价格: {price:.2f}\nRSI: {rsi:.2f}\nMACD: {macd:.2f} vs {signal:.2f}"

                    elif ema12 < ema26 and macd < signal and rsi > 30:
                        message = f"🚨 BingX 空头信号\n交易对: {symbol}\n周期: {name}\n📉 SELL\n价格: {price:.2f}\nRSI: {rsi:.2f}\nMACD: {macd:.2f} vs {signal:.2f}"

                    if message:
                        send_discord_message(DISCORD_WEBHOOK_BINGX, message)

            time.sleep(POLL_INTERVAL)

        except Exception as e:
            print("❌ BingX 监控错误:", e)
            time.sleep(10)

# ============ Upbit 监控 ============
def monitor_upbit():
    last_tx = {addr: None for addr in UPBIT_WALLETS_ETH}
    while True:
        try:
            for addr in UPBIT_WALLETS_ETH:
                url = f"https://api.etherscan.io/api?module=account&action=txlist&address={addr}&sort=desc&apikey={ETHERSCAN_API_KEY}"
                r = requests.get(url, timeout=5).json()
                txs = r.get("result", [])
                if not txs: continue
                latest = txs[0]["hash"]

                if last_tx[addr] != latest:
                    last_tx[addr] = latest
                    value = int(txs[0]["value"]) / 1e18
                    to_addr = txs[0]["to"]
                    send_discord_message(
                        DISCORD_WEBHOOK_UPBIT,
                        f"🚨 Upbit 钱包新交易\n地址: {addr}\n交易哈希: {latest}\n数量: {value:.4f} ETH\nTo: {to_addr}"
                    )

            time.sleep(30)

        except Exception as e:
            print("❌ Upbit 监控错误:", e)
            time.sleep(10)

# ============ 主程序 ============
if __name__ == "__main__":
    t1 = threading.Thread(target=monitor_bingx, daemon=True)
    t2 = threading.Thread(target=monitor_upbit, daemon=True)

    t1.start()
    t2.start()

    print("✅ BingX & Upbit 监控器已启动，正在运行中...")

    while True:
        time.sleep(60)
