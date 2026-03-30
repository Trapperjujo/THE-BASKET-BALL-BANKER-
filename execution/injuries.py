import pandas as pd
import json
import os

class InjuryManager:
    """
    Handles player status and calculates Team OffRTG/DefRTG adjustments.
    Uses PER and USG% to determine the depth of devaluation.
    """
    
    def __init__(self, stats_path="history/2026_season/player_advanced_2026.csv"):
        self.stats_path = stats_path
        self.players_df = pd.read_csv(stats_path) if os.path.exists(stats_path) else pd.DataFrame()
        self.active_injuries = {} # { "Team": ["Player Name", ...] }

    def set_injuries(self, team: str, players: list):
        """Set the list of missing players for a team"""
        self.active_injuries[team] = players

    def calculate_devaluation(self, team: str) -> float:
        """
        Returns a multiplier for the team's Offensive Rating.
        Logic: Reduce OffRTG based on missing PER density.
        """
        if team not in self.active_injuries or self.players_df.empty:
            return 1.0
            
        missing_players = self.active_injuries[team]
        total_devaluation = 0.0
        
        for player in missing_players:
            # Match player in advanced stats
            p_data = self.players_df[self.players_df['Player'].str.contains(player, case=False, na=False)]
            if not p_data.empty:
                per = p_data.iloc[0].get('PER', 15.0)
                usg = p_data.iloc[0].get('USG%', 20.0)
                ts = p_data.iloc[0].get('TS%', 0.58) # League avg
                
                # Impact Formula: (PER / 35) * (USG / 30) * (TS / 0.58) * 15% 
                # High TS% players leaving creates more efficiency loss.
                impact = (per / 35.0) * (usg / 30.0) * (ts / 0.58) * 0.15
                total_devaluation += impact
        
        # Cap devaluation at 35% for extreme injury bugs
        return max(0.65, 1.0 - total_devaluation)

    def get_available_players(self, team_code: str) -> list:
        """Get list of players for a specific team for UI selection"""
        if self.players_df.empty:
            return []
        team_players = self.players_df[self.players_df['Tm'] == team_code]['Player'].tolist()
        return sorted(team_players)

if __name__ == "__main__":
    # Internal test
    manager = InjuryManager()
    # Test for Lakers if Luka is out
    manager.set_injuries("LAL", ["Luka Dončić"])
    reduction = manager.calculate_devaluation("LAL")
    print(f"[TEST] LAL OffRTG Multiplier if Luka is out: {reduction:.2f}")
