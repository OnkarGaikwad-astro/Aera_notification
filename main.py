from fastapi import FastAPI
from pydantic import BaseModel
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests

SERVICE_ACCOUNT_FILE = "galexi-eebbe-firebase-adminsdk-fbsvc-f445bdfa82.json"
PROJECT_ID = "galexi-eebbe"

app = FastAPI()

class PushData(BaseModel):
    token: str
    title: str
    body: str

def get_access_token():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/firebase.messaging"]
    )
    creds.refresh(Request())
    return creds.token

@app.get("/")
def home():
    return {"status": "running"}


@app.get("/check")
def check():
    import os
    return {"exists": os.path.isfile(SERVICE_ACCOUNT_FILE)}



@app.post("/send")
def send_notification(data: PushData):
    access_token = get_access_token()

    url = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"
    
    message = {
        "message": {
            "token": data.token,
            "notification": {
                "title": data.title,
                "body": data.body
            },
            "android": {
                "priority": "HIGH",
                "notification": {
                    "channel_id": "high_importance_channel",
                    "visibility": "PUBLIC",
                    "default_sound": True
                }
            }
        }
    }

    res = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json=message
    )

    return {"status": res.status_code, "response": res.text}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)