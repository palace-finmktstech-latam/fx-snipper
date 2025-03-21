# backend/app/swap_calculator/constants.py
from enum import Enum

# Day count conventions
class DayCountConvention(str, Enum):
    ACT_360 = "Actual/360"
    ACT_365 = "Actual/365"
    THIRTY_360 = "30/360"
    THIRTY_E_360 = "30E/360"

# Business day conventions
class BusinessDayConvention(str, Enum):
    FOLLOWING = "Following"
    MODIFIED_FOLLOWING = "ModifiedFollowing"
    PRECEDING = "Preceding"
    MODIFIED_PRECEDING = "ModifiedPreceding"
    UNADJUSTED = "Unadjusted"

# Payment frequencies
class PaymentFrequency(str, Enum):
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    SEMIANNUAL = "Semiannual"
    ANNUAL = "Annual"
    ONCE = "Once"

# Mapping of frequency strings to month periods
FREQUENCY_MONTHS = {
    PaymentFrequency.DAILY: 0,
    PaymentFrequency.WEEKLY: 0,
    PaymentFrequency.MONTHLY: 1,
    PaymentFrequency.QUARTERLY: 3,
    PaymentFrequency.SEMIANNUAL: 6,
    PaymentFrequency.ANNUAL: 12,
    PaymentFrequency.ONCE: 0,
}

# Amortization types
class AmortizationType(str, Enum):
    BULLET = "BULLET"  # Principal paid at maturity
    LINEAR = "LINEAR"  # Equal principal payments