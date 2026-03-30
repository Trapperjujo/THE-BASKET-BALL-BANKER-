import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_apisports_odds():
    """Fallback fetcher for THE-BASKET-BALL-BANKER- using API-Sports (RapidAPI)"""
    api_key = os.getenv("API_SPORTS_KEY")
    if not api_key:
        print("[ERROR] No API_SPORTS_KEY found in .env")
        return []
    
    # API-Sports NBA Odds endpoint (2025-2026 season)
    url = "https://v1.basketball.api-sports.io/odds"
    params = {
        "league": "12", # NBA
        "season": "2025-2026"
    }
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "v1.basketball.api-sports.io"
    }
    
    print("[ODDS-ALT] Fetching secondary market data from API-Sports...")
    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            data = response.json().get('response', [])
            os.makedirs(".tmp/cache", exist_ok=True)
            # Standardize output for the Monte Carlo engine
            standard_odds = []
            for item in data:
                # Basic normalization logic for our engine
                standard_odds.append(item)
                
            with open(".tmp/cache/live_odds_alt.json", "w") as f:
                json.dump(standard_odds, f, indent=4)
            print(f"[SUCCESS] Fetched fallback odds for {len(standard_odds)} matchups.")
            return standard_odds
        else:
            print(f"[ERROR] API-Sports Failure: {response.status_code}")
            return []
    except Exception as e:
        print(f"[ERROR] Connectivity Error: {str(e)}")
        return []

if __name__ == "__main__":
    fetch_apisports_odds()
