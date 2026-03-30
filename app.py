import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import json
from execution.compute_nba_alpha import NBAAlphaEngine
from execution.monte_carlo_engine import MonteCarloEngine
from execution.playoff_sim import PlayoffSimulator
from execution.financial_analysis import FinancialDecisionModel

# --- APP CONFIGURATION ---
st.set_page_config(
    page_title="THE-BASKET-BALL-BANKER- 🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INJURY STATE ---
if 'out_players' not in st.session_state:
    st.session_state.out_players = {} # {Team: [List]}

# --- GLASSMORPHIC STYLING ---
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* Global Glass Panel */
    div.element-container:has(div.glass-card) {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
        margin: 10px 0;
    }
    
    /* Specific Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.8) !important;
        backdrop-filter: blur(8px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    /* Typography & Headers */
    h1, h2, h3 {
        color: #f58426 !important; /* NBA Orange */
        font-family: 'Outfit', sans-serif;
    }
    
    .metric-label {
        color: #94a3b8;
        font-size: 0.85rem;
    }

    .verdict-tag {
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    
    /* Metric Description Card */
    .metric-card {
        background: rgba(255, 255, 255, 0.04);
        border-radius: 12px;
        padding: 15px;
        border-left: 3px solid #f58426; /* NBA Orange */
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        background: rgba(255, 255, 255, 0.06);
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR & AUTH ---
with st.sidebar:
    st.title("THE BANKER 🤖")
    st.write("Institutional NBA Analytics")
    
    api_key = st.text_input(
        "The Odds API Key", 
        type="password", 
        placeholder="Enter your key...",
        help="For the most accurate, real-time NBA predictions, we recommend signing up for a free tier at [The Odds API](https://the-odds-api.com/) and entering your key here for live market data."
    )
    st.divider()
    
    bankroll = st.number_input("Total Bankroll (CAD)", value=1000.0, step=100.0)
    kelly_val = st.select_slider(
        "Risk Profile (Kelly Selection)",
        options=[0.25, 0.50, 1.00],
        value=0.25,
        help="Institutional betting strategy: 0.25 = Conservative (Quarter Kelly) | 0.50 = Balanced (Half) | 1.00 = Strategic (Full Kelly)"
    )
    
    st.divider()
    with st.expander("🏥 SIMULATE INJURY REPORT"):
        st.write("Mark players as **OUT** to adjust team ratings.")
        
        # Pull dynamic team list from data if available
        path = "history/2026_season/player_advanced_2026.csv"
        if os.path.exists(path):
            df_p = pd.read_csv(path)
            all_teams = sorted([str(t) for t in df_p['Team'].unique() if pd.notna(t) and t not in ['2TM', '3TM']])
            team_to_report = st.selectbox("Select Team", all_teams)
            
            # Load player list for this team
            team_players = sorted(df_p[df_p['Team'] == team_to_report]['Player'].tolist())
            selected_out = st.multiselect("Active Injuries", team_players, key=f"inj_{team_to_report}")
            st.session_state.out_players[team_to_report] = selected_out
            
            if st.button("🗑️ Clear All Injuries"):
                st.session_state.out_players = {}
                st.rerun()
        else:
            st.warning("Player data missing for reporter.")

    # --- ACTIVE INJURY SUMMARY ---
    total_out = sum(len(v) for v in st.session_state.out_players.values() if v)
    if total_out > 0:
        st.sidebar.markdown("---")
        st.sidebar.subheader("🏥 CURRENTLY OUT (SIM)")
        for team, players in st.session_state.out_players.items():
            if players:
                st.sidebar.write(f"**{team}**: {', '.join(players)}")
    
    st.divider()
    if st.button("🔄 REFRESH MODEL (LIVE)"):
        with st.spinner("Syncing Official NBA.com Data & Injuries..."):
            from execution.monte_carlo_engine import MonteCarloEngine
            from execution.scraper_rotowire import RotowireScraper
            from execution.fetch_odds import fetch_nba_odds
            from execution.nba_api_client import NBAClient
            
            # 1. Official Ratings Sync
            engine = MonteCarloEngine()
            engine.sync_live_data()
            
            # 2. Automated Injuries (Rotowire)
            rw = RotowireScraper()
            auto_injuries = rw.scrape_injuries()
            for team, players in auto_injuries.items():
                if players:
                    # Update session state with scraped injuries
                    st.session_state.out_players[team] = players
            
            # 3. Live Odds
            fetch_nba_odds()
            
            # 4. Daily Scoreboard
            client = NBAClient()
            client.get_todays_games()
            
            st.cache_data.clear()
            st.success("Universal Sync Complete. Data Source: Official NBA.com API")
            st.rerun()

# --- DATA LAYER ---
@st.cache_data
def load_standings():
    try:
        standings_path = "history/2026_season/standings_2026.csv"
        advanced_path = "history/2026_season/team_advanced_2026.csv"
        
        if os.path.exists(standings_path):
            df_standings = pd.read_csv(standings_path)
            
            if os.path.exists(advanced_path):
                df_adv = pd.read_csv(advanced_path)
                # Strip '*' from team names in advanced stats for clean mapping
                df_adv['Team'] = df_adv['Team'].str.replace('*', '', regex=False)
                # Merge Net Rating into standings
                if 'NRtg' in df_adv.columns:
                    df_standings = pd.merge(df_standings, df_adv[['Team', 'NRtg']], on='Team', how='left')
                else:
                    # Fallback if column names differ
                    nrtg_col = [c for c in df_adv.columns if 'NRtg' in str(c)]
                    if nrtg_col:
                        df_standings = pd.merge(df_standings, df_adv[['Team', nrtg_col[0]]], on='Team', how='left')
                        df_standings = df_standings.rename(columns={nrtg_col[0]: 'NRtg'})
                    else:
                        df_standings['NRtg'] = 0.0 # Emergency fallback
            return df_standings
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading standings: {e}")
        return pd.DataFrame()

@st.cache_data
def load_predictions(bankroll_val, current_injuries, kelly_val):
    from execution.monte_carlo_engine import MonteCarloEngine
    from execution.financial_analysis import FinancialDecisionModel
    import json
    
    mc_engine = MonteCarloEngine()
    
    # 1. Try to load today's scoreboard (Official NBA.com)
    sb_path = ".tmp/cache/todays_scoreboard_2026.csv"
    matchups = []
    if os.path.exists(sb_path):
        try:
            df_sb = pd.read_csv(sb_path)
            # Fetch games for today. Note: Column names in ScoreboardV2 can vary.
            # We look for GAME_ID and TEAM nicknames.
            if 'HOME_TEAM_NAME' in df_sb.columns:
                 for _, row in df_sb.iterrows():
                    matchups.append({"home": row['HOME_TEAM_NAME'], "away": row['VISITOR_TEAM_NAME']})
            else:
                # Fallback to team IDs if names aren't in the CSV
                matchups = [
                    {"home": "Celtics", "away": "Pistons"},
                    {"home": "Thunder", "away": "Spurs"},
                    {"home": "Knicks", "away": "Cavaliers"}
                ]
        except:
             matchups = [{"home": "Celtics", "away": "Pistons"}, {"home": "Thunder", "away": "Spurs"}]
    else:
        matchups = [
            {"home": "Celtics", "away": "Pistons"},
            {"home": "Thunder", "away": "Spurs"},
            {"home": "Knicks", "away": "Cavaliers"}
        ]
    
    fin_model = FinancialDecisionModel(bankroll=bankroll_val, kelly_fraction=kelly_val)
    
    # Apply session injuries to manager
    for team, p_list in current_injuries.items():
        mc_engine.injury_manager.set_injuries(team, p_list)

        # 1. Projected Scores
        h_score = round(sim['home_pts'])
        a_score = round(sim['away_pts'])
        
        # 2. Identify Player Props (Top Scorer/Assists)
        # We use USG% for scorers and AST% for facilitators
        path_p = "history/2026_season/player_advanced_2026.csv"
        home_scorer, home_passer = "TBD", "TBD"
        away_scorer, away_passer = "TBD", "TBD"
        
        if os.path.exists(path_p):
            df_p = pd.read_csv(path_p)
            
            def get_leaders(team_name):
                # Simple nickname matching for roster lookup
                nick = team_name.split()[-1]
                roster = df_p[df_p['Team'].str.contains(nick, na=False, case=False)]
                
                # Filter out simulated injuries (Accuracy Priority #1)
                team_out = current_injuries.get(team_name, [])
                roster = roster[~roster['Player'].isin(team_out)]
                
                if roster.empty: return "TBD", "TBD"
                
                top_s = roster.sort_values(by='USG%', ascending=False).iloc[0]['Player']
                top_a = roster.sort_values(by='AST%', ascending=False).iloc[0]['Player']
                return top_s, top_a

            home_scorer, home_passer = get_leaders(m['home'])
            away_scorer, away_passer = get_leaders(m['away'])
            
        prob_val = sim['home_win_prob'] / 100.0 if sim['home_win_prob'] > 50 else sim['away_win_prob'] / 100.0
        winner_name = m['home'] if sim['home_win_prob'] > 50 else m['away']
        
        # Calculate EV (Expected Value)
        # EV = (Prob * Odds) - 1.0
        # If Odds are Decimal: EV = (Prob * (Odds-1)) - ((1-Prob) * 1)
        ev_val = (prob_val * (odds_val - 1.0)) - ((1.0 - prob_val) * 1.0)
        
        preds.append({
            "home": m['home'],
            "away": m['away'],
            "winner": winner_name,
            "home_score": h_score,
            "away_score": a_score,
            "home_scorer": home_scorer,
            "home_passer": home_passer,
            "away_scorer": away_scorer,
            "away_passer": away_passer,
            "prob": prob_val * 100,
            "mc_prob": prob_val * 100,
            "odds": odds_val,
            "ev": ev_val,
            "margin": sim['avg_margin'],
            "total": sim['avg_total'],
            "risk": risk_score,
            "kelly_stake": stake_info / bankroll_val,
            "suggested_bet": stake_info
        })
    
    return preds

# --- DASHBOARD MAIN ---
st.title("🏀 NBA ALPHA COMMAND CENTER")
st.subheader("TRUE 2025-26 Season Insights")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["AI Predictions 🎯", "Playoff Sim 🏆", "Standings 📈", "Research ⚡", "PRO-METRIC GUIDE 📖"])

with tab1:
    st.write("### Institutional Prediction Feed")
    
    with st.expander("📖 Dashboard Legend"):
        st.write("For in-depth metric strategies, visit the **PRO-METRIC GUIDE** tab.")
        
    preds = load_predictions(bankroll, st.session_state.out_players, kelly_val)
    
    if preds:
        for p in preds:
            with st.container():
                # Conditional styling based on verdict
                verdict_color = "#22c55e" if "LOCK" in p['verdict'] else "#eab308" if "VALUE" in p['verdict'] else "#94a3b8"
                
                # Conditional styling based on EV
                ev_color = "#22c55e" if p['ev'] > 0.05 else "#94a3b8"
                ev_tag = f"<span style='background: {ev_color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold;'>+EV ALPHA: {p['ev']*100:.1f}%</span>" if p['ev'] > 0 else ""

                st.markdown(f"""
                <div class="prediction-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span class="verdict-tag" style="background: #a855f7; color: white;">PRO-MODEL: {int(p['prob'])}% CONFIDENCE</span>
                        {ev_tag}
                    </div>
                    
                    <h2 style='margin: 10px 0; font-size: 1.4rem;'>{p['away']} @ {p['home']}</h2>
                    
                    <div style="background: rgba(34, 211, 238, 0.1); padding: 15px; border-radius: 12px; margin: 15px 0; border: 1px solid rgba(34, 211, 238, 0.2);">
                        <p style='margin:0; font-size: 0.85rem; color: #22d3ee; text-transform: uppercase; letter-spacing: 1px;'>🎯 PROJECTED FINAL</p>
                        <h1 style='margin:5px 0; font-size: 2.2rem; display: flex; justify-content: space-between;'>
                            <span>{p['home']} {int(p['home_score'])}</span>
                            <span style='color: #94a3b8; font-size: 1.2rem; align-self: center;'>-</span>
                            <span>{int(p['away_score'])} {p['away']}</span>
                        </h1>
                    </div>

                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                        <div>
                            <p class='metric-label'>Monte Carlo Prob</p>
                            <p style='color: #a855f7; font-weight: bold; font-size: 1.3rem;'>{int(p['mc_prob'])}%</p>
                        </div>
                        <div>
                            <p class='metric-label'>Risk Score</p>
                            <p style='color: #f87171; font-weight: bold; font-size: 1.3rem;'>{p['risk']}</p>
                        </div>
                    </div>

                    <div style='background: rgba(245, 132, 38, 0.05); padding: 15px; border-radius: 12px; border-left: 4px solid #f58426;'>
                        <p style='margin:0; font-size: 0.8rem; color: #f58426; font-weight: bold;'>💎 PRO-REPORT: ALPHA PROP WATCH</p>
                        <hr style='border:0; border-top: 1px solid rgba(245, 132, 38, 0.2); margin: 8px 0;'>
                        <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px;'>
                            <div>
                                <p style='margin:0; font-size: 0.7rem; color: #94a3b8;'>HOME STAT LEADERS</p>
                                <p style='margin:0; font-size: 0.85rem;'>🔥 {p['home_scorer']} (USG%)</p>
                                <p style='margin:0; font-size: 0.85rem;'>🕹️ {p['home_passer']} (AST%)</p>
                            </div>
                            <div>
                                <p style='margin:0; font-size: 0.7rem; color: #94a3b8;'>AWAY STAT LEADERS</p>
                                <p style='margin:0; font-size: 0.85rem;'>🔥 {p['away_scorer']} (USG%)</p>
                                <p style='margin:0; font-size: 0.85rem;'>🕹️ {p['away_passer']} (AST%)</p>
                            </div>
                        </div>
                    </div>

                    <div style="margin-top: 20px; padding: 15px; background: rgba(34, 211, 238, 0.05); border-radius: 12px; border: 1px solid rgba(34, 211, 238, 0.1);">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span style='color: #94a3b8; font-size: 0.8rem;'>SUGGESTED WAGER</span>
                            <span style='color: white; font-weight: bold;'>${p['suggested_bet']:.2f}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                            <span style='color: #94a3b8; font-size: 0.8rem;'>PREDICTED PROFIT</span>
                            <span style='color: #22c55e; font-weight: bold;'>+${(p['suggested_bet'] * (p['odds'] - 1)):.2f}</span>
                        </div>
                        <hr style='border:0; border-top: 1px solid rgba(255,255,255,0.05); margin: 8px 0;'>
                        <div style="display: flex; justify-content: space-between;">
                            <span style='color: #22d3ee; font-weight: bold; font-size: 0.9rem;'>TOTAL RETURN</span>
                            <span style='color: #22d3ee; font-weight: bold; font-size: 1.1rem;'>${(p['suggested_bet'] * p['odds']):.2f}</span>
                        </div>
                    </div>

                    <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.05); display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <p class='metric-label'>Market Price (H2H)</p>
                            <p style='margin:0; font-size: 1.2rem; font-weight: bold;'>{p['odds']}</p>
                        </div>
                        <div style='text-align: right;'>
                            <p class='metric-label'>SMART STAKE (KELLY)</p>
                            <span class="verdict-tag" style="background: #22c55e; color: white;">RUN SIMULATION ✅</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("No live predictions. Model requires active matchups.")

with tab2:
    st.write("### 🏆 2026 Playoff Bracket Forecast")
    if st.button("🚀 Run 10,000 Iteration Simulation"):
        with st.spinner("Simulating full series brackets..."):
            sim = PlayoffSimulator()
            result = sim.run_full_bracket()
            
            st.success("Simulation Complete.")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("East Representative", result['east_champ'])
                st.metric("West Representative", result['west_champ'])
            with col2:
                st.write("**Finals Matchup**")
                st.title(result['finals_matchup'])
                st.write(f"The model gives the **{result['east_champ']}** a **{result['east_win_prob']}%** chance of winning the title.")

with tab3:
    st.write("### Conference Standings (TRUE 2025-26)")
    df_standings = load_standings()
    
    if not df_standings.empty:
        east_df = df_standings[df_standings['Conference'] == 'Eastern'].sort_values(by='W', ascending=False)
        west_df = df_standings[df_standings['Conference'] == 'Western'].sort_values(by='W', ascending=False)
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**EASTERN CONFERENCE**")
            st.dataframe(east_df[['Team', 'W', 'L', 'NRtg']].reset_index(drop=True), use_container_width=True)
        with col2:
            st.write("**WESTERN CONFERENCE**")
            st.dataframe(west_df[['Team', 'W', 'L', 'NRtg']].reset_index(drop=True), use_container_width=True)
    else:
        st.error("Standings data not found.")

with tab4:
    st.write("### ⚡ Player Analytics Leaderboard")
    path = "history/2026_season/player_advanced_2026.csv"
    if os.path.exists(path):
        df_players = pd.read_csv(path)
        st.dataframe(df_players[['Player', 'Team', 'PER', 'TS%', 'USG%', 'BPM', 'VORP']].sort_values(by='PER', ascending=False).head(50), use_container_width=True)
    else:
        st.warning("Stats file missing. Run scraper.")

with tab5:
    st.write("### 📖 PRO-METRIC STRATEGY GUIDE")
    st.write("Master the institutional metrics used to identify alpha in the player market.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h4 style='color: #f58426; margin:0;'>🎯 PER (Efficiency)</h4>
            <p style='font-size: 0.8rem; color: #94a3b8; margin: 5px 0;'><b>Tier:</b> 15.0 Avg | 20.0 All-Star | 25.0 MVP</p>
            <p style='font-size: 0.9rem;'>Holistic per-minute production. Perfect for identifying under-utilized bench stars who deserve more minutes.</p>
        </div>
        <div class="metric-card">
            <h4 style='color: #22d3ee; margin:0;'>🔥 TS% (True Shooting)</h4>
            <p style='font-size: 0.8rem; color: #94a3b8; margin: 5px 0;'><b>Tier:</b> 0.62+ Elite | 0.58 Good | < 0.54 Poor</p>
            <p style='font-size: 0.9rem;'>The ultimate measure of scoring efficiency—factors in 2PT, 3PT, and FT volume into one number.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h4 style='color: #a855f7; margin:0;'>🕹️ USG% (Usage)</h4>
            <p style='font-size: 0.8rem; color: #94a3b8; margin: 5px 0;'><b>Tier:</b> 30%+ Alpha | 20% Starter | < 15% Role</p>
            <p style='font-size: 0.9rem;'>Volume metric. Identifies who handles the rock. Essential for projecting stat spikes when teammates are injured.</p>
        </div>
        <div class="metric-card">
            <h4 style='color: #22c55e; margin:0;'>🛡️ VORP / BPM</h4>
            <p style='font-size: 0.8rem; color: #94a3b8; margin: 5px 0;'><b>Tier:</b> 4.0+ VORP | 6.0+ BPM (Elite)</p>
            <p style='font-size: 0.9rem;'>Impact relative to a replacement player. Identifies the true "Engines" that drive team win probability.</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.success("🧠 **STRATEGIC ALPHA: THE USAGE SPIKE**")
    st.write("""
    The most profitable use of this dashboard is identifying **Usage Vacuum**. When a star player is marked **OUT** in the Sidebar Injury Reporter, their **USG% (Usage)** must be redistributed.
    
    1. Look for players on that team with **High Efficiency (TS%)** but **Low Usage (USG%)**. 
    2. These "hidden alphas" are now primed for a massive statistical spike. 
    3. Use this to find value in over/under player props before the market adjusts.
    """)
    if os.path.exists(path):
        df_players = pd.read_csv(path)
        st.dataframe(df_players[['Player', 'Team', 'PER', 'TS%', 'USG%', 'BPM', 'VORP']].sort_values(by='PER', ascending=False).head(50), use_container_width=True)
    else:
        st.warning("Stats file missing. Run scraper.")

# Footer
st.divider()
st.caption("THE-BASKET-BALL-BANKER- | Designed for Trapperjujo | 2026 Season Launch")
