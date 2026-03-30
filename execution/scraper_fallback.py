import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

class ESPNNBAScraper:
    """
    Fallback scraper for TRUE NBA 2025-2026 Standings and Scores.
    Use when official API is throttled or for quick verification.
    """
    
    def __init__(self):
        self.standings_url = "https://www.espn.com/nba/standings/_/season/2026"
        self.scoreboard_url = "https://www.espn.com/nba/scoreboard/_/date/20260329"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.cache_dir = ".tmp/cache"
        os.makedirs(self.cache_dir, exist_ok=True)

    def scrape_standings(self) -> pd.DataFrame:
        """Scrape current conference standings from ESPN"""
        print("[SCRAPE] Fetching TRUE 2025-26 Standings from ESPN...")
        try:
            # Use pandas read_html for quick extraction of tables
            tables = pd.read_html(self.standings_url)
            
            # ESPN's standings page has multiple tables (Team Names vs Stats)
            # Table 0: Eastern Conf Teams, Table 1: Eastern Conf Stats
            # Table 2: Western Conf Teams, Table 3: Western Conf Stats
            
            east_teams = tables[0]
            east_stats = tables[1]
            west_teams = tables[2]
            west_stats = tables[3]
            
            # Combine Teams and Stats
            east = pd.concat([east_teams, east_stats], axis=1)
            west = pd.concat([west_teams, west_stats], axis=1)
            
            east['Conference'] = 'Eastern'
            west['Conference'] = 'Western'
            
            standings = pd.concat([east, west], ignore_index=True)
            
            # Clean up column names (ESPN sometimes has 'W-L' as a single column)
            # Rename first column to 'Team'
            standings.columns.values[0] = "Team"
            
            standings.to_csv(f"{self.cache_dir}/standings_fallback.csv", index=False)
            return standings
            
        except Exception as e:
            print(f"[ERROR] Scraper failed: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    scraper = ESPNNBAScraper()
    df = scraper.scrape_standings()
    if not df.empty:
        print("\n[SUCCESS] Scraped TRUE Standings via Fallback:")
        print(df[['Team', 'W', 'L', 'PCT', 'Conference']].head(10).to_string(index=False))
