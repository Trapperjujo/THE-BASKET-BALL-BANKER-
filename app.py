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
    
    /* Prediction Card Specifics */
    .prediction-card {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 15px;
        border-left: 4px solid #22d3ee; /* Neon Cyan */
        margin-bottom: 20px;
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
    st.info("Applying Financial Decision Model (0.25 Kelly Base)")
    
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
    if st.button("🔄 Sync 2026 Model"):
        st.cache_data.clear()
        st.success("Model Cache Purged.")

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
def load_predictions(bankroll_val, current_injuries):
    mc_engine = MonteCarloEngine()
    fin_model = FinancialDecisionModel(bankroll=bankroll_val)
    
    # Apply session injuries to manager
    for team, p_list in current_injuries.items():
        mc_engine.injury_manager.set_injuries(team, p_list)

    # Heuristic predictions (Mock/Actual from compute_nba_alpha)
    try:
        alpha_engine = NBAAlphaEngine()
        alpha_engine.generate_daily_predictions()
        path = ".tmp/predictions/daily_predictions.json"
        with open(path, "r") as f:
            base_preds = json.load(f)
            
        # Enrich with Monte Carlo & Financial Verdicts
        for p in base_preds:
            sim = mc_engine.simulate_game(p['home'], p['away'])
            # Probability based on simulation
            win_p = sim['home_win_prob']/100.0 if p['winner'] == p['home'] else sim['away_win_prob']/100.0
            fin = fin_model.get_smart_stake(win_p, float(p['odds']), 10.0)
            
            p['mc_prob'] = sim['home_win_prob'] if p['winner'] == p['home'] else sim['away_win_prob']
            p['verdict'] = fin['verdict']
            p['risk'] = fin['risk_score']
            p['suggested_stake'] = fin['suggested_stake_cad']
            
        return base_preds
    except:
        return []

# --- DASHBOARD MAIN ---
st.title("🏀 NBA ALPHA COMMAND CENTER")
st.subheader("TRUE 2025-26 Season Insights")

tab1, tab2, tab3, tab4 = st.tabs(["AI Predictions 🎯", "Playoff Simulation 🏆", "League Standings 📈", "Advanced Research ⚡"])

with tab1:
    st.write("### Institutional Prediction Feed")
    
    with st.expander("📖 Dashboard Legend & User Guide"):
        st.markdown("""
        #### Understanding the NBA Alpha Terminal
        
        *   **Heuristic Prob**: Base model confidence derived from Team EPM and historical matchups. It sets the baseline expectation.
        *   **Monte Carlo Prob**: Probabilistic confidence from 1,000+ simulations. This accounts for team volatility and Gaussian distribution of outcomes.
        *   **Risk Score (0.0 - 1.0)**: Measures simulation variance. A high score means the simulation results were widely spread (high uncertainty).
        *   **Market Price**: The current decimal odds from the bookmaker.
        *   **🎯 SMART STAKE**: The mathematically optimal wager in CAD using a **0.25 Adjusted Kelly Criterion**. It factors in your bankroll and the simulation's risk to maximize long-term growth.
        
        ---
        **Strategy**: Look for games where **Monte Carlo Prob** is >10% higher than the implied market odds for maximum +EV value.
        """)
        
    preds = load_predictions(bankroll, st.session_state.out_players)
    
    if preds:
        for p in preds:
            with st.container():
                # Conditional styling based on verdict
                verdict_color = "#22c55e" if "LOCK" in p['verdict'] else "#eab308" if "VALUE" in p['verdict'] else "#94a3b8"
                
                st.markdown(f"""
                <div class="prediction-card">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <p style='font-size: 0.8rem; color: #94a3b8; margin:0;'>{p['date']} • {p['conference']}</p>
                        <span class="verdict-tag" style="background: {verdict_color}; color: white;">{p['verdict']}</span>
                    </div>
                    <h3 style='margin: 10px 0;'>{p['away']} @ {p['home']}</h3>
                    <div style="display: flex; gap: 20px; margin-bottom: 10px;">
                        <div>
                            <p class='metric-label'>Heuristic Prob</p>
                            <p style='color: #22d3ee; font-weight: bold; font-size: 1.2rem;'>{int(p['prob']*100)}%</p>
                        </div>
                        <div>
                            <p class='metric-label'>Monte Carlo Prob</p>
                            <p style='color: #a855f7; font-weight: bold; font-size: 1.2rem;'>{int(p['mc_prob'])}%</p>
                        </div>
                        <div>
                            <p class='metric-label'>Risk Score</p>
                            <p style='color: #f87171; font-weight: bold; font-size: 1.2rem;'>{p['risk']}</p>
                        </div>
                    </div>
                    <hr style='border: 0.1px solid rgba(255,255,255,0.1)'>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <p class='metric-label'>Market Price: <b>{p['odds']}</b></p>
                        <p style='color: #f58426; font-size: 1.2rem; margin: 0;'><b>🎯 SMART STAKE: ${p['suggested_stake']:.2f}</b></p>
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
    st.write("### ⚡ Advanced Metrics Leaderboard")
    
    with st.expander("📊 Analytics Legend & Key"):
        st.markdown("""
        #### How to Interpret Advanced NBA Metrics
        
        | Metric | Definition | Banker's Tip |
| :--- | :--- | :--- |
| **PER** | **Player Efficiency Rating**: Per-minute productivity (League Avg = 15.0). | Identifies dominant performers regardless of pure scoring volume. |
| **TS%** | **True Shooting %**: Measures scoring efficiency including 3PT and FT. | Crucial for over/under point props—efficiency usually beats volume. |
| **USG%** | **Usage Rate**: Percentage of team plays used by a player. | **High Usage + Teammate Injury = MASSIVE volume spike** for props. |
| **BPM** | **Box Plus/Minus**: Box-score estimate of impact per 100 possessions. | Highlights elite defenders or "super-role" players. |
| **VORP** | **Value Over Replacement**: Cumulative impact relative to an average backup. | Best for long-term MVP-caliber player valuation. |

---
**Strategy**: Look for **High Usage (USG%)** players with **High Efficiency (TS%)**—these are the "Banker's" primary targets for statistical consistency.
        """)
        
    path = "history/2026_season/player_advanced_2026.csv"
    if os.path.exists(path):
        df_players = pd.read_csv(path)
        st.dataframe(df_players[['Player', 'Team', 'PER', 'TS%', 'USG%', 'BPM', 'VORP']].sort_values(by='PER', ascending=False).head(50), use_container_width=True)
    else:
        st.warning("Stats file missing. Run scraper.")

# Footer
st.divider()
st.caption("THE-BASKET-BALL-BANKER- | Designed for Trapperjujo | 2026 Season Launch")
