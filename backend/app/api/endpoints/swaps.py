from fastapi import APIRouter, HTTPException, Body, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import logging
from fastapi.responses import JSONResponse

from app.services.ai_service import AIService
from app.services.swap_service import SwapParamTransformer, load_ql_parameters, create_swap_cashflows, transform_output

router = APIRouter()

# Initialize service
ai_service = AIService()

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
        # Update AI service with user info
        ai_service.update_user_info(request.user_name, request.user_entity)
        
        # Convert Pydantic models to dict for compatibility
        person_company_pairs = [pair.dict() for pair in request.person_company_pairs]
        ai_service.update_person_company_pairs(person_company_pairs)
        
        # Process based on input type
        if request.input_type == 'image':
            if not request.input_image:
                raise HTTPException(status_code=400, detail="No image data provided")
            
            extracted_text = ai_service.extract_text(request.input_image)
            
        elif request.input_type == 'text':
            if not request.input_text:
                raise HTTPException(status_code=400, detail="No input text provided")
                
            extracted_text = request.input_text
            
        else:
            raise HTTPException(status_code=400, detail="Invalid input type")
        
        # Process text with AI
        raw_json_str = ai_service.process_text(extracted_text, request.ai_provider)
        trade_json = json.loads(raw_json_str)
        
        if "TradeSummary" not in trade_json:
            raise HTTPException(
                status_code=500, 
                detail="Invalid JSON structure from AI processing"
            )
        
        # Transform and calculate cashflows
        transformer = SwapParamTransformer()
        intermediate_params = transformer.transform_json(trade_json)
        params = load_ql_parameters(intermediate_params)
        leg1, leg2 = create_swap_cashflows(**params)
        
        # Transform to required format
        output_data = transform_output(trade_json, leg1, leg2)
        
        return output_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))