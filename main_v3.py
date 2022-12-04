import json
import secrets
from datetime import datetime, timedelta

import requests
import uvicorn
from environs import Env
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse

env = Env(expand_vars=True)
env.read_env()

fast_api = FastAPI()

CLIENT_ID = env.str("CLIENT_ID_V3")
CLIENT_SECRET = env.str("CLIENT_SECRET_V3")
REDIRECT_URL = env.str("REDIRECT_URI")
ACCOUNT = env.str("ACCOUNT")

states: list[str] = []


def get_access_token(auth_code: str) -> str:
    token_response = requests.post(
        "https://signin.tradestation.com/oauth/token",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": auth_code,
            "redirect_uri": REDIRECT_URL,
        }
    )

    return token_response.json()["access_token"]


def get_refresh_token(expired_token: str):
    token_response = requests.post(
        "https://signin.tradestation.com/oauth/token",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": expired_token,
        }
    )

    return token_response.json()["access_token"]


def get_orders(access_token: str):
    orders_response = requests.get(
        f"https://api.tradestation.com/v3/brokerage/accounts/{ACCOUNT}/orders",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return orders_response.json()


def get_historical_orders(access_token: str):
    since = (datetime.today() - timedelta(days=89)).strftime("%Y-%m-%d")
    orders_response = requests.get(
        f"https://api.tradestation.com/v3/brokerage/accounts/{ACCOUNT}/historicalorders?since={since}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return orders_response.json()


@fast_api.get("/auth")
async def request_auth():
    state = secrets.token_hex(32)
    url = (
        "https://signin.tradestation.com/authorize?"
        "response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URL}&"
        "audience=https://api.tradestation.com&"
        f"state={state}&"
        "scope=openid%20offline_access%20ReadAccount"
    )

    states.append(state)

    return RedirectResponse(url)


@fast_api.get("/")
async def authenticated(code: str, state: str):
    if state not in states:
        raise HTTPException(403, "state mismatch")

    orders = get_historical_orders(get_access_token(code))

    with open("data.json", "w+", encoding="UTF-8") as f:
        f.write(json.dumps(orders))

    return orders


if __name__ == "__main__":
    # Go to http://localhost:31022/auth to initialize
    uvicorn.run("main_v3:fast_api", port=31022, reload=True)
