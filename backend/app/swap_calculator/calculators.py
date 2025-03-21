from datetime import date, timedelta
from typing import List, Dict, Any, Tuple, Optional
import math
import calendar
# Default floating rate removed - no longer needed
from app.swap_calculator.constants import (
    FREQUENCY_MONTHS
)
from app.main import logger
from core_logging.client import EventType, LogLevel
import os

# Get parameters from environment variables
my_entity = os.environ.get('MY_ENTITY', 'Unknown')

def calculate_interest(
    notional: float,
    rate: float,
    start_date: date,
    end_date: date,
    day_count_convention: str
) -> float:
    """
    Calculate interest based on the specified day count convention.
    
    Args:
        notional: The notional amount for the period
        rate: The interest rate as a percentage (e.g., 2.215 for 2.215%)
        start_date: Period start date
        end_date: Period end date
        day_count_convention: The day count convention to use
        
    Returns:
        The calculated interest amount
    """
    accrual_days = (end_date - start_date).days
    rate_decimal = rate / 100  # Convert percentage to decimal
    
    if day_count_convention == "Actual/365" or day_count_convention == "Actual/365F":
        return notional * rate_decimal * accrual_days / 365
    
    elif day_count_convention == "Actual/360":
        return notional * rate_decimal * accrual_days / 360
    
    elif day_count_convention == "30/360" or day_count_convention == "Bond Basis":
        # Implement 30/360 (ISDA) convention
        d1 = min(start_date.day, 30)
        d2 = min(end_date.day, 30) if d1 == 30 else end_date.day
        days_360 = (360 * (end_date.year - start_date.year) + 
                   30 * (end_date.month - start_date.month) + 
                   (d2 - d1))
        return notional * rate_decimal * days_360 / 360
    
    elif day_count_convention == "30E/360" or day_count_convention == "Eurobond Basis":
        # European 30/360
        d1 = min(start_date.day, 30)
        d2 = min(end_date.day, 30)
        days_360 = (360 * (end_date.year - start_date.year) + 
                   30 * (end_date.month - start_date.month) + 
                   (d2 - d1))
        return notional * rate_decimal * days_360 / 360
    
    elif day_count_convention == "Actual/Actual" or day_count_convention == "Actual/Actual ISDA":
        # Handle leap years properly
        if start_date.year == end_date.year:
            days_in_year = 366 if calendar.isleap(start_date.year) else 365
            return notional * rate_decimal * accrual_days / days_in_year
        else:
            # Split calculation across years
            interest = 0
            current_date = start_date
            while current_date < end_date:
                year_end = date(current_date.year, 12, 31)
                if year_end >= end_date:
                    period_end = end_date
                else:
                    period_end = year_end
                
                days_in_period = (period_end - current_date).days
                days_in_year = 366 if calendar.isleap(current_date.year) else 365
                
                interest += notional * rate_decimal * days_in_period / days_in_year
                current_date = date(period_end.year + 1, 1, 1)
            
            return interest
    
    # Default to Actual/365 if convention not recognized
    logger.warning(
        f"Day count convention '{day_count_convention}' not recognized. Using Actual/365.",
        event_type=EventType.SYSTEM_EVENT,
        tags=["quantlib", "cashflow", "warning"],
        entity=my_entity
    )
    return notional * rate_decimal * accrual_days / 365

def is_business_day(check_date: date) -> bool:
    """Check if a given date is a business day (not weekend)."""
    # This is a simplified implementation - in a real system, you'd check
    # against a holiday calendar as well
    return check_date.weekday() < 5  # 0-4 are Monday to Friday

def adjust_for_business_day(check_date: date, convention: str) -> date:
    """
    Adjust a date according to the specified business day convention.
    
    Args:
        check_date: The date to adjust
        convention: The business day convention to apply
            "FOLLOWING": Move to the next business day
            "MODIFIED_FOLLOWING": Move to the next business day unless it's in the next month,
                                 in which case move to the previous business day
            "PRECEDING": Move to the previous business day
            "NONE": No adjustment
    """
    if convention == "Unadjusted" or is_business_day(check_date):
        return check_date
    
    if convention == "Following":
        while not is_business_day(check_date):
            check_date = check_date + timedelta(days=1)
    elif convention == "ModifiedFollowing":
        original_month = check_date.month
        while not is_business_day(check_date):
            check_date = check_date + timedelta(days=1)
            # If we've moved to the next month, go back to previous business day
            if check_date.month != original_month:
                check_date = check_date - timedelta(days=1)
                while not is_business_day(check_date):
                    check_date = check_date - timedelta(days=1)
                break
    elif convention == "Preceding":
        while not is_business_day(check_date):
            check_date = check_date - timedelta(days=1)
    
    return check_date

def add_months(start_date: date, months: int) -> date:
    """Add a number of months to a date, handling month-end logic."""
    years_to_add = months // 12
    months_to_add = months % 12
    
    new_year = start_date.year + years_to_add
    new_month = start_date.month + months_to_add
    
    if new_month > 12:
        new_year += 1
        new_month -= 12
    
    # Handle month-end dates (e.g., Jan 31 + 1 month = Feb 28/29)
    current_day = min(start_date.day, _get_month_end_day(new_year, new_month))
    return date(new_year, new_month, current_day)

def calculate_period_dates(
    effective_date: date,
    termination_date: date,
    frequency_months: int,
    business_day_convention: str
) -> List[Tuple[date, date]]:
    """
    Calculate period start and end dates based on frequency and business day convention.
    
    Returns a list of tuples (start_date, end_date) for each period.
    """
    logger.info(
        "Calculating period dates",
        event_type=EventType.SYSTEM_EVENT,
        tags=["quantlib", "cashflow", "calculation"],
        data={
            "business_day_convention": business_day_convention,
        },
        entity=my_entity
    )
    """
    Calculate period start and end dates based on frequency and business day convention.
    
    Returns a list of tuples (start_date, end_date) for each period.
    """
    if frequency_months <= 0:
        # For one-off payments
        return [(effective_date, termination_date)]
    
    periods = []
    start_date = effective_date
    
    while start_date < termination_date:
        # Calculate the unadjusted end date
        unadjusted_end_date = add_months(start_date, frequency_months)
        
        # Cap the end date at the termination date
        if unadjusted_end_date > termination_date:
            unadjusted_end_date = termination_date
            
        # Adjust the end date according to the business day convention
        adjusted_end_date = adjust_for_business_day(unadjusted_end_date, business_day_convention)
        
        # Add the period
        periods.append((start_date, adjusted_end_date))
        
        # The next period starts after the current end date
        start_date = adjusted_end_date
        
        # If we've reached or passed the termination date, we're done
        if start_date >= termination_date:
            break
    
    return periods

def _get_month_end_day(year: int, month: int) -> int:
    """Get the last day of the specified month."""
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - timedelta(days=1)).day

def calculate_swap_cashflows(
    trade_date: date,
    effective_date: date,
    termination_date: date,
    fixed_leg: Dict[str, Any],
    floating_leg: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Calculate cashflows for a swap based on leg parameters.
    
    Returns a tuple of (fixed_leg_cashflows, floating_leg_cashflows)
    """
    
    try:
        logger.info(
            "Calculating swap cashflows",
            event_type=EventType.SYSTEM_EVENT,
            tags=["quantlib", "cashflow", "calculation"],
            data={
                "trade_date": str(trade_date),
                "effective_date": str(effective_date),
                "termination_date": str(termination_date),
                "fixed_leg": fixed_leg,
                "floating_leg": floating_leg
            },
            entity=my_entity
        )
        
        # Calculate period dates for fixed leg
        fixed_freq_months = fixed_leg["frequency"]["months"]
        fixed_business_day_convention = fixed_leg.get("business_day_convention", "ModifiedFollowing")
        fixed_periods = calculate_period_dates(
            effective_date,
            termination_date,
            fixed_freq_months,
            fixed_business_day_convention
        )
        
        # Calculate period dates for floating leg
        floating_freq_months = floating_leg["frequency"]["months"]
        floating_business_day_convention = floating_leg.get("business_day_convention", "ModifiedFollowing")
        floating_periods = calculate_period_dates(
            effective_date,
            termination_date,
            floating_freq_months,
            floating_business_day_convention
        )
        
        # Get day count conventions
        fixed_day_count = fixed_leg.get("day_count_convention", "Actual/365")
        floating_day_count = floating_leg.get("day_count_convention", "Actual/365")
        
        # Get amortization types (default to BULLET if not specified)
        fixed_amortization_type = fixed_leg.get("amortization_type", "BULLET")
        floating_amortization_type = floating_leg.get("amortization_type", "BULLET")
        
        # Generate fixed leg cashflows
        fixed_cashflows = _generate_cashflows(
            periods=fixed_periods,
            notional=fixed_leg["notional"],
            rate=fixed_leg["rate"],
            spread=0.0,  # No spread for fixed leg
            day_count_convention=fixed_day_count,
            amortization_type=fixed_amortization_type,
            is_floating=False,
            reference_rate_name=None
        )
        
        # Get floating reference rate name if available
        reference_rate_name = floating_leg.get("rate", "LIBOR")
        
        # Generate floating leg cashflows
        floating_cashflows = _generate_cashflows(
            periods=floating_periods,
            notional=floating_leg["notional"],
            rate=None,  # No known rate for floating leg
            spread=floating_leg.get("spread", 0),
            day_count_convention=floating_day_count,
            amortization_type=floating_amortization_type,
            is_floating=True,
            reference_rate_name=reference_rate_name
        )
        
        logger.info(
            "Swap cashflows calculated successfully",
            event_type=EventType.SYSTEM_EVENT,
            data={
                "fixed_cashflows": len(fixed_cashflows),
                "floating_cashflows": len(floating_cashflows)
            },
            tags=["quantlib", "cashflow", "success"],
            entity=my_entity
        )
        
        return fixed_cashflows, floating_cashflows
    
    except Exception as e:
        logger.log_exception(
            e,
            message="Error calculating swap cashflows",
            level=LogLevel.ERROR,
            tags=["quantlib", "cashflow", "error"],
            entity=my_entity
        )
        raise

def _generate_cashflows(
    periods: List[Tuple[date, date]],
    notional: float,
    rate: Optional[float],
    spread: float = 0.0,
    day_count_convention: str = "Actual/365",
    amortization_type: str = "BULLET",
    is_floating: bool = False,
    reference_rate_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Generate cashflows for any leg type (fixed or floating).
    
    Args:
        periods: List of (start_date, end_date) tuples for each period
        notional: The notional amount
        rate: The interest rate as a percentage (e.g., 2.215 for 2.215%). Set to None for floating legs.
        spread: The spread over the reference rate for floating legs
        day_count_convention: The day count convention to use
        amortization_type: The amortization schedule type (BULLET or LINEAR)
        is_floating: Whether this is a floating rate leg
        reference_rate_name: Name of the reference rate for floating legs
        
    Returns:
        List of cashflow dictionaries
    """
    cashflows = []
    remaining_notional = notional
    payment_count = len(periods)
    
    for i, (start_date, end_date) in enumerate(periods):
        # Calculate accrual days
        accrual_days = (end_date - start_date).days
        
        # Calculate amortization based on type
        if amortization_type == "LINEAR":
            # Distribute amortization equally across periods
            amortization_per_period = notional / payment_count if payment_count > 0 else notional
            if i == payment_count - 1:  # Last payment
                amortization = remaining_notional  # Handle rounding errors
            else:
                amortization = amortization_per_period
        else:  # Default is BULLET
            # No amortization until final payment
            if i == payment_count - 1:  # Last payment
                amortization = remaining_notional
            else:
                amortization = 0
        
        # Calculate interest differently based on leg type
        if is_floating:
            # For floating legs, interest will be determined later
            # Display reference rate name + spread
            rate_display = f"{reference_rate_name}{'+' + str(spread) if spread > 0 else ''}"
            interest = "TBD"  # To be determined
        else:
            # For fixed legs, calculate interest based on fixed rate
            interest = calculate_interest(remaining_notional, rate, start_date, end_date, day_count_convention)
            rate_display = rate
        
        # Create cashflow entry
        cashflow = {
            "Start Date": start_date.strftime("%Y-%m-%d"),
            "End Date": end_date.strftime("%Y-%m-%d"),
            "Rate": rate_display,
            "Spread": spread,
            "Notional": remaining_notional,
            "Amortization": amortization,
            "Interest": interest
        }
        
        cashflows.append(cashflow)
        
        # Update for next period
        remaining_notional -= amortization
    
    return cashflows