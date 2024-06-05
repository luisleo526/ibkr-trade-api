import os
from enum import Enum

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LINE_API = 'https://notify-api.line.me/api/notify'
IBKR_API = 'https://localhost:5000'

class TVSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TVPayload(BaseModel):
    symbol: int = Field(..., description="Symbol of the contract")
    side: TVSide = Field(TVSide.BUY, description="Side of action")
    amount: int = Field(1, description="Amount of contracts")


def send_line_notify(message):
    payload = {'message': message}
    headers = {
        'Authorization': 'Bearer ' + os.getenv('LINE_NOTIFY_API_KEY')
    }
    requests.post(LINE_API, data=payload, headers=headers)


@app.post("/test")
async def action(payload: TVPayload):
    send_line_notify(f"Symbol: {payload.symbol}, Side: {payload.side}, Amount: {payload.amount}")
    return {"payload": payload.dict()}
