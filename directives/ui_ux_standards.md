# NBA Predictive Terminal: UI/UX Standards

## Aesthetic: "Glassmorphic Analytical Terminal"

### 1. Colors & Theme
- **Background**: Deep Indigo/Midnight (#0F172A).
- **Glass Effect**: Transparent panels with 15-20% opacity white, backdrop blur (20-30px).
- **Accents**: 
    - NBA Orange (#F58426) for call-to-actions.
    - Neon Cyan (#22D3EE) for "Value" highlights.
    - Soft Red (#EF4444) for "Fade" recommendations.

### 2. Layout Structure
- **Global Hub**: Persistent Sidebar for navigating between (A) Daily Prediction Feed, (B) Player Research Dashboard, (C) League Power Rankings.
- **High-Density Data**: Tables must be clear but compact. Use `st.dataframe` or `st.table` with custom CSS for reduced padding.
- **AI Insights Panel**: Dedicated card with a custom emoji icon (🤖) for narrative AI summaries.

### 3. Interactive Elements
- **Expander Matchups**: Each game is its own expander. Inside, show:
    - Team Win Probability (Elo-based).
    - +EV Betting Recommendations (+EV % and suggested unit).
    - Kelly Criterion Wager Allocation.
- **Filter Bars**: Date selection, Team filtering, Min/Max PER/USG filtering.

### 4. Typography
- **Headings**: Modern sans-serif (e.g., 'Inter', 'Outfit', 'Roboto').
- **Monospace**: Only for critical stats (PER, EPM) to emphasize data accuracy.

### 5. Micro-Animations
- Hover states for buttons.
- Fade-in transitions for new data loads.
- Progress bars for "Season Progress" or "Confidence Levels".
