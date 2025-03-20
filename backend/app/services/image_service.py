import base64
import os
import io
from PIL import Image
from pathlib import Path
from typing import Optional, List, Dict
import logging

class ImageService:
    def __init__(self):
        pass
        
    def encode_image(self, image_path: str) -> str:
        """Encode an image file to base64 string."""
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def encode_pil_image(self, pil_image: Image.Image) -> str:
        """Encode a PIL Image object to base64."""
        buffered = io.BytesIO()
        pil_image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode('utf-8')