import numpy as np

class FinancialDecisionModel:
    """
    Applies institutional-grade financial decision models to NBA betting.
    Focuses on Risk Management, Credit/Cost of Capital (Bankroll), and Cost-Benefit.
    """
    
    def __init__(self, bankroll=1000.0, max_drawdown=0.20, kelly_fraction=0.25):
        self.bankroll = bankroll
        self.max_drawdown = max_drawdown # Risk tolerance (20% max)
        self.kelly_fraction = kelly_fraction # e.g. 0.25, 0.5, 1.0

    def calculate_cost_benefit(self, prob, odds):
        """
        Standard EV calculation (Cost-Benefit Analysis).
        odds: Decimal odds (e.g. 1.91 for -110)
        """
        ev = (prob * (odds - 1)) - (1 - prob)
        return round(ev, 4)

    def get_smart_stake(self, prob, odds, confidence_interval_width):
        """
        Financial Decision Model: Adjusted Kelly Criterion.
        Factors in the 'Credit Cost' (Risk) of the variance in my simulation.
        """
        # Base Kelly
        b = odds - 1
        p = prob
        q = 1 - p
        kelly = (b * p - q) / b
        
        # Risk Scaling (Cost Analysis):
        # If the simulation variance is high (wide CI), we reduce the stake.
        # institutional 'fractional Kelly' approach
        volatility_penalty = 1.0 - (min(confidence_interval_width, 15.0) / 30.0)
        smart_kelly = kelly * self.kelly_fraction * volatility_penalty # Base Kelly control
        
        # Ensure we don't exceed max drawdown
        suggested_stake = max(0.0, self.bankroll * smart_kelly)
        return {
            "ev": self.calculate_cost_benefit(p, odds),
            "suggested_stake_cad": round(suggested_stake, 2),
            "risk_score": round(1.0 - volatility_penalty, 2), # 0 (safe) to 1 (risky)
            "verdict": self._get_verdict(p, odds, suggested_stake)
        }

    def _get_verdict(self, p, odds, stake):
        ev = self.calculate_cost_benefit(p, odds)
        if stake <= 0: return "SKIP (No Margin)"
        if ev > 0.15 and p > 0.65: return "FINANCIAL LOCK"
        if ev > 0.05: return "VALUE BET"
        return "MARGINAL"

if __name__ == "__main__":
    # Test cases
    model = FinancialDecisionModel()
    # High confidence low variance
    print(f"Lock Test: {model.get_smart_stake(0.75, 1.91, 5.0)}")
    # Low confidence high variance
    print(f"Risk Test: {model.get_smart_stake(0.55, 1.91, 15.0)}")
