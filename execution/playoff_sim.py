import pandas as pd
import numpy as np
import os
import sys

# Ensure root directory is in path for imports
sys.path.append(os.getcwd())
from execution.monte_carlo_engine import MonteCarloEngine

class PlayoffSimulator:
    """
    Simulates a full NBA Playoff Bracket based on 2026 Standings.
    Runs 10,000 iterations to find the Most Likely Champion.
    """
    
    def __init__(self):
        self.engine = MonteCarloEngine()
        self.standings_path = "history/2026_season/standings_2026.csv"
        self.standings = pd.read_csv(self.standings_path) if os.path.exists(self.standings_path) else pd.DataFrame()

    def simulate_series(self, team1, team2, games=7):
        """Simulates a Best of X series"""
        t1_wins = 0
        t2_wins = 0
        needed = (games // 2) + 1
        
        for g in range(games):
            # Alternate home court (2-2-1-1-1 format)
            # Simplification: Higher seed is team1
            is_home = True if g in [0, 1, 4, 6] else False
            
            if is_home:
                res = self.engine.simulate_game(team1, team2, iterations=1)
            else:
                # Away game for team1
                res = self.engine.simulate_game(team2, team1, iterations=1)
            
            # Record winner
            # Note: res is a dict, we need the outcome of the 1 single iteration
            # Refactoring engine to support single item outcome better
            # For now, using prob as proxy for speed in high iterations
            pass
            
        # Optimization: Instead of 1-by-1, use the win_prob from engine directly to calculate series odds
        res = self.engine.simulate_game(team1, team2, iterations=5000)
        p = res['home_win_prob'] / 100.0
        
        # Binary distribution for Best of 7 (Binomial calculation)
        # Prob of winning 4 or more games in 7
        from scipy.stats import binom
        series_prob = 1 - binom.cdf(3, 7, p)
        return series_prob

    def run_full_bracket(self):
        """Simulate the entire 2026 bracket"""
        if self.standings.empty:
            return {"error": "Standings data missing"}
            
        # 1. Get Top 8 from East and West
        east = self.standings[self.standings['Conference'] == 'Eastern'].head(8)['Team'].tolist()
        west = self.standings[self.standings['Conference'] == 'Western'].head(8)['Team'].tolist()
        
        # 2. Simulate Rounds (recursive)
        east_champ = self._resolve_conference(east)
        west_champ = self._resolve_conference(west)
        
        # 3. Finals
        finals_prob = self.simulate_series(east_champ, west_champ)
        
        return {
            "east_champ": east_champ,
            "west_champ": west_champ,
            "finals_matchup": f"{east_champ} vs {west_champ}",
            "east_win_prob": round(finals_prob * 100, 1)
        }

    def _resolve_conference(self, teams):
        """Simplified bracket resolver (1v8, 4v5, 2v7, 3v6)"""
        # Round 1
        r1_w1 = self._winner(teams[0], teams[7])
        r1_w2 = self._winner(teams[3], teams[4])
        r1_w3 = self._winner(teams[1], teams[6])
        r1_w4 = self._winner(teams[2], teams[5])
        
        # Round 2
        r2_w1 = self._winner(r1_w1, r1_w2)
        r2_w2 = self._winner(r1_w3, r1_w4)
        
        # Conf Finals
        return self._winner(r2_w1, r2_w2)

    def _winner(self, t1, t2):
        prob = self.simulate_series(t1, t2)
        return t1 if prob > 0.5 else t2

if __name__ == "__main__":
    sim = PlayoffSimulator()
    print("[SIM] Running 2026 Playoff Bracket Simulation...")
    # Bracket requires scipy for binomial calc
    try:
        import scipy
        result = sim.run_full_bracket()
        print(f"[RESULT] Bracket prediction: {result}")
    except ImportError:
        print("[ERROR] scipy not found. Please install to run bracket.")
