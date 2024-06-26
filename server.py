import json
import os
import time
from enum import Enum
from typing import Annotated

import requests
from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from pydantic import BaseModel, Field

app = FastAPI(
    title="TradingView IB Trader",
    description="""
    這是一個透過 IB API 來下單的 FastAPI 服務，主要是為了讓使用者可以
    透過TradingView Webhook來執行IB Client Portal下單，並透過 Line Notify 來通知使用者。
    
    # TradingView Webhook JSON 訊息格式
    
    ```
    {
        "accId"     :   "<請填入你的帳號ID>",
        "symbol"    :   "<請填入希望交易的合約ID>,
        "side"      :   "{{strategy.order.action}}",  # 根據TradingView策略的買賣操作, 可能值為"buy"或"sell"
        "amount"    :   {{strategy.order.contracts}}, # 根據TradingView策略的合約數量, 可能值為任意整數，建議固定為1
        "simulated" :   false（若希望只是測試則改為true）
    }
    ```
    
    ## 範例
    
    ```
    {
        "accId"     :   "DU123456",
        "symbol"    :   "620731036",
        "side"      :   "{{strategy.order.action}}",
        "amount"    :   "{{strategy.order.contracts}}",
        "simulated" :   false
    }
    ```
    
    ## TradingView Webhook 設定
    
    """ + f"{os.getenv('API_HOST')}/action",
    swagger_ui_parameters={
        "useUnsafeMarkdown": True
    }

)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LINE_API = 'https://notify-api.line.me/api/notify'

keywords = ['Confirm']


class TVSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class RIGHT(str, Enum):
    CALL = "C"
    PUT = "P"


class TVPayload(BaseModel):
    accId: str = Field(..., description="Account ID")
    symbol: str = Field("620731036", description="Symbol of the contract")
    # order_type: str = Field("MKT", description="Order type", enum=["MKT", "LMT"])
    # price: float = Field(0, description="Price of the contract")
    side: TVSide = Field(TVSide.BUY, description="Side of action")
    amount: str = Field(1, description="Amount of contracts")
    simulated: bool = Field(False, description="Simulated trading")

    def get_info(self):
        side = '買入' if self.side == "buy" else "賣出"
        info = f"""
        帳號ID: {self.accId}
        訂單摘要: \n在合約 {self.symbol} 上進行 {side} {self.amount} 個合約的操作\n
        模擬倉: {self.simulated}\n\n
        合約細節可於登入後前往以下連結查看:
        {os.getenv('API_HOST')}/contract?conid={self.symbol}
        """
        return info


def send_line_notify(message):
    payload = {'message': message}
    headers = {
        'Authorization': 'Bearer ' + os.getenv('LINE_NOTIFY_API_KEY')
    }
    requests.post(LINE_API, data=payload, headers=headers)


def required_login():
    url = f"{os.getenv('CPAPI_URL')}/v1/api/iserver/auth/status"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if not data['authenticated'] or not data['connected']:
            return False
        return True
    return False


def place_order(payload):
    url = f"{os.getenv('CPAPI_URL')}/v1/api/iserver/account/{payload.accId}/orders"
    headers = {'Content-Type': 'application/json'}
    data = {
        "accId": payload.accId,
        "conid": payload.symbol,
        "orderType": "MKT",
        "side": payload.side.upper(),
        "quantity": payload.amount,
        "tif": "DAY",
    }

    data = {"orders": [data]}

    if payload.simulated:
        url = f"{url}/whatif"

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        data = response.json()
        if type(data) is list:
            return data[0]
    except Exception as e:
        send_line_notify(f"操作失敗\n原因：\n\n{str(e)}")
        return {"message": str(e)}


def confirmed_order(orderId: str):
    url = f"{os.getenv('CPAPI_URL')}/v1/api/iserver/reply/{orderId}"
    payload = json.dumps({
        "confirmed": True
    })
    headers = {
        'Content-Type': 'application/json',
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        if type(data) is list:
            return data[0]
    except Exception as e:
        send_line_notify(f"操作失敗\n原因：\n\n{str(e)}")
        return {"message": str(e)}


@app.get("/")
async def read_root():
    return get_swagger_ui_html(
        openapi_url="https://www.interactivebrokers.com/api/doc.json",
        title="TradingView IB Trader",
    )


@app.post("/action", tags=["TradingView專用"])
async def action(payload: TVPayload, good: bool = Depends(required_login)):
    send_line_notify(f"接收到訂單：\n\n{payload.get_info()}")
    if not good:
        send_line_notify(f"接收到訂單，但尚未登入，請前往 {os.getenv('CPAPI_URL')} 登入！")

    order_detail = place_order(payload)
    if payload.simulated:
        send_line_notify(f"訂單送出成功（模擬）：{order_detail}")
        return order_detail

    tries = 0
    while 'order_status' not in order_detail:
        if tries > 5:
            send_line_notify(f"訂單送出失敗\n 原因：測試過多\n\n{order_detail}")
            return order_detail
        if 'id' not in order_detail or 'error' in order_detail:
            send_line_notify(f"訂單送出失敗\n原因：\n\n{order_detail}")
            return order_detail
        order_detail = confirmed_order(order_detail['id'])
        time.sleep(0.5)
        tries += 1

    send_line_notify(f"訂單送出成功\n\n{order_detail}")
    return order_detail


@app.get("/list/accountId", tags=["列出帳號所有子帳戶"])
async def list_account_id(good: bool = Depends(required_login)):
    if good:
        url = f"{os.getenv('CPAPI_URL')}/v1/api/portfolio/accounts"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            send_line_notify(f"操作 /list/accountId 失敗\n原因：\n\n{str(e)}")
            return {"message": str(e)}
    else:
        send_line_notify(f"操作 /list/accountId 失敗，尚未登入，請前往 {os.getenv('CPAPI_URL')} 登入！")
        return {"message": "Not login yet"}


@app.get("/list/futures", tags=["根據關鍵字列出期貨資訊"])
async def list_futures(
        symbols: Annotated[str, Query(..., description="關鍵字")],
        good: bool = Depends(required_login)
):
    if good:
        url = f"{os.getenv('CPAPI_URL')}/v1/api/trsrv/futures?symbols={symbols}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            send_line_notify(f"操作失敗 /list/conid\n原因：\n\n{str(e)}")
            return {"message": str(e)}
    else:
        send_line_notify(f"操作失敗 /list/conid ，尚未登入，請前往 {os.getenv('CPAPI_URL')} 登入！")
        return {"message": "Not login yet"}


@app.get("/list/stock", tags=["根據關鍵字列出股票資訊"])
async def list_stock(
        symbols: Annotated[str, Query(..., description="關鍵字")],
        good: bool = Depends(required_login)
):
    if good:
        url = f"{os.getenv('CPAPI_URL')}/v1/api/trsrv/stocks?symbols={symbols}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            send_line_notify(f"操作失敗 /list/conid\n原因：\n\n{str(e)}")
            return {"message": str(e)}
    else:
        send_line_notify(f"操作失敗 /list/conid ，尚未登入，請前往 {os.getenv('CPAPI_URL')} 登入！")
        return {"message": "Not login yet"}


@app.get("/show", tags=["根據ID列出合約資訊"])
async def list_conid(
        conid: Annotated[int, Query(..., description="合約ID，可由 /list/futures 或 /list/stock 取得")],
        good: bool = Depends(required_login)
):
    if good:
        url = f"{os.getenv('CPAPI_URL')}/v1/api/iserver/contract/{conid}/info"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            send_line_notify(f"操作失敗 /list/conid\n原因：\n\n{str(e)}")
            return {"message": str(e)}
    else:
        send_line_notify(f"操作 /list/conid 失敗，尚未登入，請前往 {os.getenv('CPAPI_URL')} 登入！")
        return {"message": "Not login yet"}


@app.get("/show/opt", tags=["根據標的物ID列出期權合約資訊"])
async def list_opt_conid(
        conid: Annotated[int, Query(..., description="標的物合約ID，可由 /list/futures 或 /list/stock 取得")],
        month: Annotated[str, Query(..., description="月份，格式為MMMYY")] = 'JUN24',
        strike: Annotated[float, Query(..., description="履約價")] = 0,
        right: Annotated[RIGHT, Query(..., description="權利金，可能值為C或P")] = RIGHT.CALL,
        good: bool = Depends(required_login)
):
    if good:
        url = f"{os.getenv('CPAPI_URL')}/v1/api/iserver/secdef/info?conid={conid}&sectype=OPT&month={month}&strike={strike}&right={right}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            send_line_notify(f"操作失敗 /list/conid\n原因：\n\n{str(e)}")
            return {"message": str(e)}
    else:
        send_line_notify(f"操作 /list/conid 失敗，尚未登入，請前往 {os.getenv('CPAPI_URL')} 登入！")
        return {"message": "Not login yet"}


@app.post("/search", tags=["根據關鍵字列出所有合約"])
async def search_contract(
        symbol: Annotated[str, Query(..., description="關鍵字")],
        name: Annotated[bool, Query(..., description="合約名稱")] = True,
        good: bool = Depends(required_login)
):
    if good:
        url = f"{os.getenv('CPAPI_URL')}/v1/api/iserver/secdef/search"
        payload = {
            "symbol": symbol,
            "name": name
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            send_line_notify(f"操作失敗 /search\n原因：\n\n{str(e)}")
            return {"message": str(e)}
    else:
        send_line_notify(f"操作 /search 失敗，尚未登入，請前往 {os.getenv('CPAPI_URL')} 登入！")
        return {"message": "Not login yet"}


@app.get("/strikes", tags=["根據標的ID列出期權的履約價"])
async def list_strikes(
        conid: Annotated[int, Query(..., description="標的物合約ID，可由 /search 取得")],
        month: Annotated[str, Query(..., description="月份，格式為MMM")] = None,
        good: bool = Depends(required_login)
):
    if good:
        url = f"{os.getenv('CPAPI_URL')}/v1/api/iserver/secdef/strikes?conid={conid}&sectype=OPT&month={month.upper()}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            send_line_notify(f"操作失敗 /strikes\n原因：\n\n{str(e)}")
            return {"message": str(e)}
    else:
        send_line_notify(f"操作 /strikes 失敗，尚未登入，請前往 {os.getenv('CPAPI_URL')} 登入！")
        return {"message": "Not login yet"}


official = FastAPI()


def custom_openapi():
    if official.openapi_schema:
        return official.openapi_schema

    openapi_url = 'https://www.interactivebrokers.com/api/doc.json'
    openapi_schema = requests.get(openapi_url).json()

    # remove the server from the schema
    openapi_schema['host'] = 'cpapi.asd555asd.4pass.io'

    openapi_schema['schemes'] = ['https']

    official.openapi_schema = openapi_schema
    return official.openapi_schema


official.openapi = custom_openapi

app.mount("/official", official)
