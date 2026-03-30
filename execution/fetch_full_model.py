from execution.nba_api_client import NBAClient
import os
import json
import pandas as pd

def initialize_2026_model():
    """Execute the full data model fetch for training"""
    client = NBAClient()
    
    print("\n[INIT] BUILDING FULL 2025-2026 NBA DATA MODEL\n")
    
    # 1. Fetch High-Dimensional Data
    model_data = client.get_2026_full_data_model()
    
    # 2. Extract Key Features for Prediction
    if not model_data["players"].empty and not model_data["teams"].empty:
        # Create a combined 'Training State' JSON
        # For this demo, we'll just summarize the state
        stats_summary = {
            "total_players": len(model_data["players"]),
            "total_teams": len(model_data["teams"]),
            "top_per_leader": model_data["players"].sort_values(by='PER', ascending=False).iloc[0]['PLAYER_NAME'] if 'PER' in model_data["players"] else "N/A",
            "top_netrtg_team": model_data["teams"].sort_values(by='NET_RATING', ascending=False).iloc[0]['TEAM_NAME'] if 'NET_RATING' in model_data["teams"] else "N/A",
            "timestamp": "2026-03-29"
        }
        
        history_path = ".tmp/history"
        os.makedirs(history_path, exist_ok=True)
        with open(f"{history_path}/full_data_model_2026.json", "w") as f:
            json.dump(stats_summary, f, indent=4)
            
        print(f"\n[SUCCESS] Model training snapshot completed.")
        print(f"📊 Stats Overview: {stats_summary['total_players']} players and {stats_summary['total_teams']} teams analyzed.")
        return stats_summary
    else:
        print("\n[ERROR] Model data fetch failed. Check API status.")
        return {}

if __name__ == "__main__":
    initialize_2026_model()
