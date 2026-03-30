import requests
import json
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

def fetch_sportspage_data():
    """Third Fallback fetcher for THE-BASKET-BALL-BANKER- using Sportspage Feeds API (RapidAPI)"""
    # Check Streamlit Secrets first (for Cloud), then Env (for Local)
    try:
        api_key = st.secrets["SPORTSPAGE_API_KEY"]
    except:
        api_key = os.getenv("SPORTSPAGE_API_KEY")
        
    if not api_key:
        print("[ERROR] No SPORTSPAGE_API_KEY found in secrets or .env")
        return []
    
    # Endpoints: We fetch Odds (league matches NBA for the banker's core logic)
    url = "https://sportspage-feeds.p.rapidapi.com/odds"
    params = {"league": "NBA"}
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "sportspage-feeds.p.rapidapi.com"
    }
    
    print("[ODDS-SPORT] Fetching tertiary market data from Sportspage Feeds...")
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json().get('results', [])
            os.makedirs(".tmp/cache", exist_ok=True)
            with open(".tmp/cache/live_odds_sportspage.json", "w") as f:
                json.dump(data, f, indent=4)
            print(f"[SUCCESS] Fetched Sportspage market data for {len(data)} matchups.")
            return data
        else:
            print(f"[ERROR] Sportspage Failure: {response.status_code}")
            return []
    except Exception as e:
        print(f"[ERROR] Sportspage Connection Error: {str(e)}")
        return []

if __name__ == "__main__":
    fetch_sportspage_data()
