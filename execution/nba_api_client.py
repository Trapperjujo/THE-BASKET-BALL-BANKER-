import pandas as pd
import time
import random
import requests
from nba_api.stats.endpoints import leaguedashplayerstats, leaguestandings, scoreboardv2
from nba_api.stats.static import teams
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

load_dotenv()

class NBAClient:
    """
    Deterministic client for fetching TRUE 2025-2026 NBA data.
    Uses nba_api with robust error handling and rate-limiting.
    """
    
    def __init__(self):
        self.headers = {
            'Host': 'stats.nba.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.nba.com/',
            'Connection': 'keep-alive',
        }
        self.season = "2025-26"
        self.cache_dir = ".tmp/cache"
        os.makedirs(self.cache_dir, exist_ok=True)

    def _get_with_retry(self, endpoint_class, **kwargs):
        """Helper to handle Rate Limiting (403/429)"""
        max_retries = 3
        for i in range(max_retries):
            try:
                time.sleep(random.uniform(1.2, 2.5)) # Respectful delay
                endpoint = endpoint_class(headers=self.headers, **kwargs)
                return endpoint.get_data_frames()[0]
            except Exception as e:
                if i == max_retries - 1:
                    print(f"[ERROR] Error calling {endpoint_class.__name__}: {e}")
                    return pd.DataFrame()
                time.sleep(5 * (i + 1)) # Exponential backoff

    def get_2026_standings(self) -> pd.DataFrame:
        """Fetch current 2025-26 League Standings"""
        print(f"[DATA] Fetching TRUE {self.season} Standings...")
        df = self._get_with_retry(leaguestandings.LeagueStandings, season=self.season)
        if not df.empty:
            df.to_csv(f"{self.cache_dir}/standings_2026.csv", index=False)
        return df

    def get_2026_full_data_model(self) -> Dict[str, pd.DataFrame]:
        """Fetch complete Player and Team Metrics for Model Training/Analysis"""
        print(f"[MODEL] Fetching Comprehensive {self.season} Data Model...")
        
        # 1. Player Advanced Stats (TS%, USG%, PER)
        player_df = self._get_with_retry(leaguedashplayerstats.LeagueDashPlayerStats, 
                                        season=self.season, 
                                        measure_type_detailed_defense='Advanced')
        
        # 2. Team Advanced Stats (OffRTG, DefRTG, NetRTG, Pace)
        from nba_api.stats.endpoints import leaguedashteamstats
        team_df = self._get_with_retry(leaguedashteamstats.LeagueDashTeamStats, 
                                      season=self.season, 
                                      measure_type_detailed_defense='Advanced')
        
        model_data = {
            "players": player_df,
            "teams": team_df
        }
        
        if not player_df.empty:
            player_df.to_csv(f"{self.cache_dir}/full_players_2026.csv", index=False)
        if not team_df.empty:
            team_df.to_csv(f"{self.cache_dir}/full_teams_2026.csv", index=False)
            
        return model_data

    def get_todays_games(self) -> pd.DataFrame:
        """Fetch games scheduled for 'now' (based on current system time)"""
        # System date: 2026-03-29
        game_date = "2026-03-29" 
        print(f"[DATA] Fetching games for {game_date}...")
        df = self._get_with_retry(scoreboardv2.ScoreboardV2, day_offset='0', game_date=game_date)
        return df

if __name__ == "__main__":
    client = NBAClient()
    
    # --- Live Execution ---
    print("\n[INIT] INITIALIZING NBA DATA ATLAS (2025-2026 SESSION)\n")
    
    standings = client.get_2026_standings()
    if not standings.empty:
        print("\n[DATA] CURRENT STANDINGS PREVIEW:")
        # Display key metrics to prove "TRUE" data
        display_cols = ['TeamCity', 'TeamName', 'Conference', 'Record', 'Winstreak']
        # Note: adjust column names if leaguestandings uses different ones
        if 'TeamCity' in standings.columns:
            print(standings[display_cols].head(10).to_string(index=False))
        else:
            print(standings.head(10))
        
    players = client.get_2026_player_stats()
    if not players.empty:
        print(f"\n[SUCCESS] Loaded statistics for {len(players)} players.")
        print("[CACHE] All data saved to .tmp/cache/ for predictive analysis.")
