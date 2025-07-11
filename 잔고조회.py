from dotenv import load_dotenv
load_dotenv()

import os
from pybit.unified_trading import HTTP


# 환경변수에서 API 키/시크릿 불러오기
api_key = os.environ.get("BYBIT_API_KEY")
api_secret = os.environ.get("BYBIT_API_SECRET")

# print("API KEY:", api_key)
# print("API SECRET:", api_secret)
session = HTTP(
    testnet=True,
    api_key=api_key,
    api_secret=api_secret
)

def get_balance(coin="USDT"):
    try:
        res = session.get_wallet_balance(accountType="UNIFIED", coin=coin)
        return res['result']['list'][0]['totalEquity']
    except Exception as e:
        return f"잔고조회 에러: {e}"

if __name__ == "__main__":
    balance = get_balance("USDT")
    print("USDT 잔고:", balance)
