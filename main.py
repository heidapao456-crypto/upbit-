import time
import requests

# ===== 配置区 =====
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1410605627549552660/irVKGqHysnuEWm0LTQ5MODk8OJh0iVziEjarfsnIJmWYE2nSUdrFBnq2PfZFZxM8LN-b"
ETHERSCAN_API_KEY = "KBXFARN1ESDRM5GISP964FXRZP8QR1DUB8"

UPBIT_WALLETS_ETH = [
    "0xe3792A9c235D434B702023b33F03C48C41631090",
    "0xb4c93d3129f04a3d0f600ddccadb98c50e6e2619",
    "0xba826fec90cefdf6706858e5fbafcb27a290fbe0",
    "0x9a9c4219bb88918758ccf83928fa79a563031a16"
]

POLL_INTERVAL = 10  # 秒
# ==================

seen_tokens = set()  # 已监控过的代币

def send_discord_message(content: str):
    try:
        res = requests.post(DISCORD_WEBHOOK, json={"content": content})
        if res.status_code != 204:
            print(f"❌ Discord 推送失败: {res.text}")
    except Exception as e:
        print(f"❌ Discord 推送异常: {e}")

def fetch_wallet_tokens(wallet: str):
    """获取某个钱包最近代币交易"""
    url = "https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "tokentx",
        "address": wallet,
        "page": 1,
        "offset": 20,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("status") == "1":
            return data["result"]
    except Exception as e:
        print(f"⚠️ 获取交易失败 {wallet}: {e}")
    return []

def fetch_upbit_markets():
    """获取 Upbit 已上线的交易对"""
    try:
        url = "https://api.upbit.com/v1/market/all"
        res = requests.get(url, timeout=10)
        data = res.json()
        markets = [m["market"] for m in data]  # 例: "KRW-BTC"
        return markets
    except Exception as e:
        print(f"⚠️ 获取 Upbit 市场失败: {e}")
        return []

def monitor():
    print("✅ Upbit Fast Listing Monitor started.")
    while True:
        markets = fetch_upbit_markets()
        for wallet in UPBIT_WALLETS_ETH:
            txs = fetch_wallet_tokens(wallet)
            for tx in txs:
                token_address = tx["contractAddress"]
                token_symbol = tx["tokenSymbol"]
                token_name = tx["tokenName"]

                if token_address not in seen_tokens:
                    seen_tokens.add(token_address)

                    symbol_upper = token_symbol.upper()
                    listed = any(symbol_upper in m for m in markets)

                    if listed:
                        msg = f"✅ Upbit 已正式上线: {token_name} ({token_symbol})\n🔗 合约: {token_address}"
                    else:
                        msg = f"🚨 Upbit 热钱包发现新代币（可能即将上线）\n📌 代币: {token_name} ({token_symbol})\n🔗 合约: {token_address}\n💼 钱包: {wallet}"

                    print(msg)
                    send_discord_message(msg)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    monitor()
