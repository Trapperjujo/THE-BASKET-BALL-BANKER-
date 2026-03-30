import requests
import pandas as pd
import os
from bs4 import BeautifulSoup

class NBAAdvancedScraper:
    """
    Scraper for Basketball Reference "Advanced Stats" (2025-26).
    Source: PER, TS%, USG%, BPM, VORP, etc.
    """
    
    def __init__(self):
        self.season = 2026
        self.url = f"https://www.basketball-reference.com/leagues/NBA_{self.season}_advanced.html"
        self.cache_dir = ".tmp/cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_advanced_stats(self) -> pd.DataFrame:
        """Exhaustively scrape the Advanced stats table for model training."""
        print(f"[SCRAPE] Fetching TRUE {self.season} Advanced Stats from Basketball Reference...")
        try:
            # Use pandas read_html directly on the URL (simple and effective)
            tables = pd.read_html(self.url, header=0)
            df = tables[0]
            
            # Clean up the table (Basketball Reference repeats headers every 20 rows)
            df = df[df['Player'] != 'Player']
            
            # Convert columns to numeric where possible
            cols_to_convert = ['Age', 'G', 'MP', 'PER', 'TS%', '3PAr', 'FTr', 'ORB%', 'DRB%', 'TRB%', 'AST%', 'STL%', 'BLK%', 'TOV%', 'USG%', 'OWS', 'DWS', 'WS', 'WS/48', 'OBPM', 'DBPM', 'BPM', 'VORP']
            for col in cols_to_convert:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Handle the 'Player' names (strip suffixes like '*')
            df['Player'] = df['Player'].str.replace('*', '', regex=False)
            
            # Save to permanent history for the "Brain" to use
            history_path = ".tmp/history"
            os.makedirs(history_path, exist_ok=True)
            df.to_csv(f"{history_path}/advanced_stats_{self.season}.csv", index=False)
            
            print(f"[SUCCESS] Scraped {len(df)} players for the 2026 model.")
            return df
            
        except Exception as e:
            print(f"[ERROR] Advanced Scraper failed: {e}")
            return pd.DataFrame()

if __name__ == "__main__":
    scraper = NBAAdvancedScraper()
    df = scraper.fetch_advanced_stats()
    if not df.empty:
        print("\n[PREVIEW] Top 5 PER Leaders (2025-2026):")
        print(df[['Player', 'Tm', 'PER', 'USG%', 'TS%', 'BPM']].sort_values(by='PER', ascending=False).head(10).to_string(index=False))
