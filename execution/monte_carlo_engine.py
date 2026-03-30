import pandas as pd
import numpy as np
import os
import sys

# Ensure root directory is in path for imports
sys.path.append(os.getcwd())
from execution.injuries import InjuryManager

from execution.injuries import InjuryManager
from execution.nba_api_client import NBAClient

class MonteCarloEngine:
    """
    Probabilistic NBA Game Forecaster
    Uses Institutional Team Ratings (Off/Def/Pace) and Gaussian distributions
    to simulate 10,000+ game outcomes.
    """
    
    def __init__(self):
        self.client = NBAClient()
        self.team_stats_path = "history/2026_season/team_advanced_2026.csv"
        self.live_stats_path = ".tmp/cache/live_team_ratings_2026.csv"
        
        # Prefer live ratings from nba_api
        if os.path.exists(self.live_stats_path):
            self.team_df = pd.read_csv(self.live_stats_path)
            self.is_live = True
        else:
            self.team_df = pd.read_csv(self.team_stats_path) if os.path.exists(self.team_stats_path) else pd.DataFrame()
            self.is_live = False
            
        self.injury_manager = InjuryManager()
        self.std_dev = 11.5 # NBA League Average spread variance

    def sync_live_data(self):
        """Official Sync: Pull current ORtg/DRtg from NBA.com API"""
        print("[SYNC] Fetching live institutional ratings...")
        df = self.client.get_live_team_ratings()
        if not df.empty:
            self.team_df = df
            self.is_live = True
        return self.is_live

    def simulate_game(self, home_team_name: str, away_team_name: str, iterations=1000):
        """Runs Monte Carlo simulation for a single matchup"""
        
        # 1. Fetch Stats
        home_stats = self._get_team_stats(home_team_name)
        away_stats = self._get_team_stats(away_team_name)
        
        if home_stats.empty or away_stats.empty:
            return {"error": f"Stats not found for {home_team_name} or {away_team_name}"}

        # 2. Extract Base Metrics
        h_off = home_stats.get('ORtg', 115.0)
        h_def = home_stats.get('DRtg', 115.0)
        h_pace = home_stats.get('Pace', 99.0)
        
        a_off = away_stats.get('ORtg', 115.0)
        a_def = away_stats.get('DRtg', 115.0)
        a_pace = away_stats.get('Pace', 99.0)

        # 3. Injury Adjustments (The Usage Spike factor)
        h_factor = self.injury_manager.calculate_devaluation(home_team_name)
        a_factor = self.injury_manager.calculate_devaluation(away_team_name)
        h_off *= h_factor
        a_off *= a_factor

        # 4. Projected Points (Normalizing for Pace and Opponent Defense)
        # Goal: Find how many pts Team A scores against Team B's DefRTG
        # Heuristic: (My OffRTG + Opp DefRTG) / 2 = Expected Points per 100 poss
        avg_pace = (h_pace + a_pace) / 2.0
        
        h_exp_100 = (h_off + a_def) / 2.0 + 3.0 # Home Court Advantage (+3 pts)
        a_exp_100 = (a_off + h_def) / 2.0
        
        h_mean = (h_exp_100 * avg_pace) / 100.0
        a_mean = (a_exp_100 * avg_pace) / 100.0

        # 5. Iterative Simulation
        h_sims = np.random.normal(h_mean, self.std_dev, iterations)
        a_sims = np.random.normal(a_mean, self.std_dev, iterations)
        
        outcomes = h_sims - a_sims
        home_wins = np.sum(outcomes > 0)
        
        win_prob = (home_wins / iterations) * 100
        avg_margin = np.mean(outcomes)
        total_points = np.mean(h_sims + a_sims)
        
        # Confidence Intervals
        ci_lower = np.percentile(outcomes, 25)
        ci_upper = np.percentile(outcomes, 75)

        return {
            "home_win_prob": round(win_prob, 1),
            "away_win_prob": round(100 - win_prob, 1),
            "avg_margin": round(avg_margin, 1),
            "avg_total": round(total_points, 1),
            "home_pts": round((total_points + avg_margin) / 2, 1),
            "away_pts": round((total_points - avg_margin) / 2, 1),
            "ci": (round(ci_lower, 1), round(ci_upper, 1)),
            "iterations": iterations
        }

    def _get_team_stats(self, team_name: str):
        if self.team_df.empty:
            return pd.Series()
        
        # Standardize inputs
        target = team_name.replace("*", "").strip()
        
        # 1. Direct Mapping (Common discrepancies)
        TEAM_MAP = {
            "LA Clippers": "Los Angeles Clippers",
            "LAL": "Los Angeles Lakers",
            "OKC": "Oklahoma City Thunder",
            "SAS": "San Antonio Spurs",
            "NYK": "New York Knicks",
            "GSW": "Golden State Warriors",
            "PHO": "Phoenix Suns",
            "NOP": "New Orleans Pelicans",
            "DET": "Detroit Pistons",
            "BOS": "Boston Celtics"
        }
        target = TEAM_MAP.get(target, target)

        # 2. Cleanup dataframe names for matching
        # Remove asterisks and handle case
        clean_names = self.team_df['Team'].str.replace("*", "", regex=False).str.strip()
        
        # 3. Match attempt 1: Exact
        match = self.team_df[clean_names.str.lower() == target.lower()]
        
        # 4. Match attempt 2: Contained (e.g. 'Thunder' in 'Oklahoma City Thunder')
        if match.empty:
            nickname = target.split(" ")[-1] # Grab 'Pistons' from 'Detroit Pistons'
            match = self.team_df[clean_names.str.contains(nickname, case=False, na=False)]
            
        return match.iloc[0] if not match.empty else pd.Series()

if __name__ == "__main__":
    engine = MonteCarloEngine()
    # Test OKC vs SAS (The two titans of our 2026 data mod)
    result = engine.simulate_game("Thunder", "Spurs")
    print(f"[SIM] OKC vs SAS Results: {result}")
