from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
from app.main import logger
from core_logging.client import EventType, LogLevel

from app.services.ai_service import AIService
from app.services.swap_service import SwapParamTransformer, load_ql_parameters, create_swap_cashflows, transform_output

router = APIRouter()

# Initialize service
ai_service = AIService()

# Get parameters from environment variables
my_entity = os.environ.get('MY_ENTITY')

# Define request models
class PersonCompanyPair(BaseModel):
    person: str
    company: str

class ProcessSwapRequest(BaseModel):
    input_type: str
    input_image: Optional[str] = None
    input_text: Optional[str] = None
    ai_provider: str = "OpenAI"
    user_name: str
    user_entity: str
    person_company_pairs: List[PersonCompanyPair] = []

@router.post("/process-swap")
async def process_swap(request: ProcessSwapRequest):
    try:
        logger.info(
            "Received swap processing request",
            event_type=EventType.INTEGRATION,
            entity=my_entity,
            user_id=request.user_name,
            data={
                "input_type": request.input_type,
                "ai_provider": request.ai_provider
            },
            tags=["api", "process-swap", "request"]
        )
        
        # Update AI service with user info
        ai_service.update_user_info(request.user_name, request.user_entity)
        
        # Convert Pydantic models to dict for compatibility
        person_company_pairs = [pair.dict() for pair in request.person_company_pairs]
        ai_service.update_person_company_pairs(person_company_pairs)
        
        # Process based on input type
        if request.input_type == 'image':
            if not request.input_image:
                error_msg = 'No image data provided'
                logger.warning(
                    error_msg,
                    event_type=EventType.INTEGRATION,
                    entity=my_entity,
                    user_id=request.user_name,
                    tags=["api", "validation", "error"]
                )
                raise HTTPException(status_code=400, detail=error_msg)
            
            logger.info(
                "Processing image for text extraction",
                event_type=EventType.SYSTEM_EVENT,
                entity=my_entity,
                user_id=request.user_name,
                tags=["api", "image", "extraction"]
            )
            extracted_text = ai_service.extract_text(request.input_image)
                
        elif request.input_type == 'text':
            if not request.input_text:
                error_msg = 'No input text provided'
                logger.warning(
                    error_msg,
                    event_type=EventType.INTEGRATION,
                    entity=my_entity,
                    user_id=request.user_name,
                    tags=["api", "validation", "error"]
                )
                raise HTTPException(status_code=400, detail=error_msg)
                
            logger.info(
                "Using provided text input",
                event_type=EventType.SYSTEM_EVENT,
                entity=my_entity,
                user_id=request.user_name,
                data={"text_length": len(request.input_text)},
                tags=["api", "text", "input"]
            )
            extracted_text = request.input_text
            
        else:
            error_msg = 'Invalid input type'
            logger.warning(
                error_msg,
                event_type=EventType.INTEGRATION,
                entity=my_entity,
                user_id=request.user_name,
                data={"input_type": request.input_type},
                tags=["api", "validation", "error"]
            )
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Process text with AI
        logger.info(
            "Processing text with AI",
            event_type=EventType.TRANSACTION,
            entity=my_entity,
            user_id=request.user_name,
            data={"provider": request.ai_provider},
            tags=["api", "ai", "processing"]
        )
        
        raw_json_str = ai_service.process_text(extracted_text, request.ai_provider)
        trade_json = json.loads(raw_json_str)
        
        if "TradeSummary" not in trade_json:
            error_msg = 'Invalid JSON structure from AI processing'
            logger.error(
                error_msg,
                event_type=EventType.SYSTEM_EVENT,
                entity=my_entity,
                user_id=request.user_name,
                data={"received_json": trade_json},
                tags=["api", "ai", "error", "json"]
            )
            raise HTTPException(status_code=500, detail=error_msg)

        # Transform and calculate cashflows
        transformer = SwapParamTransformer()
        intermediate_params = transformer.transform_json(trade_json)
        params = load_ql_parameters(intermediate_params)
        leg1, leg2 = create_swap_cashflows(**params)
        output_data = transform_output(trade_json, leg1, leg2)
        
        # Log success
        logger.info(
            "Swap processing completed successfully",
            event_type=EventType.TRANSACTION,
            entity=my_entity,
            user_id=request.user_name,
            tags=["api", "process-swap", "success"]
        )
        
        return output_data
        
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.log_exception(
                e,
                message="Unexpected error in process_swap endpoint",
                level=LogLevel.CRITICAL,
                tags=["api", "error", "fatal"],
                entity=my_entity
            )
            raise HTTPException(status_code=500, detail=str(e))
        raise