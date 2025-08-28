import os
import requests
import pandas as pd
import numpy as np

# ========= 配置 =========
DISCORD_WEBHOOK_BINGX = os.getenv("https://discord.com/api/webhooks/1410621268297912413/7d53-mjxPw0Az4y8TOeIWC7Axd4y9J3AsSwnGk93U93aATqkGXEXm_UROHpeTb8kTIwU")
DISCORD_WEBHOOK_UPBIT = os.getenv("https://discord.com/api/webhooks/1410605627549552660/irVKGqHysnuEWm0LTQ5MODk8OJh0iVziEjarfsnIJmWYE2nSUdrFBnq2PfZFZxM8LN-b")
ETHERSCAN_API_KEY = os.getenv("EDBDUQ59YZIIPTR4Z6C38TZR39TIENM3D5")

# 已知 Upbit ETH 热钱包（可增减）
UPBIT_WALLETS_ETH = [
    "0x0fC0e57eC17361E165e4A9257f1D6E8c6a8e890d",
    "0xA7D9ddbe1f17865597fbd27EC712455208B6B76D",
    "0x30f5F5B2dc5b7F21Ab532d75A1B01D1d5bB0e3e0",
    "0x4bF2dF986cD8A89bBB9fD8d5A004A762954b78F4",
    "0x7f19720A857F834887FC9A7bC0a0fBe7Fc7f8102"
]

# BingX 行情币种
BINGX_SYMBOLS = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]
# ========================


def send_discord_message(webhook_url, msg: str):
    """发送消息到 Discord"""
    try:
        requests.post(webhook_url, json={"content": msg})
    except Exception as e:
        print("发送 Discord 消息失败:", e)


# ======================== BingX 行情检查 ========================
def check_bingx():
    for symbol in BINGX_SYMBOLS:
        url = f"https://api-swap-rest.bingbon.pro/api/v1/market/kline?symbol={symbol}&interval=60&limit=100"
        try:
            data = requests.get(url, timeout=10).json()
            if "data" not in data:
                continue
            df = pd.DataFrame(data["data"], columns=["time","o","h","l","c","v"])
            df[["o","h","l","c"]] = df[["o","h","l","c"]].astype(float)

            closes = df["c"].values
            sma20 = pd.Series(closes).rolling(20).mean().iloc[-1]
            rsi = calc_rsi(closes, 14)
            macd, signal = calc_macd(closes)

            if closes[-1] > sma20 and rsi > 50 and macd > signal:
                send_discord_message(DISCORD_WEBHOOK_BINGX, f"📈 {symbol} 买入信号 (RSI={rsi:.2f})")
            elif closes[-1] < sma20 and rsi < 50 and macd < signal:
                send_discord_message(DISCORD_WEBHOOK_BINGX, f"📉 {symbol} 卖出信号 (RSI={rsi:.2f})")
        except Exception as e:
            print(f"BingX 检查 {symbol} 出错:", e)


def calc_rsi(prices, period=14):
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)

    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        upval = max(delta, 0)
        downval = -min(delta, 0)
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)
    return rsi[-1]


def calc_macd(prices, fast=12, slow=26, signal=9):
    prices = pd.Series(prices)
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd.iloc[-1], signal_line.iloc[-1]


# ======================== Upbit 钱包检查 ========================
def check_upbit():
    for wallet in UPBIT_WALLETS_ETH:
        # ETH 转账
        url_eth = f"https://api.etherscan.io/api?module=account&action=txlist&address={wallet}&sort=desc&apikey={ETHERSCAN_API_KEY}"
        # ERC20 转账
        url_token = f"https://api.etherscan.io/api?module=account&action=tokentx&address={wallet}&sort=desc&apikey={ETHERSCAN_API_KEY}"
        try:
            res_eth = requests.get(url_eth, timeout=10).json()
            if res_eth["status"] == "1" and len(res_eth["result"]) > 0:
                tx = res_eth["result"][0]
                msg = f"💰 Upbit ETH 转账:\n钱包: {wallet}\n哈希: {tx['hash']}\n数量: {int(tx['value'])/1e18:.4f} ETH"
                send_discord_message(DISCORD_WEBHOOK_UPBIT, msg)

            res_token = requests.get(url_token, timeout=10).json()
            if res_token["status"] == "1" and len(res_token["result"]) > 0:
                tx = res_token["result"][0]
                msg = f"🔔 Upbit ERC20 转账:\n钱包: {wallet}\n哈希: {tx['hash']}\n代币: {tx['tokenSymbol']} {int(tx['value'])/(10**int(tx['tokenDecimal'])):.4f}"
                send_discord_message(DISCORD_WEBHOOK_UPBIT, msg)

        except Exception as e:
            print(f"Upbit 钱包检查 {wallet} 出错:", e)


# ======================== 主程序 ========================
if __name__ == "__main__":
    print("开始检查 BingX 和 Upbit ...")
    check_bingx()
    check_upbit()
    print("检查完成，程序退出。")
