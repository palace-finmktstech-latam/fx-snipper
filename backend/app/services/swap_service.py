from datetime import datetime, date, timedelta
from typing import Dict, List, Union, Any, Tuple, Optional
import math
import os
from app.main import logger
from core_logging.client import EventType, LogLevel
from app.swap_calculator.adapters import (
    prepare_swap_parameters,
    parse_date_basis,
    parse_business_day_convention,
    parse_frequency,
    parse_maturity,
    parse_rate,
    get_month_end_day
)
from app.swap_calculator.calculators import calculate_swap_cashflows

# Get parameters from environment variables
my_entity = os.environ.get('MY_ENTITY')

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
    return f"{rate:.3f}%"

def transform_output(trade_json: dict, leg1_cashflows: list, leg2_cashflows: list) -> dict:
    """Transform the API output to match the required format."""
    try:
        logger.info(
            "Transforming output data",
            event_type=EventType.SYSTEM_EVENT,
            tags=["swap", "transform", "output"],
            data={"fixed_rate": trade_json["TradeSummary"]["Leg 1 Payer"]["Rate"],
                  "floating_rate": trade_json["TradeSummary"]["Leg 2 Payer"]["Rate"]},
            entity=my_entity
        )
        
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

        logger.info(
            "Output transformation completed",
            event_type=EventType.SYSTEM_EVENT,
            data={"leg1_flows": len(leg1_cashflows), "leg2_flows": len(leg2_cashflows)},
            tags=["swap", "transform", "success"],
            entity=my_entity
        )
        
        return {
            "tradeInfo": trade_info,
            "legs": legs
        }
    except Exception as e:
        logger.log_exception(
            e,
            message="Error transforming output data",
            level=LogLevel.ERROR,
            tags=["swap", "transform", "error"],
            entity=my_entity
        )
        raise

class SwapParamTransformer:
    def __init__(self):
        pass
        
    def transform_json(self, trade_json: Dict[str, Any]) -> Dict[str, Any]:
        """Transform the AI-extracted JSON into a format suitable for QuantLib."""
        try:
            logger.info(
                "Transforming trade JSON parameters",
                event_type=EventType.SYSTEM_EVENT,
                tags=["swap", "transform", "parameters"],
                entity=my_entity
            )
            
            # Use the prepare_swap_parameters function from adapters.py
            params = prepare_swap_parameters(trade_json)
            
            logger.info(
                "JSON transformation completed successfully",
                event_type=EventType.SYSTEM_EVENT,
                data={
                    "trade_date": params["trade_date"].isoformat(),
                    "effective_date": params["effective_date"].isoformat(),
                    "termination_date": params["termination_date"].isoformat(),
                },
                tags=["swap", "transform", "success"],
                entity=my_entity
            )
            
            return params
            
        except Exception as e:
            logger.log_exception(
                e,
                message="Error transforming trade JSON",
                level=LogLevel.ERROR,
                tags=["swap", "transform", "error"],
                entity=my_entity
            )
            raise

def load_ql_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert transformed parameters into QuantLib-specific parameters."""
    try:
        logger.info(
            "Loading QuantLib parameters",
            event_type=EventType.SYSTEM_EVENT,
            tags=["swap", "quantlib", "parameters"],
            entity=my_entity
        )
        
        # All we need to do is pass through the parameters already transformed
        # This function now mainly serves as a logging point and potential
        # future validation layer
        
        logger.info(
            "QuantLib parameters loaded successfully",
            event_type=EventType.SYSTEM_EVENT,
            data={
                "trade_date": params["trade_date"].isoformat(),
                "effective_date": params["effective_date"].isoformat(),
                "termination_date": params["termination_date"].isoformat(),
            },
            tags=["swap", "quantlib", "success"],
            entity=my_entity
        )
        
        return params
        
    except Exception as e:
        logger.log_exception(
            e,
            message="Error loading QuantLib parameters",
            level=LogLevel.ERROR,
            tags=["swap", "quantlib", "error"],
            entity=my_entity
        )
        raise

def create_swap_cashflows(**kwargs) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Generate cashflow schedules for both legs of a swap."""
    try:
        logger.info(
            "Creating swap cashflows",
            event_type=EventType.SYSTEM_EVENT,
            tags=["swap", "cashflow", "calculation"],
            data={"fixed_leg": kwargs["fixed_leg"], "floating_leg": kwargs["floating_leg"]},
            entity=my_entity
        )
        
        # Delegate to the calculator module
        return calculate_swap_cashflows(
            kwargs["trade_date"],
            kwargs["effective_date"],
            kwargs["termination_date"],
            kwargs["fixed_leg"],
            kwargs["floating_leg"]
        )
    except Exception as e:
        logger.log_exception(
            e,
            message="Error creating swap cashflows",
            level=LogLevel.ERROR,
            tags=["swap", "cashflow", "error"],
            entity=my_entity
        )
        raise