import os
import json
import time
import uuid
import jwt
import requests
from dotenv import load_dotenv

load_dotenv()

YANDEX_SERVICE_KEY_PATH = os.getenv("YANDEX_SERVICE_KEY_PATH")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
IAM_TOKEN_CACHE_PATH = ".cache/iam_token.json"


def load_service_key(path=YANDEX_SERVICE_KEY_PATH):
    with open(path) as f:
        return json.load(f)


def create_jwt_token(service_key):
    now = int(time.time())
    payload = {
        "aud": "https://iam.api.cloud.yandex.net/iam/v1/tokens",
        "iss": service_key["service_account_id"],
        "iat": now,
        "exp": now + 360,
        "jti": str(uuid.uuid4())
    }

    return jwt.encode(
        payload,
        service_key["private_key"],
        algorithm="PS256",
        headers={"kid": service_key["id"]}
    )


def load_cached_iam_token() -> str:
    if not os.path.exists(IAM_TOKEN_CACHE_PATH):
        return None
    with open(IAM_TOKEN_CACHE_PATH) as f:
        data = json.load(f)
    if time.time() < data["expires_at"]:
        return data["iam_token"]
    return None


def get_fresh_iam_token(jwt_token: str) -> str:
    response = requests.post(
        "https://iam.api.cloud.yandex.net/iam/v1/tokens",
        json={"jwt": jwt_token}
    )
    response.raise_for_status()
    iam_token = response.json()["iamToken"]
    os.makedirs(os.path.dirname(IAM_TOKEN_CACHE_PATH), exist_ok=True)
    with open(IAM_TOKEN_CACHE_PATH, "w") as f:
        json.dump({
            "iam_token": iam_token,
            "expires_at": int(time.time()) + 11.5 * 3600
        }, f)
    return iam_token


def get_iam_token(service_key: dict) -> str:
    cached = load_cached_iam_token()
    if cached:
        return cached
    jwt_token = create_jwt_token(service_key)
    return get_fresh_iam_token(jwt_token)
