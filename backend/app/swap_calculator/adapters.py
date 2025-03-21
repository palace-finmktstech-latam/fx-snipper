# backend/app/swap_calculator/adapters.py
from datetime import date, datetime, timedelta
from typing import Dict, Any, Union, Tuple
import math
from app.swap_calculator.constants import (
    DayCountConvention, 
    BusinessDayConvention, 
    PaymentFrequency,
    FREQUENCY_MONTHS
)

def parse_date_basis(date_basis_str: str) -> str:
    """Convert a string date basis to a standardized format."""
    date_basis_lower = date_basis_str.lower()
    
    if "actual/360" in date_basis_lower:
        return DayCountConvention.ACT_360
    elif "actual/365" in date_basis_lower:
        return DayCountConvention.ACT_365
    elif "30/360" in date_basis_lower:
        return DayCountConvention.THIRTY_360
    elif "30e/360" in date_basis_lower:
        return DayCountConvention.THIRTY_E_360
    
    return DayCountConvention.ACT_360  # Default

def parse_business_day_convention(bdc_str: str) -> str:
    """Convert a string business day convention to a standardized format."""
    bdc_lower = bdc_str.lower()
    
    if "modified following" in bdc_lower:
        return BusinessDayConvention.MODIFIED_FOLLOWING
    elif "following" in bdc_lower:
        return BusinessDayConvention.FOLLOWING
    elif "modified preceding" in bdc_lower:
        return BusinessDayConvention.MODIFIED_PRECEDING
    elif "preceding" in bdc_lower:
        return BusinessDayConvention.PRECEDING
    elif "no adjustment" in bdc_lower:
        return BusinessDayConvention.UNADJUSTED
    
    return BusinessDayConvention.MODIFIED_FOLLOWING  # Default

def parse_frequency(frequency_str: str) -> Dict[str, Any]:
    """Convert a string frequency to standardized period and months."""
    frequency_lower = frequency_str.lower()
    
    if "daily" in frequency_lower:
        period = PaymentFrequency.DAILY
    elif "weekly" in frequency_lower:
        period = PaymentFrequency.WEEKLY
    elif "monthly" in frequency_lower:
        period = PaymentFrequency.MONTHLY
    elif "quarterly" in frequency_lower:
        period = PaymentFrequency.QUARTERLY
    elif "semi-annually" in frequency_lower or "semiannually" in frequency_lower:
        period = PaymentFrequency.SEMIANNUAL
    elif "annually" in frequency_lower:
        period = PaymentFrequency.ANNUAL
    elif "one-off" in frequency_lower:
        period = PaymentFrequency.ONCE
    else:
        period = PaymentFrequency.SEMIANNUAL  # Default
    
    return {
        "period": period,
        "months": FREQUENCY_MONTHS[period]
    }

def parse_maturity(maturity_str: str, effective_date: date) -> date:
    """Convert a maturity string to a date."""
    # Try to parse as a specific date first
    try:
        return datetime.strptime(maturity_str, "%d-%m-%Y").date()
    except ValueError:
        pass
    
    # Parse as a tenor (e.g., "5Y", "10Y", "1Y6M")
    years = months = 0
    
    # Extract years
    if "Y" in maturity_str:
        years_part = maturity_str.split("Y")[0]
        if years_part:
            years = float(years_part)
    
    # Extract months
    if "M" in maturity_str:
        months_part = maturity_str.split("M")[0]
        if "Y" in months_part:
            months_part = months_part.split("Y")[1]
        if months_part and months_part.strip():
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
    day = min(effective_date.day, get_month_end_day(new_year, new_month))
    
    return date(new_year, new_month, day)

def get_month_end_day(year: int, month: int) -> int:
    """Get the last day of the specified month."""
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - timedelta(days=1)).day

def parse_rate(rate_value: Union[str, float]) -> float:
    """Convert a rate string or value to a decimal."""
    if isinstance(rate_value, float):
        return rate_value
    
    if isinstance(rate_value, str):
        if "%" in rate_value:
            # Convert percentage to decimal
            return float(rate_value.replace("%", "").strip()) / 100
        else:
            try:
                return float(rate_value)
                
            except ValueError:
                #return 0.0
                return rate_value
    
    return 0.0

def prepare_swap_parameters(trade_json: Dict[str, Any]) -> Dict[str, Any]:
    """Transform trade JSON into parameters for cashflow calculation."""
    trade_summary = trade_json["TradeSummary"]
    
    # Get trade date
    trade_date_str = trade_summary["Trade Date"]
    trade_date = datetime.strptime(trade_date_str, "%d-%m-%Y").date()
    
    # Calculate effective date (trade date + start lag)
    start_lag = int(trade_summary.get("Start Lag", 0))
    effective_date = trade_date + timedelta(days=start_lag)
    
    # Parse maturity
    maturity_str = trade_summary["Maturity"]
    termination_date = parse_maturity(maturity_str, effective_date)
    
    # Extract leg details
    leg1 = trade_summary["Leg 1 Payer"]
    leg2 = trade_summary["Leg 2 Payer"]
    
    # Prepare leg parameters
    legs = []
    for leg in [leg1, leg2]:
        leg_type = leg["Leg Type"].lower()
        rate = parse_rate(leg["Rate"])
        params = {
            "type": leg_type,
            "rate": rate,
            "notional": float(leg["Notional Amount"]),
            "currency": leg["Leg Currency"],
            "date_basis": parse_date_basis(leg["Date Basis"]),
            "business_day_convention": parse_business_day_convention(leg["Business Date Adjustment"]),
            "frequency": parse_frequency(leg.get("Coupon Frequency", "Semi-Annually")),
            "company": leg["Company"]
        }
        legs.append(params)
    
    # Determine which leg is fixed and which is floating
    if legs[0]["type"] == "fixed" and legs[1]["type"] == "floating":
        fixed_leg, floating_leg = legs[0], legs[1]
    elif legs[0]["type"] == "floating" and legs[1]["type"] == "fixed":
        floating_leg, fixed_leg = legs[0], legs[1]
    else:
        # Default handling if types are unclear
        fixed_leg, floating_leg = legs[0], legs[1]
        fixed_leg["type"] = "fixed"
        floating_leg["type"] = "floating"
    
    return {
        "trade_date": trade_date,
        "effective_date": effective_date,
        "termination_date": termination_date,
        "fixed_leg": fixed_leg,
        "floating_leg": floating_leg
    }