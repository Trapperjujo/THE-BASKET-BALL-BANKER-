# Data Fetching Strategy: TRUE NBA 2025-2026

## Objective
To provide high-fidelity, real-time statistical data for the 2025-2026 NBA season, ensuring all advanced metrics (EPM, PER, TS%) are calculated from "True" source data.

## Primary Sources

### 1. `nba_api` (Python Library)
- **Role**: Fetching official league stats from `stats.nba.com`.
- **Endpoints**: `Leaguedashplayerstats`, `LeagueStandings`, `BoxScoreAdvancedV3`.
- **Reliability**: Subject to rate limits. Implementation must use `time.sleep` and random user-agents.

### 2. The Odds API
- **Role**: Real-time market data (Spreads, Over/Unders, Moneylines) for +EV calculations.
- **Accuracy**: Aggregates from 30+ sportsbooks (DraftKings, FanDuel, etc.).

### 3. `balldontlie.io` (Backup)
- **Role**: Rapid fetching of game results and basic scores if `nba_api` is throttled.

## Data Normalization
- All player data is normalized to **Per 36 Minutes** to align with the Betting Strategy directive.
- **True Shooting % (TS%)** is calculated as: `PTS / (2 * (FGA + 0.44 * FTA))`.
- **Usage Rate (USG%)** estimation: `100 * ((FGA + 0.44 * FTA + TOV) * (Tm Min / 5)) / (MP * (Tm FGA + 0.44 * Tm FTA + Tm TOV))`.

## Caching Strategy
- To avoid API bans, all fetched data is stored in `.tmp/cache/` for 1 hour.
- Standing data is cached for 6 hours.
- Prediction logs are permanent.

## 2025-2026 Season Specifics
- Season ID: `22025` (Standard NBA format).
- Focus on post-All-Star Break trends (if applicable based on current date).
