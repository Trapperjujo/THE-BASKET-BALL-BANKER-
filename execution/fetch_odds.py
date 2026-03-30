import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_nba_odds():
    """Real fetcher for THE-BASKET-BALL-BANKER- using The Odds API"""
    api_key = os.getenv("THE_ODDS_API_KEY")
    if not api_key:
        print("[ERROR] No THE_ODDS_API_KEY found in .env")
        return []
    
    url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds/?apiKey={api_key}&regions=us&markets=h2h,spreads&oddsFormat=decimal"
    
    print("[ODDS] Fetching live NBA market data...")
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        os.makedirs(".tmp/cache", exist_ok=True)
        with open(".tmp/cache/live_odds.json", "w") as f:
            json.dump(data, f, indent=4)
        print(f"[SUCCESS] Fetched odds for {len(data)} upcoming games.")
        return data
    else:
        print(f"[ERROR] Failed to fetch odds: {response.status_code} - {response.text}")
        return []

if __name__ == "__main__":
    fetch_nba_odds()
