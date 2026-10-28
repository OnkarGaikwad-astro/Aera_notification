import json
import os

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.oauth2 import service_account
from google.auth.transport.requests import Request

app = FastAPI()

PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "galexi-eebbe")
FIREBASE_SERVICE_ACCOUNT = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


class PushData(BaseModel):
    token: str
    title: str
    body: str


def get_access_token() -> str:
    if not FIREBASE_SERVICE_ACCOUNT:
        raise RuntimeError(
            "Missing FIREBASE_SERVICE_ACCOUNT environment variable"
        )

    try:
        service_account_info = json.loads(FIREBASE_SERVICE_ACCOUNT)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT must contain valid service-account JSON"
        ) from exc

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=[FCM_SCOPE],
    )
    credentials.refresh(Request())
    return credentials.token


@app.get("/")
def home():
    return {"status": "running"}


@app.get("/check")
def check():
    # Do not return the credential contents or other secrets.
    return {
        "project_id_configured": bool(PROJECT_ID),
        "service_account_configured": bool(FIREBASE_SERVICE_ACCOUNT),
    }


@app.post("/send")
def send_notification(data: PushData):
    if not PROJECT_ID:
        raise HTTPException(
            status_code=500,
            detail="Missing FIREBASE_PROJECT_ID environment variable",
        )

    try:
        access_token = get_access_token()
    except Exception as exc:
        # Log the details server-side, but do not expose secrets to callers.
        print(f"Could not obtain Firebase access token: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Firebase authentication is not configured correctly",
        ) from exc

    url = (
        f"https://fcm.googleapis.com/v1/projects/"
        f"{PROJECT_ID}/messages:send"
    )

    message = {
        "message": {
            "token": data.token,
            "notification": {
                "title": data.title,
                "body": data.body,
            },
            "android": {
                "priority": "HIGH",
                "notification": {
                    "channel_id": "high_importance_channel",
                    "visibility": "PUBLIC",
                    "default_sound": True,
                },
            },
        }
    }

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json=message,
            timeout=15,
        )
    except requests.RequestException as exc:
        print(f"FCM request failed: {exc}")
        raise HTTPException(
            status_code=502,
            detail="Could not reach Firebase Cloud Messaging",
        ) from exc

    try:
        response_body = response.json()
    except ValueError:
        response_body = {"message": response.text}

    if not response.ok:
        raise HTTPException(
            status_code=response.status_code,
            detail=response_body,
        )

    return {"status": response.status_code, "response": response_body}
