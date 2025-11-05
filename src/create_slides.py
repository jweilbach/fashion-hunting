#!/usr/bin/env python3
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import yaml

def main():
    with open("config/settings.yaml", "r") as f:
        settings = yaml.safe_load(f)
    title = settings.get("slides_title", "ABMC — Earned Media Report")

    scopes = ['https://www.googleapis.com/auth/presentations']
    creds = Credentials.from_service_account_file('gcp_service_account.json', scopes=scopes)
    slides = build('slides', 'v1', credentials=creds)

    presentation = slides.presentations().create(body={"title": title}).execute()
    pid = presentation['presentationId']

    requests_batch = [
      {"createSlide": {"slideLayoutReference": {"predefinedLayout": "TITLE"}}},
      {"createSlide": {"slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"}}},
      {"createSlide": {"slideLayoutReference": {"predefinedLayout": "TITLE_AND_TWO_COLUMNS"}}}
    ]

    slides.presentations().batchUpdate(presentationId=pid, body={"requests": requests_batch}).execute()
    print(f"Created deck: https://docs.google.com/presentation/d/{pid}/edit")

if __name__ == "__main__":
    main()
