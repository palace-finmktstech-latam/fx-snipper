from datetime import datetime, date, timedelta
from typing import Dict, List, Union, Any, Tuple, Optional
import math

def format_date_with_weekday(date_str: str) -> str:
    """Convert YYYY-MM-DD to DDD-DD-MM-YYYY format."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%a-%d-%m-%Y")
    except ValueError:
        return date_str

def format_rate(rate: Union[str, float]) -> str:
    """Format rate as percentage string."""
    if isinstance(rate, str):
        return rate
    return f"{rate*100:.2f}%"

def transform_output(trade_json: dict, leg1_cashflows: list, leg2_cashflows: list) -> dict:
    """Transform the API output to match the required format."""
    trade_summary = trade_json["TradeSummary"]
    
    # Create tradeInfo section
    trade_info = {
        "tradeDate": trade_summary["Trade Date"],
        "maturity": trade_summary["Maturity"],
        "priceMaker": trade_summary["Price Maker"],
        "priceTaker": trade_summary["Price Taker"],
        "acceptedPrice": trade_summary["Accepted Price"],
        "acceptedSide": trade_summary["Accepted Side"],
        "leg1Type": trade_summary["Leg 1 Payer"]["Leg Type"],
        "leg1Rate": trade_summary["Leg 1 Payer"]["Rate"],
        "leg1Payer": trade_summary["Leg 1 Payer"]["Company"],
        "leg1Currency": trade_summary["Leg 1 Payer"]["Leg Currency"],
        "leg1NotionalAmount": trade_summary["Leg 1 Payer"]["Notional Amount"],
        "leg1DayCountConvention": trade_summary["Leg 1 Payer"]["Date Basis"],
        "leg1BusinessDayConvention": trade_summary["Leg 1 Payer"]["Business Date Adjustment"],
        "leg2Type": trade_summary["Leg 2 Payer"]["Leg Type"],
        "leg2Rate": trade_summary["Leg 2 Payer"]["Rate"],
        "leg2Payer": trade_summary["Leg 2 Payer"]["Company"],
        "leg2Currency": trade_summary["Leg 2 Payer"]["Leg Currency"],
        "leg2NotionalAmount": trade_summary["Leg 2 Payer"]["Notional Amount"],
        "leg2DayCountConvention": trade_summary["Leg 2 Payer"]["Date Basis"],
        "leg2BusinessDayConvention": trade_summary["Leg 2 Payer"]["Business Date Adjustment"]
    }

    # Transform cashflows
    def transform_cashflows(cashflows: list, leg_number: int, payer: str, 
                          day_count: str, currency: str, leg_type: str) -> dict:
        return {
            "legNumber": leg_number,
            "payer": payer,
            "dayCountConvention": day_count,
            "currency": currency,
            "legType": leg_type,
            "cashflows": [{
                "startDate": format_date_with_weekday(cf["Start Date"]),
                "endDate": format_date_with_weekday(cf["End Date"]),
                "rate": format_rate(cf["Rate"]),
                "spread": format_rate(cf["Spread"]),
                "remainingCapital": cf["Notional"],
                "amortization": cf["Amortization"],
                "interest": cf["Interest"]
            } for cf in cashflows]
        }

    # Create legs section
    legs = [
        transform_cashflows(
            leg1_cashflows, 1,
            trade_summary["Leg 1 Payer"]["Company"],
            trade_summary["Leg 1 Payer"]["Date Basis"],
            trade_summary["Leg 1 Payer"]["Leg Currency"],
            trade_summary["Leg 1 Payer"]["Leg Type"]
        ),
        transform_cashflows(
            leg2_cashflows, 2,
            trade_summary["Leg 2 Payer"]["Company"],
            trade_summary["Leg 2 Payer"]["Date Basis"],
            trade_summary["Leg 2 Payer"]["Leg Currency"],
            trade_summary["Leg 2 Payer"]["Leg Type"]
        )
    ]

    return {
        "tradeInfo": trade_info,
        "legs": legs
    }

class SwapParamTransformer:
    def __init__(self):
        # Mapping of date basis strings to day count conventions
        self.date_basis_map = {
            "actual/360": "Actual/360",
            "actual/365": "Actual/365",
            "30/360": "30/360",
            "30e/360": "30E/360"
        }
        
        # Mapping of business day convention strings
        self.bdc_map = {
            "no adjustment": "Unadjusted",
            "modified following": "ModifiedFollowing",
            "following": "Following",
            "modified preceding": "ModifiedPreceding",
            "preceding": "Preceding"
        }
        
        # Mapping of frequency strings to period values
        self.frequency_map = {
            "daily": {"period": "Daily", "months": 0},
            "weekly": {"period": "Weekly", "months": 0},
            "monthly": {"period": "Monthly", "months": 1},
            "quarterly": {"period": "Quarterly", "months": 3},
            "semi-annually": {"period": "Semiannual", "months": 6},
            "annually": {"period": "Annual", "months": 12},
            "one-off": {"period": "Once", "months": 0}
        }
        
    def transform_json(self, trade_json: Dict[str, Any]) -> Dict[str, Any]:
        """Transform the AI-extracted JSON into a format suitable for QuantLib."""
        trade_summary = trade_json["TradeSummary"]
        
        # Get trade date
        trade_date_str = trade_summary["Trade Date"]
        trade_date = datetime.strptime(trade_date_str, "%d-%m-%Y").date()
        
        # Calculate effective date (trade date + start lag)
        start_lag = int(trade_summary.get("Start Lag", 0))
        effective_date = trade_date + timedelta(days=start_lag)
        
        # Parse maturity
        maturity_str = trade_summary["Maturity"]
        termination_date = self._parse_maturity(maturity_str, effective_date)
        
        # Extract leg 1 (fixed) details
        leg1 = trade_summary["Leg 1 Payer"]
        leg1_type = leg1["Leg Type"].lower()
        leg1_rate = self._parse_rate(leg1["Rate"])
        leg1_notional = float(leg1["Notional Amount"])
        leg1_date_basis = self._normalize_date_basis(leg1["Date Basis"])
        leg1_bdc = self._normalize_bdc(leg1["Business Date Adjustment"])
        leg1_frequency = self._normalize_frequency(leg1.get("Coupon Frequency", "Semi-Annually"))
        
        # Extract leg 2 (floating) details
        leg2 = trade_summary["Leg 2 Payer"]
        leg2_type = leg2["Leg Type"].lower()
        leg2_rate = self._parse_rate(leg2["Rate"])
        leg2_notional = float(leg2["Notional Amount"])
        leg2_date_basis = self._normalize_date_basis(leg2["Date Basis"])
        leg2_bdc = self._normalize_bdc(leg2["Business Date Adjustment"])
        leg2_frequency = self._normalize_frequency(leg2.get("Coupon Frequency", "Semi-Annually"))
        
        # Determine which leg is fixed and which is floating
        if leg1_type == "fixed" and leg2_type == "floating":
            fixed_leg = {
                "rate": leg1_rate,
                "notional": leg1_notional,
                "date_basis": leg1_date_basis,
                "bdc": leg1_bdc,
                "frequency": leg1_frequency
            }
            floating_leg = {
                "spread": leg2_rate if isinstance(leg2_rate, float) else 0.0,
                "notional": leg2_notional,
                "date_basis": leg2_date_basis,
                "bdc": leg2_bdc,
                "frequency": leg2_frequency
            }
        elif leg1_type == "floating" and leg2_type == "fixed":
            fixed_leg = {
                "rate": leg2_rate,
                "notional": leg2_notional,
                "date_basis": leg2_date_basis,
                "bdc": leg2_bdc,
                "frequency": leg2_frequency
            }
            floating_leg = {
                "spread": leg1_rate if isinstance(leg1_rate, float) else 0.0,
                "notional": leg1_notional,
                "date_basis": leg1_date_basis,
                "bdc": leg1_bdc,
                "frequency": leg1_frequency
            }
        else:
            # Default if types are unclear
            fixed_leg = {
                "rate": leg1_rate,
                "notional": leg1_notional,
                "date_basis": leg1_date_basis,
                "bdc": leg1_bdc,
                "frequency": leg1_frequency
            }
            floating_leg = {
                "spread": 0.0,
                "notional": leg2_notional,
                "date_basis": leg2_date_basis,
                "bdc": leg2_bdc,
                "frequency": leg2_frequency
            }
        
        # Return transformed parameters
        return {
            "trade_date": trade_date,
            "effective_date": effective_date,
            "termination_date": termination_date,
            "fixed_leg": fixed_leg,
            "floating_leg": floating_leg
        }
    
    def _parse_maturity(self, maturity_str: str, effective_date: date) -> date:
        """Parse maturity string into a date."""
        # Try to parse as a specific date
        try:
            return datetime.strptime(maturity_str, "%d-%m-%Y").date()
        except ValueError:
            pass
        
        # Try to parse as a tenor (e.g., "5Y", "10Y", "1Y6M")
        years = 0
        months = 0
        
        # Handle "Y" for years
        if "Y" in maturity_str:
            years_part = maturity_str.split("Y")[0]
            if years_part:
                years = float(years_part)
        
        # Handle "M" for months
        if "M" in maturity_str:
            months_part = maturity_str.split("M")[0]
            if "Y" in months_part:
                months_part = months_part.split("Y")[1]
            if months_part:
                months = int(months_part)
        
        # Calculate termination date
        total_months = int(years * 12) + months
        years_to_add = total_months // 12
        months_to_add = total_months % 12
        
        new_year = effective_date.year + years_to_add
        new_month = effective_date.month + months_to_add
        
        if new_month > 12:
            new_year += 1
            new_month -= 12
        
        # Handle month end adjustments
        day = min(effective_date.day, self._get_month_end_day(new_year, new_month))
        
        return date(new_year, new_month, day)
    
    def _get_month_end_day(self, year: int, month: int) -> int:
        """Get the last day of the specified month."""
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        return (next_month - timedelta(days=1)).day
    
    def _parse_rate(self, rate_str: Union[str, float]) -> float:
        """Parse rate string into a float."""
        if isinstance(rate_str, float):
            return rate_str
        
        # Remove percentage sign and convert to decimal
        if isinstance(rate_str, str):
            if "%" in rate_str:
                return float(rate_str.replace("%", "")) / 100
            else:
                try:
                    return float(rate_str)
                except ValueError:
                    return 0.0
        return 0.0
    
    def _normalize_date_basis(self, date_basis: str) -> str:
        """Normalize date basis string to a standard format."""
        date_basis_lower = date_basis.lower()
        for key, value in self.date_basis_map.items():
            if key in date_basis_lower:
                return value
        return "Actual/360"  # Default
    
    def _normalize_bdc(self, bdc: str) -> str:
        """Normalize business day convention string to a standard format."""
        bdc_lower = bdc.lower()
        for key, value in self.bdc_map.items():
            if key in bdc_lower:
                return value
        return "ModifiedFollowing"  # Default
    
    def _normalize_frequency(self, frequency: str) -> Dict[str, Any]:
        """Normalize frequency string to a standard format."""
        frequency_lower = frequency.lower()
        for key, value in self.frequency_map.items():
            if key in frequency_lower:
                return value
        return self.frequency_map["semi-annually"]  # Default

def load_ql_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert transformed parameters into QuantLib-specific parameters."""
    # In a real implementation, this would prepare parameters for QuantLib
    # For simplicity, we'll return a basic structure for cashflow generation
    
    fixed_leg_freq_months = params["fixed_leg"]["frequency"]["months"]
    floating_leg_freq_months = params["floating_leg"]["frequency"]["months"]
    
    # Calculate number of payments based on frequency
    term_months = (params["termination_date"].year - params["effective_date"].year) * 12 + \
                  params["termination_date"].month - params["effective_date"].month
    
    fixed_payments = math.ceil(term_months / fixed_leg_freq_months) if fixed_leg_freq_months > 0 else 1
    floating_payments = math.ceil(term_months / floating_leg_freq_months) if floating_leg_freq_months > 0 else 1
    
    return {
        "trade_date": params["trade_date"],
        "effective_date": params["effective_date"],
        "termination_date": params["termination_date"],
        "fixed_rate": params["fixed_leg"]["rate"],
        "fixed_notional": params["fixed_leg"]["notional"],
        "fixed_date_basis": params["fixed_leg"]["date_basis"],
        "fixed_bdc": params["fixed_leg"]["bdc"],
        "fixed_freq_months": fixed_leg_freq_months,
        "fixed_payments": fixed_payments,
        "floating_spread": params["floating_leg"]["spread"],
        "floating_notional": params["floating_leg"]["notional"],
        "floating_date_basis": params["floating_leg"]["date_basis"],
        "floating_bdc": params["floating_leg"]["bdc"],
        "floating_freq_months": floating_leg_freq_months,
        "floating_payments": floating_payments
    }

def create_swap_cashflows(**kwargs) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate simplified cashflow schedules for both legs of a swap."""
    effective_date = kwargs["effective_date"]
    termination_date = kwargs["termination_date"]
    
    # Fixed leg parameters
    fixed_rate = kwargs["fixed_rate"]
    fixed_notional = kwargs["fixed_notional"]
    fixed_freq_months = kwargs["fixed_freq_months"]
    fixed_payments = kwargs["fixed_payments"]
    
    # Floating leg parameters
    floating_spread = kwargs["floating_spread"]
    floating_notional = kwargs["floating_notional"]
    floating_freq_months = kwargs["floating_freq_months"]
    floating_payments = kwargs["floating_payments"]
    
    # Generate fixed leg cashflows
    fixed_leg = []
    remaining_notional = fixed_notional
    amortization_per_period = fixed_notional / fixed_payments if fixed_payments > 0 else fixed_notional
    
    for i in range(fixed_payments):
        # Calculate payment date
        if fixed_freq_months > 0:
            months_to_add = (i + 1) * fixed_freq_months
            years_to_add = months_to_add // 12
            months_to_add = months_to_add % 12
            
            payment_year = effective_date.year + years_to_add
            payment_month = effective_date.month + months_to_add
            
            if payment_month > 12:
                payment_year += 1
                payment_month -= 12
            
            payment_day = min(effective_date.day, _get_month_end_day(payment_year, payment_month))
            payment_date = date(payment_year, payment_month, payment_day)
        else:
            # One-off payment
            payment_date = termination_date
        
        # Calculate period dates
        if i == 0:
            start_date = effective_date
        else:
            prev_months = i * fixed_freq_months
            prev_years = prev_months // 12
            prev_months = prev_months % 12
            
            start_year = effective_date.year + prev_years
            start_month = effective_date.month + prev_months
            
            if start_month > 12:
                start_year += 1
                start_month -= 12
            
            start_day = min(effective_date.day, _get_month_end_day(start_year, start_month))
            start_date = date(start_year, start_month, start_day)
        
        # Calculate accrual days (simplified)
        accrual_days = (payment_date - start_date).days
        
        # Apply amortization
        if i == fixed_payments - 1:
            # Last payment - ensure we amortize to zero
            amortization = remaining_notional
        else:
            amortization = amortization_per_period
        
        # Calculate interest (simplified)
        interest = remaining_notional * fixed_rate * accrual_days / 365
        
        # Create cashflow entry
        cashflow = {
            "Start Date": start_date.strftime("%Y-%m-%d"),
            "End Date": payment_date.strftime("%Y-%m-%d"),
            "Rate": fixed_rate,
            "Spread": 0.0,
            "Notional": remaining_notional,
            "Amortization": amortization,
            "Interest": interest
        }
        
        fixed_leg.append(cashflow)
        
        # Update remaining notional
        remaining_notional -= amortization
    
    # Generate floating leg cashflows
    floating_leg = []
    remaining_notional = floating_notional
    amortization_per_period = floating_notional / floating_payments if floating_payments > 0 else floating_notional
    
    for i in range(floating_payments):
        # Calculate payment date
        if floating_freq_months > 0:
            months_to_add = (i + 1) * floating_freq_months
            years_to_add = months_to_add // 12
            months_to_add = months_to_add % 12
            
            payment_year = effective_date.year + years_to_add
            payment_month = effective_date.month + months_to_add
            
            if payment_month > 12:
                payment_year += 1
                payment_month -= 12
            
            payment_day = min(effective_date.day, _get_month_end_day(payment_year, payment_month))
            payment_date = date(payment_year, payment_month, payment_day)
        else:
            # One-off payment
            payment_date = termination_date
        
        # Calculate period dates
        if i == 0:
            start_date = effective_date
        else:
            prev_months = i * floating_freq_months
            prev_years = prev_months // 12
            prev_months = prev_months % 12
            
            start_year = effective_date.year + prev_years
            start_month = effective_date.month + prev_months
            
            if start_month > 12:
                start_year += 1
                start_month -= 12
            
            start_day = min(effective_date.day, _get_month_end_day(start_year, start_month))
            start_date = date(start_year, start_month, start_day)
        
        # Calculate accrual days (simplified)
        accrual_days = (payment_date - start_date).days
        
        # Apply amortization
        if i == floating_payments - 1:
            # Last payment - ensure we amortize to zero
            amortization = remaining_notional
        else:
            amortization = amortization_per_period
        
        # Calculate interest (simplified)
        # For floating rate, we're using a placeholder rate of 2% plus spread
        floating_rate = 0.02
        interest = remaining_notional * (floating_rate + floating_spread) * accrual_days / 365
        
        # Create cashflow entry
        cashflow = {
            "Start Date": start_date.strftime("%Y-%m-%d"),
            "End Date": payment_date.strftime("%Y-%m-%d"),
            "Rate": floating_rate,
            "Spread": floating_spread,
            "Notional": remaining_notional,
            "Amortization": amortization,
            "Interest": interest
        }
        
        floating_leg.append(cashflow)
        
        # Update remaining notional
        remaining_notional -= amortization
    
    return fixed_leg, floating_leg

def _get_month_end_day(year: int, month: int) -> int:
    """Get the last day of the specified month."""
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - timedelta(days=1)).day