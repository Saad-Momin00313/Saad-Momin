from sqlalchemy.orm import Session
from models.inventory import InventoryItem
from models.expiration import ExpirationTracker, ExpirationStatus
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from core.logger import logger
from sqlalchemy import text
from ai.gemini_service import GeminiService

class InventoryService:
    def __init__(self, db: Session):
        self.db = db
        self.gemini_service = GeminiService()
    
    async def _guess_category(self, item_name: str) -> str:
        """Use AI to guess item category based on name"""
        try:
            prompt = f"""
            You are a food category classification AI. Classify this food item into exactly one category:
            Item: {item_name}
            
            Return ONLY a JSON response in this exact format:
            {{
                "category": "one of: dairy, produce, meat, grains, beverages, spices, snacks, condiments, canned, frozen, baking, other",
                "confidence": confidence level as a number between 0 and 1,
                "reasoning": "Brief explanation of the classification"
            }}
            """
            
            response = await self.gemini_service.generate_json_content(prompt)
            if response and "category" in response:
                return response["category"].lower()
            
            # Fallback to 'other' if AI fails
            logger.warning(f"AI category prediction failed for {item_name}, falling back to 'other'")
            return "other"
            
        except Exception as e:
            logger.error(f"Error in AI category prediction for {item_name}: {str(e)}")
            return "other"