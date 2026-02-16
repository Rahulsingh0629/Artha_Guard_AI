from datetime import datetime, date, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict

# --- 1. Domain Models & Constants ---

class AssetType(Enum):
    EQUITY_DELIVERY = "EQUITY_DELIVERY"
    EQUITY_INTRADAY = "EQUITY_INTRADAY" 
    MUTUAL_FUND_EQUITY = "MUTUAL_FUND_EQUITY"
    # Add Debt, Gold, F&O as needed

@dataclass
class TaxRule:
    """Configuration for a specific tax scenario."""
    stcg_rate: Decimal
    ltcg_rate: Decimal
    ltcg_threshold_days: int
    ltcg_exemption_limit: Decimal  # e.g., 1.25 Lakh for Equity
    cess_rate: Decimal = Decimal("0.04") # 4% Health & Education Cess

@dataclass
class TaxResult:
    """Structured output for the tax calculation."""
    asset_type: str
    buy_date: date
    sell_date: date
    holding_days: int
    period_type: str  # 'Long Term' or 'Short Term'
    
    gross_profit: Decimal
    taxable_income: Decimal
    tax_rate_applied: str
    
    base_tax: Decimal
    cess_amount: Decimal
    total_tax: Decimal
    net_profit: Decimal

# --- 2. Configuration Store (The "Brain") ---

class TaxConfiguration:
    """
    Stores tax rules for different Financial Years (FY).
    This allows the engine to handle historical backtesting correctly.
    """
    # Rules for FY 2026-27 (Union Budget 2024)
    FY_2026_27_RULES: Dict[AssetType, TaxRule] = {
        AssetType.EQUITY_DELIVERY: TaxRule(
            stcg_rate=Decimal("0.20"),      # 20%
            ltcg_rate=Decimal("0.125"),     # 12.5%
            ltcg_threshold_days=365,        # > 1 Year
            ltcg_exemption_limit=Decimal("125000"), # ₹1.25 Lakh Exemption
            cess_rate=Decimal("0.04")
        ),
        AssetType.MUTUAL_FUND_EQUITY: TaxRule(
            stcg_rate=Decimal("0.20"),
            ltcg_rate=Decimal("0.125"),
            ltcg_threshold_days=365,
            ltcg_exemption_limit=Decimal("125000"),
            cess_rate=Decimal("0.04")
        )
    }

    @staticmethod
    def get_rule(asset_type: AssetType) -> TaxRule:
        # In a real app, you might select rules based on the 'sell_date' financial year
        rule = TaxConfiguration.FY_2026_27_RULES.get(asset_type)
        if rule is None:
            raise ValueError(f"No rule found for asset type: {asset_type}")
        return rule

# --- 3. The Engine ---

class AdvancedTaxEngine:
    def __init__(self):
        # Setting precision context if needed, usually default is fine
        pass

    def _quantize(self, value: Decimal) -> Decimal:
        """Helper to round to 2 decimal places properly."""
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate_tax(
        self, 
        buy_date: datetime, 
        quantity: int, 
        buy_price: float, 
        current_price: float,
        asset_type: AssetType = AssetType.EQUITY_DELIVERY,
        realized_ltcg_ytd: float = 0.0 # How much LTCG exemption user has already used this year
    ) -> TaxResult:
        
        # 1. Input Sanitization & Type Conversion
        if not buy_date:
            buy_date = datetime.now(timezone.utc)
        elif buy_date.tzinfo is None:
            buy_date = buy_date.replace(tzinfo=timezone.utc)
        else:
            buy_date = buy_date.astimezone(timezone.utc)
        
        # Convert floats to Decimals for math
        d_buy_price = Decimal(str(buy_price))
        d_current_price = Decimal(str(current_price))
        d_qty = Decimal(str(quantity))
        d_realized_ltcg_ytd = Decimal(str(realized_ltcg_ytd))
        
        sell_date = datetime.now(timezone.utc) # Assuming calculation is for "Now"
        
        # 2. Basic Calculations
        holding_days = (sell_date - buy_date).days
        gross_revenue = d_current_price * d_qty
        cost_basis = d_buy_price * d_qty
        gross_profit = gross_revenue - cost_basis

        # 3. Load Rules
        rule = TaxConfiguration.get_rule(asset_type)
        if not rule:
            raise ValueError(f"No tax rules defined for {asset_type}")

        # 4. Determine Holding Period (STCG vs LTCG)
        is_long_term = holding_days > rule.ltcg_threshold_days
        
        taxable_income = Decimal("0.00")
        base_tax = Decimal("0.00")
        tax_rate_display = "0%"
        period_type = "Long Term" if is_long_term else "Short Term"

        # 5. Tax Logic
        if gross_profit <= 0:
            # Loss Scenario (No Tax)
            pass 
        elif not is_long_term:
            # --- STCG Case ---
            taxable_income = gross_profit
            base_tax = taxable_income * rule.stcg_rate
            tax_rate_display = f"{rule.stcg_rate * 100}%"
        else:
            # --- LTCG Case (With Exemption Logic) ---
            # Logic: We only tax the amount that exceeds the exemption limit.
            # We must account for how much exemption was ALREADY used this year.
            
            remaining_exemption = max(Decimal("0"), rule.ltcg_exemption_limit - d_realized_ltcg_ytd)
            
            if gross_profit > remaining_exemption:
                taxable_income = gross_profit - remaining_exemption
                base_tax = taxable_income * rule.ltcg_rate
                tax_rate_display = f"{rule.ltcg_rate * 100}% (Exemption applied)"
            else:
                taxable_income = Decimal("0")
                base_tax = Decimal("0")
                tax_rate_display = "0% (Under Exemption Limit)"

        # 6. Cess Calculation (Tax on Tax)
        cess_amount = base_tax * rule.cess_rate
        total_tax = base_tax + cess_amount
        net_profit = gross_profit - total_tax

        # 7. Construct Report
        return TaxResult(
            asset_type=asset_type.value,
            buy_date=buy_date.date(),
            sell_date=sell_date.date(),
            holding_days=holding_days,
            period_type=period_type,
            gross_profit=self._quantize(gross_profit),
            taxable_income=self._quantize(taxable_income),
            tax_rate_applied=tax_rate_display,
            base_tax=self._quantize(base_tax),
            cess_amount=self._quantize(cess_amount),
            total_tax=self._quantize(total_tax),
            net_profit=self._quantize(net_profit)
        )

# --- 4. Usage Example ---

if __name__ == "__main__":
    engine = AdvancedTaxEngine()
    
    # Example: User bought shares 400 days ago (Long Term)
    # Buy: 100 qty @ 1000 = 1,00,000
    # Current: 100 qty @ 2500 = 2,50,000
    # Profit: 1,50,000
    # Exemption: 1,25,000
    # Taxable: 25,000 @ 12.5% + Cess
    
    buy_date = datetime.now().replace(year=datetime.now().year - 2) 
    
    result = engine.calculate_tax(
        buy_date=buy_date,
        quantity=100,
        buy_price=1000.0,
        current_price=2500.0,
        asset_type=AssetType.EQUITY_DELIVERY,
        realized_ltcg_ytd=0.0 # User hasn't sold anything else this year
    )

    print(f"--- Tax Report for {result.asset_type} ---")
    print(f"Holding Period: {result.holding_days} days ({result.period_type})")
    print(f"Gross Profit  : ₹{result.gross_profit}")
    print(f"Taxable Income: ₹{result.taxable_income} (After exemption)")
    print(f"Tax Rate      : {result.tax_rate_applied}")
    print(f"Base Tax      : ₹{result.base_tax}")
    print(f"Cess (4%)     : ₹{result.cess_amount}")
    print(f"Total Tax     : ₹{result.total_tax}")
    print(f"Net Profit    : ₹{result.net_profit}")
