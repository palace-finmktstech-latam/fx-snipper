import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging
import json
from openai import OpenAI
import anthropic
import google.generativeai as gemini
from PIL import Image
import base64
import io

from app.config import settings
from app.main import logger
from core_logging.client import EventType, LogLevel

# Get parameters from environment variables
my_entity = os.environ.get('MY_ENTITY')

class AIService:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.anthropic_api_key = settings.ANTHROPIC_API_KEY
        self.google_api_key = settings.GOOGLE_API_KEY
        
        self.user_name = None
        self.user_entity = None
        self.person_company_pairs = []
        
        # Initialize clients
        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
        else:
            self.openai_client = None
            
        if self.anthropic_api_key:
            self.anthropic_client = anthropic.Client(api_key=self.anthropic_api_key)
        else:
            self.anthropic_client = None
            
        if self.google_api_key:
            gemini.configure(api_key=self.google_api_key)
        
    def update_user_info(self, user_name: str, user_entity: str):
        """Update the user information used in prompts."""
        self.user_name = user_name
        self.user_entity = user_entity

    def update_person_company_pairs(self, pairs: List[Dict[str, str]]):
        """Update the person-company pairs mapping."""
        self.person_company_pairs = pairs
    
    def extract_text(self, image_input: str) -> str:
        """Extract text from an image using OpenAI's Vision API."""
        EXTRACTION_PROMPT = "Extract the text from this image."

        if not self.openai_client:
            logger.error(
                "OpenAI API key is not set",
                event_type=EventType.SYSTEM_EVENT,
                user_id=self.user_name,
                tags=["api", "extract", "error", "config"],
                entity=my_entity
            )
            raise ValueError("OpenAI API key is not set")

        try:
            logger.info(
                "Starting text extraction from image",
                event_type=EventType.SYSTEM_EVENT,
                user_id=self.user_name,
                tags=["api", "extract", "image"],
                entity=my_entity
            )
            
            # If image_input is already base64, use it directly
            if isinstance(image_input, str) and image_input.startswith('iVBOR'):
                base64_image = image_input
            else:
                logger.error(
                    "Invalid image format provided",
                    event_type=EventType.SYSTEM_EVENT,
                    user_id=self.user_name,
                    entity=my_entity,
                    tags=["api", "extract", "error", "format"]
                )
                raise ValueError("Invalid image input format")

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-2024-11-20",
                messages=[
                    {
                        "role": "system",
                        "content": EXTRACTION_PROMPT
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": EXTRACTION_PROMPT
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0
            )
            
            logger.info(
                "Successfully extracted text from image",
                event_type=EventType.SYSTEM_EVENT,
                user_id=self.user_name,
                entity=my_entity,
                data={"text_length": len(response.choices[0].message.content)},
                tags=["api", "extract", "success"]
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.log_exception(
                e,
                message="Failed to extract text from image",
                user_id=self.user_name,
                entity=my_entity,
                level=LogLevel.ERROR,
                tags=["api", "extract", "error"]
            )
            raise Exception(f"Error extracting text from image: {str(e)}")
    
    def get_extraction_prompt(self, text_to_process: str) -> str:
        """Generate the extraction prompt with current user information."""
        if not self.user_name or not self.user_entity:
            logger.error(
                "User name and entity must be set before processing text",
                event_type=EventType.SYSTEM_EVENT,
                tags=["api", "prompt", "error", "config"],
                entity=my_entity
            )
            raise ValueError("User name and entity must be set before processing text")

        system_date = datetime.today().strftime('%d-%m-%Y')
        
        # Generate the person-company mapping text
        person_company_text = ""
        mappings = [f"{pair['person']} works for a company named {pair['company']}"
                    for pair in self.person_company_pairs]
        person_company_text = "\n        ".join(mappings)

        return f"""
        Today's date is {system_date}.

        In the extracted text below I am {self.user_name}. I work for a company named {self.user_entity}.

        {person_company_text}
        
        I have asked for bid and offer prices for the fixed leg of an Interest Rate Swap.
        
        Another part in the conversation has providing me with bid and offer prices for the fixed leg of an Interest Rate Swap, as denoted by two numbers separated by a slash. The other part has accepted a price.
        
        Prices quoted and accepted at the end of the chat are far more likely to be correct than those at the beginning.

        Tell me who (person and company name) has provided the bid and offer prices.

        Tell me who (person and company name) has accepted the price and whether it was the bid price or the offer price.

        If the first price (bid) is the accepted one, then the price maker is paying the fixed rate and the price taker is paying the floating rate.
        If the second price (offer) is the accepted one, then the price taker is paying the fixed rate and the price maker is paying the floating rate.

        Tell me who (person and company name) is paying the fixed rate (and what it is) and who (person and company name) is paying the floating rate.
        
        Prices quoted and accepted at the end of the chat are far more likely to be correct than those at the beginning.

        Tell me the Start Lag of the trade. This is usually represented as T0, T+1, T+2, and indicates how many working days after Trade Date the Effective Date is. 
        If you do not specifically find this data point, default to 0. Store as an integer.
        
        Tell me the maturity of the trade, store as number of years or as a specific date (DD-MM-YYYY).
        This could be expressed in the chat as something like 1.5Y (1.5 years) or 18m (1.5 years) or 1Y6M (1.5 years).
        It could also be expressed in the chat as a specific date, usually preceded by the word "vcto", "vencimiento", "mat" or "maturity".

        Tell me the currency of each leg, as an ISO code.

        Tell me the notional amount of each leg. This can usually be found at the start of the conversation, as this vital for the quote that is being requested.
        There are a number of conventions used to abbreviate amounts here. For example MM represents millions. K represents thousands. Write the full number, do not abbreviate.

        Tell me the cashflow dates of each leg. This should be stored as a concatenated, comma-separated string of all the cashflow dates mentioned in the chat. Make sure you distinguish between the number 1 and the number 7. Do not miss any.

        Tell me the coupon frequency for each leg. This may or may not be explicitly mentioned. If it is not
        explicitly mentioned, you can try inferring it from the series of cashflow dates if mentioned (e.g., if dates are spaced by one year, set it to "Annually").
        Other expected values might be one of the following:
        "Monthly," "Quarterly," "Semi-Annually," "Annually," or "One-Off."
        If you cannot tie a coupon frequency to a specific leg, default to "Semi-Annually".

        Tell me the cashflow percentages of each leg. This should be stored as a concatenated, comma-separated string of all the cashflow percentages (summing 100), usually next to the cashflow dates in a table forma.

        Tell me the Date Basis for each leg. This is likely one of the following:
        "Actual/360," "Actual/365," or "30/360."
        This could be referred to as "Pata fija" (Fixed Leg) or "Pata flotante" (Floating Leg) and then the date basis after that.
        If you cannot tie a Date Basis to a specific leg, default to "Actual/360".

        Tell me the Business Day Adjustment for each leg. This is likely one of the following:
        "No Adjustment," "Modified Following," "Following," "Modified Preceding," or "Preceding."
        If you cannot tie a Business Date Adjustment to a specific leg, default to "Modified Following."

        Also, tell me what the floating rate reference is in this chat. Some possible values and how they should be represented in the output are as follows:
        "UFCAM" → "ICP-CLP"
        "CLPCAM" → "ICP-CLP"
        "CLF/CAM" → "ICP-CLP"
        "SPC" → "ICP-CLP"
        "SOFR" → "USD-SOFR-RATE"
        "SOFR Rate" → "USD-SOFR-RATE" (If another variable rate reference is present, extract it as-is for now.)

        Here is the extracted text:

        {text_to_process}

        Then structure the extracted information into JSON with the following schema:
        {{
            "TradeSummary": {{
                "Trade Date": "Today's Date (DD-MM-YYYY)",
                "Start Lag": "Numeric Value",
                "Maturity": "String",
                "Price Maker": {{
                    "Name": "String",
                    "Company": "String"
                }},
                "Price Taker": {{
                    "Name": "String",
                    "Company": "String"
                }},
                "Prices": {{
                    "Bid": "Numeric Value",
                    "Offer": "Numeric Value"
                }},
                "Accepted Price": "Numeric Value",
                "Accepted Side": "String (Bid or Offer)",
                "Leg 1 Payer": {{
                    "Leg Type": "String (Fixed or Floating)",
                    "Name": "String",
                    "Company": "String",
                    "Rate": "String",
                    "Leg Currency": "ISO Code",
                    "Notional Amount": "Numeric Value",
                    "Date Basis": "String",
                    "Business Date Adjustment": "String",
                    "Coupon Frequency": "String",
                    "Cashflow Dates": "String",
                    "Cashflow Percentages": "String"
                }},
                "Leg 2 Payer": {{
                    "Leg Type": "String (Fixed or Floating)",
                    "Name": "String",
                    "Company": "String",
                    "Rate": "String",
                    "Leg Currency": "ISO Code",
                    "Notional Amount": "Numeric Value",
                    "Date Basis": "String",
                    "Business Date Adjustment": "String",
                    "Coupon Frequency": "String",
                    "Cashflow Dates": "String",
                    "Cashflow Percentages": "String"
                }}
            }}
        }}

        DO NOT include any markdown in the JSON output, such as ```json or ```

        Important Notes:

        If any data point is missing in the chat, label it as "Not Mentioned" in the JSON output. DO NOT GUESS.
        Ensure proper handling of shorthand, jargon, and implied data where necessary.
        Maintain the specified JSON structure and format.

        Suggest reading from the end of the conversation and working back. This is because data points may change 
        as a result of the conversation.

        If you are unsure on any data point, please leave it blank. Do not guess.

        Before finishing, double check which part is paying which leg. 
        Remember, if the first price (bid) is the accepted one, then the price maker is paying the fixed rate and the price taker is paying the floating rate.
        If the second price (offer) is the accepted one, then the price taker is paying the fixed rate and the price maker is paying the floating rate.
        If you realise you've made a mistake, switch them around.

        Also, before finishing, remove any markdown in the JSON output, such as ```json or ```

        DO NOT include any markdown in the JSON output, such as ```json or ```
        """
    
    def process_text(self, extracted_text: str, ai_provider: str = "OpenAI") -> str:
        """Process the extracted text to generate structured JSON output."""
        EXTRACTION_PROMPT = self.get_extraction_prompt(extracted_text)

        try:
            logger.info(
                f"Processing text with {ai_provider} AI",
                event_type=EventType.TRANSACTION,
                user_id=self.user_name,
                entity=my_entity,
                data={"text_length": len(extracted_text)},
                tags=["ai", "process", ai_provider.lower()]
            )
            
            if ai_provider == "OpenAI":
                if not self.openai_client:
                    logger.error(
                        "OpenAI API key is not set",
                        event_type=EventType.SYSTEM_EVENT,
                        user_id=self.user_name,
                        entity=my_entity,
                        tags=["ai", "process", "error", "config"]
                    )
                    raise ValueError("OpenAI API key is not set.")

                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-2024-11-20",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert in interpreting Bloomberg chat messages between Swap traders. You will study chat snippets and extract the key trade details from the chat, in JSON format. Do not put Markdown around the extracted JSON. Only provide the JSON itself, I don't want any complementary text at all."
                        },
                        {
                            "role": "user",
                            "content": EXTRACTION_PROMPT
                        }
                    ],
                    max_tokens=1000,
                    temperature=0
                )
                
                result = response.choices[0].message.content

            elif ai_provider == "Anthropic":
                if not self.anthropic_client:
                    logger.error(
                        "Anthropic API key is not set",
                        event_type=EventType.SYSTEM_EVENT,
                        user_id=self.user_name,
                        entity=my_entity,
                        tags=["ai", "process", "error", "config"]
                    )
                    raise ValueError("Anthropic API key is not set.")
                
                response = self.anthropic_client.messages.create(
                    model="claude-3-7-sonnet-20250219",
                    system="You are an expert in interpreting Bloomberg chat messages between Swap traders. You will study chat snippets and extract the key trade details from the chat, in JSON format. Do not put Markdown around the extracted JSON. Only provide the JSON itself, I don't want any complementary text at all.",
                    messages=[{
                        "role": "user",
                        "content": EXTRACTION_PROMPT
                    }],
                    max_tokens=2000,
                    temperature=0
                )
                
                result = response.content[0].text
            
            elif ai_provider == "Google":
                if not self.google_api_key:
                    logger.error(
                        "Google API key is not set",
                        event_type=EventType.SYSTEM_EVENT,
                        user_id=self.user_name,
                        entity=my_entity,
                        tags=["ai", "process", "error", "config"]
                    )
                    raise ValueError("Google API key is not set")
                
                try:
                    generation_config = {
                        "temperature": 0,
                        "top_p": 1,
                        "top_k": 1,
                        "max_output_tokens": 1000,
                        "response_mime_type": "text/plain",
                    }
                    
                    model = gemini.GenerativeModel(
                        model_name="gemini-1.5-pro",
                        generation_config=generation_config,
                        system_instruction="You are an expert in interpreting Bloomberg chat messages between Swap traders. You will study chat snippets and extract the key trade details from the chat, in JSON format. Do not put Markdown around the extracted JSON. Only provide the JSON itself, I don't want any complementary text at all, or markdown."
                    )
                    
                    response = model.generate_content(EXTRACTION_PROMPT)
                    result = response.text
                    
                except Exception as e:
                    logger.log_exception(
                        e,
                        message=f"Error with Google API during processing",
                        user_id=self.user_name,
                        entity=my_,
                        level=LogLevel.ERROR,
                        tags=["ai", "process", "error", "google"]
                    )
                    raise Exception(f"Error with Google API: {str(e)}")

            else:
                logger.error(
                    f"Invalid AI provider specified: {ai_provider}",
                    event_type=EventType.SYSTEM_EVENT,
                    user_id=self.user_name,
                    entity=my_entity,
                    tags=["ai", "process", "error", "config"]
                )
                raise ValueError("Invalid AIProvider specified. Use 'OpenAI', 'Anthropic' or 'Google'.")
            
            logger.info(
                f"Successfully processed text with {ai_provider}",
                event_type=EventType.TRANSACTION,
                user_id=self.user_name,
                entity=my_entity,
                data={"result_length": len(result)},
                tags=["ai", "process", "success", ai_provider.lower()]
            )
            
            return result

        except Exception as e:
            logger.log_exception(
                e,
                message=f"Error processing text with {ai_provider} API",
                user_id=self.user_name,
                entity=my_entity,
                level=LogLevel.ERROR,
                tags=["ai", "process", "error"]
            )
            raise Exception(f"Error processing text with {ai_provider} API: {str(e)}")