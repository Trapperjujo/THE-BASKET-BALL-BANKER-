import pandas as pd
import requests
import os

class NBATeamScraper:
    """
    Scraper for Team-level Advanced Stats (OffRTG, DefRTG, Pace)
    Source: Basketball Reference
    """
    def __init__(self):
        self.url = "https://www.basketball-reference.com/leagues/NBA_2026.html"
        self.history_dir = "history/2026_season"
        os.makedirs(self.history_dir, exist_ok=True)

    def fetch_team_advanced(self):
        print(f"[SCRAPE] Fetching 2025-26 Team Advanced Stats from Basketball Reference...")
        try:
            # Table id for Advanced Team Stats is usually 'advanced-team'
            # read_html is the most reliable way for BBRef
            tables = pd.read_html(self.url, attrs={'id': 'advanced-team'})
            df = tables[0]
            
            # Clean up multi-index columns if they exist
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(0)
            
            # Save the Deliverable
            path = f"{self.history_dir}/team_advanced_2026.csv"
            df.to_csv(path, index=False)
            print(f"[SUCCESS] Saved Team Stats to {path}")
            return df
        except Exception as e:
            print(f"[ERROR] Team Scraper failed: {e}")
            # Try a broader fetch if ID fails
            try:
                tables = pd.read_html(self.url)
                # Look for a table with 'OffRtg'
                for t in tables:
                    if 'OffRtg' in t.columns or ('Advanced', 'OffRtg') in t.columns:
                        t.to_csv(f"{self.history_dir}/team_advanced_2026.csv", index=False)
                        return t
                return pd.DataFrame()
            except:
                return pd.DataFrame()

if __name__ == "__main__":
    scraper = NBATeamScraper()
    df = scraper.fetch_team_advanced()
    if not df.empty:
        print("\n[PREVIEW] Top 5 Teams by Net Rating:")
        # Find the Net Rating column (might be 'NRtg' or similar)
        nrtg_col = [c for c in df.columns if 'NRtg' in str(c)][0]
        team_col = [c for c in df.columns if 'Team' in str(c)][0]
        print(df[[team_col, nrtg_col]].sort_values(by=nrtg_col, ascending=False).head(5).to_string(index=False))
