import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

class RotowireScraper:
    """
    Automated NBA Injury & Lineup Scaper.
    Source: Rotowire (Institutional standard for real-time status).
    """
    
    def __init__(self):
        self.url = "https://www.rotowire.com/basketball/nba-lineups.php"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def scrape_injuries(self) -> dict:
        """
        Scrapes the lineups page for 'OUT' and 'GTD' players.
        Returns a dict: { 'TeamAbbr': [list of players] }
        """
        print("[SCRAPE] Fetching Live Injury Data from Rotowire...")
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find all game lineup boxes
            lineup_boxes = soup.find_all(class_='lineup')
            results = {}

            for box in lineup_boxes:
                # Get Team names (Home/Away)
                teams = box.find_all(class_='lineup__abbr')
                if len(teams) < 2: continue
                
                away_team = teams[0].get_text(strip=True)
                home_team = teams[1].get_text(strip=True)
                
                results[away_team] = []
                results[home_team] = []
                
                # Find all players with "OUT" or "GTD" status
                # These are usually in separate lists within the box
                injuries = box.find_all(class_='lineup__list--injuries')
                
                # Away is usually index 0, Home index 1
                if len(injuries) >= 2:
                    # Away Injuries
                    for p in injuries[0].find_all(class_='lineup__player'):
                        name = p.find(class_='lineup__player-name-full').get_text(strip=True)
                        results[away_team].append(name)
                    
                    # Home Injuries
                    for p in injuries[1].find_all(class_='lineup__player'):
                        name = p.find(class_='lineup__player-name-full').get_text(strip=True)
                        results[home_team].append(name)

            print(f"[SUCCESS] Scraped injuries for {len(results)} teams.")
            return results

        except Exception as e:
            print(f"[ERROR] Rotowire Scraper failed: {e}")
            return {}

if __name__ == "__main__":
    scraper = RotowireScraper()
    active_injuries = scraper.scrape_injuries()
    for team, players in active_injuries.items():
        if players:
            print(f"{team}: {players}")
