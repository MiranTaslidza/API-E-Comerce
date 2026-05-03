import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# 1. Definisanje opsega (Scopes)
# Ovo govori Google-u: "Želimo samo da šaljemo mailove u ime korisnika"
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    creds = None
    # Fajl token.pickle čuva korisničke pristupne tokene
    # On se kreira automatski nakon prve uspješne prijave
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    # Ako nema validnih kredencijala, tražimo od korisnika da se prijavi
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Ovdje koristimo tvoj fajl koji si preimenovao
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
            
        # Čuvamo kredencijale za sljedeći put
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('gmail', 'v1', credentials=creds)


