import json
from datetime import datetime, timedelta

import requests
import uvicorn
from environs import Env
from fastapi import FastAPI
from fastapi.responses import RedirectResponse

env = Env(expand_vars=True)
env.read_env()

fast_api = FastAPI()

CLIENT_ID = env.str("CLIENT_ID_V2")
CLIENT_SECRET = env.str("CLIENT_SECRET_V2")
REDIRECT_URL = env.str("REDIRECT_URI")
ACCOUNT = env.str("ACCOUNT")


def get_access_token(auth_code: str) -> str:
    token_response = requests.post(
        "https://api.tradestation.com/v2/security/authorize",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": auth_code,
            "redirect_uri": REDIRECT_URL,
        }
    )

    # `token_response.json()` returns `refresh_token` to get the refresh token
    return token_response.json()["access_token"]


def get_refresh_token(refresh_token: str):
    token_response = requests.post(
        "https://api.tradestation.com/v2/security/authorize",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token,
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
        f"https://api.tradestation.com/v2/accounts/{ACCOUNT}/orders?since={since}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return orders_response.json()


@fast_api.get("/auth")
async def request_auth():
    url = (
        "https://api.tradestation.com/v2/authorize?"
        "response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URL}"
    )

    return RedirectResponse(url)


@fast_api.get("/")
async def authenticated(code: str):
    orders = get_historical_orders(get_access_token(code))

    with open("data.json", "w+", encoding="UTF-8") as f:
        f.write(json.dumps(orders))

    return orders


if __name__ == "__main__":
    # Go to http://localhost:31022/auth to initialize
    uvicorn.run("main_v2:fast_api", port=31022, reload=True)
