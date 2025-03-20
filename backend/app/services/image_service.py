import base64
import os
import io
from PIL import Image
from pathlib import Path
from typing import Optional, List, Dict
import logging
from app.main import logger
from core_logging.client import EventType, LogLevel

# Get parameters from environment variables
my_entity = os.environ.get('MY_ENTITY')

class ImageService:
    def __init__(self):
        pass
        
    def encode_image(self, image_path: str) -> str:
        """Encode an image file to base64 string."""
        try:
            logger.info(
                f"Encoding image from path: {image_path}",
                event_type=EventType.SYSTEM_EVENT,
                tags=["image", "encode", "file"],
                entity=my_entity
            )
            
            path = Path(image_path)

            if not path.exists():
                logger.error(
                    f"Image file not found: {image_path}",
                    event_type=EventType.SYSTEM_EVENT,
                    tags=["image", "encode", "error", "file-not-found"],
                    entity=my_entity
                )
                raise FileNotFoundError(f"Image file not found: {image_path}")

            with open(path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode('utf-8')
                
            logger.info(
                "Image encoded successfully",
                event_type=EventType.SYSTEM_EVENT,
                data={"encoded_length": len(encoded)},
                tags=["image", "encode", "success"],
                entity=my_entity
            )
            
            return encoded
        except Exception as e:
            if not isinstance(e, FileNotFoundError):
                logger.log_exception(
                    e,
                    message=f"Error encoding image from path: {image_path}",
                    level=LogLevel.ERROR,
                    tags=["image", "encode", "error"],
                    entity=my_entity
                )
            raise

    def encode_pil_image(self, pil_image: Image.Image) -> str:
        """Encode a PIL Image object to base64."""
        try:
            logger.info(
                "Encoding PIL image",
                event_type=EventType.SYSTEM_EVENT,
                data={"image_size": f"{pil_image.width}x{pil_image.height}"},
                tags=["image", "encode", "pil"],
                entity=my_entity
            )
            
            buffered = io.BytesIO()
            pil_image.save(buffered, format="PNG")
            encoded = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            logger.info(
                "PIL image encoded successfully",
                event_type=EventType.SYSTEM_EVENT,
                data={"encoded_length": len(encoded)},
                tags=["image", "encode", "success"],
                entity=my_entity
            )
            
            return encoded
        except Exception as e:
            logger.log_exception(
                e,
                message="Error encoding PIL image",
                level=LogLevel.ERROR,
                tags=["image", "encode", "error"],
                entity=my_entity
            )
            raise