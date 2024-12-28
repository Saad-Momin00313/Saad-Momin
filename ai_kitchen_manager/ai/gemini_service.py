import google.generativeai as genai
from typing import Optional, Dict, Any, Union
import os
import json
import re
from core.logger import logger

class GeminiService:
    def __init__(self):
        """Initialize the Gemini service with API key and model configuration"""
        try:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not set")
            
            # Configure the Gemini API
            genai.configure(api_key=api_key)
            
            # Initialize the model
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Create a wrapper for backward compatibility
            self.chat_model = self._create_chat_model_wrapper()
            
            # Set default parameters for balanced JSON generation
            self.temperature = 0.7  # Higher temperature for more creative recommendations
            self.top_p = 0.9
            self.top_k = 40
            
            logger.info("GeminiService initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing GeminiService: {str(e)}")
            raise
    
    def _create_chat_model_wrapper(self):
        """Create a wrapper for backward compatibility with chat_model attribute"""
        class ChatModelWrapper:
            def __init__(self, parent):
                self.parent = parent
            
            def generate_content(self, prompt, **kwargs):
                # Use the parent's model but with JSON cleaning
                response = self.parent.model.generate_content(prompt, **kwargs)
                if not response or not response.text:
                    return response
                
                # Create a new response object with cleaned text for JSON prompts
                if '"' in prompt or '{' in prompt or '[' in prompt:
                    cleaned_text = self.parent._clean_json_text(response.text)
                    validated_text = self.parent._validate_json_structure(cleaned_text)
                    # Create a new response-like object
                    class CleanedResponse:
                        def __init__(self, text):
                            self.text = text
                    return CleanedResponse(validated_text)
                return response
        
        return ChatModelWrapper(self)
    
    def configure_model(self, temperature: float = 0.1, top_p: float = 0.95, top_k: int = 40):
        """Configure model parameters"""
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
    
    def _clean_json_text(self, text: str) -> str:
        """Clean and format JSON text to ensure valid structure"""
        try:
            # Remove any non-JSON content before the first { and after the last }
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                text = text[json_start:json_end]
            
            # Remove trailing commas inside arrays and objects
            text = re.sub(r',(\s*[}\]])', r'\1', text)
            
            # Try to parse and re-serialize to ensure valid JSON
            try:
                parsed = json.loads(text)
                # Ensure meal plan structure is complete
                if "meal_plan" in parsed and "days" in parsed["meal_plan"]:
                    for day in parsed["meal_plan"]["days"]:
                        if "meals" in day:
                            for meal in day["meals"]:
                                # Ensure missing_ingredients is a list
                                if "missing_ingredients" not in meal:
                                    meal["missing_ingredients"] = []
                                elif not isinstance(meal["missing_ingredients"], list):
                                    meal["missing_ingredients"] = []
                                # Ensure inventory_match is a number
                                if "inventory_match" not in meal:
                                    meal["inventory_match"] = 100
                                elif not isinstance(meal["inventory_match"], (int, float)):
                                    meal["inventory_match"] = 100
                return json.dumps(parsed, separators=(',', ':'))
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                logger.error(f"Failed JSON text: {text}")
                return text
            
        except Exception as e:
            logger.error(f"Error cleaning JSON text: {str(e)}")
            return text
    
    def _fix_truncated_meal_plan(self, text: str) -> str:
        """Fix a truncated meal plan by completing the structure"""
        try:
            # First try to parse the JSON
            try:
                json_data = json.loads(text)
                if "meal_plan" in json_data and "days" in json_data["meal_plan"]:
                    return text
            except json.JSONDecodeError:
                pass
            
            # Find all complete days
            complete_days = []
            day_starts = [m.start() for m in re.finditer(r'"day":\s*\d+', text)]
            
            for i, start in enumerate(day_starts):
                try:
                    # Find the start of the next day or end of text
                    next_start = day_starts[i + 1] if i + 1 < len(day_starts) else len(text)
                    day_text = text[start:next_start]
                    
                    # Check if this day has complete meals
                    meal_count = len(re.findall(r'"type":\s*"(?:breakfast|lunch|dinner)"', day_text))
                    if meal_count != 3:
                        continue
                    
                    # Check for complete ingredients sections
                    ingredients_starts = [m.start() for m in re.finditer(r'"ingredients":\s*\[', day_text)]
                    if len(ingredients_starts) != 3:
                        continue
                    
                    # Ensure each ingredients section is complete
                    is_complete = True
                    for ing_start in ingredients_starts:
                        # Find the matching closing bracket
                        bracket_count = 1
                        for j, char in enumerate(day_text[ing_start + len('"ingredients": ['):], ing_start + len('"ingredients": [')):
                            if char == '[':
                                bracket_count += 1
                            elif char == ']':
                                bracket_count -= 1
                                if bracket_count == 0:
                                    break
                        if bracket_count != 0:
                            is_complete = False
                            break
                    
                    if not is_complete:
                        continue
                    
                    # Try to parse this day's JSON by completing the structure
                    day_json = '{' + day_text.rstrip(',') + '}'
                    try:
                        day_data = json.loads(day_json)
                        if self._validate_day_structure(day_data):
                            complete_days.append(day_data)
                    except json.JSONDecodeError:
                        continue
                except Exception as e:
                    logger.error(f"Error processing day: {str(e)}")
                    continue
            
            if not complete_days:
                return text
            
            # Sort days by day number
            complete_days.sort(key=lambda x: x["day"])
            
            # Create a valid meal plan with complete days
            result = {
                "meal_plan": {
                    "days": complete_days
                }
            }
            
            # Validate the final structure
            try:
                return json.dumps(result)
            except Exception as e:
                logger.error(f"Error creating final JSON: {str(e)}")
                return text
            
        except Exception as e:
            logger.error(f"Error fixing truncated meal plan: {str(e)}")
            return text
    
    def _validate_day_structure(self, day_data: Dict) -> bool:
        """Validate the structure of a single day in the meal plan"""
        try:
            if not isinstance(day_data, dict) or "day" not in day_data or "meals" not in day_data:
                return False
            
            if not isinstance(day_data["meals"], list) or len(day_data["meals"]) != 3:
                return False
            
            meal_types = set()
            for meal in day_data["meals"]:
                if not isinstance(meal, dict):
                    return False
                    
                required_fields = ["type", "name", "ingredients", "inventory_match", "missing_ingredients"]
                if not all(field in meal for field in required_fields):
                    return False
                
                # Check meal type
                if meal["type"] not in ["breakfast", "lunch", "dinner"]:
                    return False
                meal_types.add(meal["type"])
                
                # Validate ingredients
                if not isinstance(meal["ingredients"], list):
                    return False
                
                for ingredient in meal["ingredients"]:
                    if not isinstance(ingredient, dict):
                        return False
                    if not all(field in ingredient for field in ["name", "quantity", "unit"]):
                        return False
                    if not all(isinstance(ingredient[field], str) for field in ["name", "quantity", "unit"]):
                        return False
                
                # Validate inventory match
                if not isinstance(meal["inventory_match"], (int, float)):
                    try:
                        meal["inventory_match"] = float(meal["inventory_match"])
                    except (ValueError, TypeError):
                        return False
                
                # Validate missing ingredients
                if not isinstance(meal["missing_ingredients"], list):
                    return False
                if not all(isinstance(item, str) for item in meal["missing_ingredients"]):
                    return False
            
            # Ensure we have all meal types
            if len(meal_types) != 3 or not meal_types == {"breakfast", "lunch", "dinner"}:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating day structure: {str(e)}")
            return False
    
    def _validate_json_structure(self, text: str) -> str:
        """Validate and fix JSON structure"""
        try:
            # First try to parse as is
            try:
                json.loads(text)
                return text
            except json.JSONDecodeError:
                pass
            
            # If this is a meal plan, handle meal plan validation
            if '"meal_plan"' in text and '"days"' in text:
                # Find all complete days
                day_matches = list(re.finditer(r'{\s*"day":\s*(\d+)', text))
                complete_days = []
                
                for i, day_match in enumerate(day_matches):
                    try:
                        day_start = day_match.start()
                        # Find the end of this day's data
                        next_day_start = day_matches[i + 1].start() if i + 1 < len(day_matches) else len(text)
                        day_text = text[day_start:next_day_start]
                        
                        # Check if this day has all required components
                        if not all(key in day_text for key in ['"meals":', '"type":', '"name":', '"ingredients":', '"inventory_match":', '"missing_ingredients":']):
                            continue
                        
                        # Check for complete meal structure
                        meal_types = re.findall(r'"type":\s*"(breakfast|lunch|dinner)"', day_text)
                        if len(meal_types) != 3 or len(set(meal_types)) != 3:
                            continue
                        
                        # Ensure all ingredients sections are complete
                        ingredients_sections = re.findall(r'"ingredients":\s*\[(.*?)\]', day_text, re.DOTALL)
                        if len(ingredients_sections) != 3:
                            continue
                        
                        # Verify each ingredients section has complete items
                        valid_ingredients = True
                        for ingredients in ingredients_sections:
                            if not all(key in ingredients for key in ['"name"', '"quantity"', '"unit"']):
                                valid_ingredients = False
                                break
                        
                        if not valid_ingredients:
                            continue
                        
                        # This appears to be a complete day
                        complete_days.append(day_text.rstrip(','))
                    except Exception as e:
                        logger.error(f"Error processing day: {str(e)}")
                        continue
                
                if complete_days:
                    # Create a valid meal plan structure
                    result = {
                        "meal_plan": {
                            "days": []
                        }
                    }
                    
                    # Parse and add each complete day
                    for day_text in complete_days:
                        try:
                            day_json = '{' + day_text + '}'
                            day_data = json.loads(day_json)
                            result["meal_plan"]["days"].append(day_data)
                        except json.JSONDecodeError:
                            continue
                    
                    # Sort days by day number
                    result["meal_plan"]["days"].sort(key=lambda x: x["day"])
                    
                    # Return the validated JSON
                    return json.dumps(result, separators=(',', ':'))
            
            return text
            
        except Exception as e:
            logger.error(f"Error validating JSON structure: {str(e)}")
            return text
    
    async def generate_json_content(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Generate JSON content using the Gemini model"""
        try:
            # Add explicit JSON formatting instruction and size limit
            json_prompt = f"""
            {prompt}
            
            CRITICAL RESPONSE REQUIREMENTS:
            1. Respond ONLY with valid JSON. No additional text or formatting.
            2. Keep responses concise and within 4000 characters.
            3. For shopping lists:
               - Always include at least one item in essential_items if inventory is low
               - Prioritize expiring items and low stock items
               - Provide specific quantities and clear reasons
            4. Ensure all JSON objects are properly closed.
            5. Do not truncate in the middle of objects.
            6. Use proper JSON formatting with double quotes.
            7. Include all required fields for each item type.
            """
            
            # Generate content with balanced parameters
            response = self.model.generate_content(
                json_prompt,
                generation_config={
                    'temperature': self.temperature,
                    'top_p': self.top_p,
                    'top_k': self.top_k,
                    'max_output_tokens': 4000,
                    'stop_sequences': ['}}}']
                }
            )
            
            if not response or not response.text:
                logger.error("Empty response from Gemini model")
                return None
            
            # Log the raw response for debugging
            logger.debug(f"Raw response: {response.text}")
            
            # Clean and validate the JSON response
            cleaned_text = self._clean_json_text(response.text)
            logger.debug(f"Cleaned text: {cleaned_text}")
            
            try:
                validated_text = self._validate_json_structure(cleaned_text)
                logger.debug(f"Validated text: {validated_text}")
                
                # Parse and validate the structure
                result = json.loads(validated_text)
                
                # Handle different types of responses
                if "shopping_list" in result:
                    # Validate shopping list structure
                    shopping_list = result.get("shopping_list", {})
                    if not isinstance(shopping_list, dict):
                        logger.error("Invalid shopping list structure")
                        return None
                    
                    required_sections = ["meal_plan_items", "essential_items", "recommended_items"]
                    if not all(section in shopping_list for section in required_sections):
                        logger.error("Missing required sections in shopping list")
                        return None
                    
                    # Ensure lists are properly initialized
                    for section in required_sections:
                        if not isinstance(shopping_list[section], list):
                            shopping_list[section] = []
                    
                    # Validate each item in the lists
                    for section in required_sections:
                        items = shopping_list[section]
                        valid_items = []
                        for item in items:
                            if not isinstance(item, dict):
                                continue
                            
                            # Check required fields
                            if section in ["meal_plan_items", "essential_items"]:
                                if all(key in item for key in ["name", "quantity", "priority", "reason"]):
                                    valid_items.append(item)
                            else:  # recommended_items
                                if all(key in item for key in ["name", "quantity", "reason"]):
                                    valid_items.append(item)
                        
                        shopping_list[section] = valid_items
                    
                    return result
                
                elif "meal_plan" in result:
                    # Handle meal plan validation (existing code)
                    days = result.get("meal_plan", {}).get("days", [])
                    if not days:
                        logger.error("No complete days found in meal plan")
                        return None
                    
                    complete_days = []
                    for day in days:
                        if not isinstance(day, dict) or "meals" not in day:
                            continue
                        
                        meals = day["meals"]
                        if not isinstance(meals, list) or len(meals) != 3:
                            continue
                        
                        if all(
                            isinstance(meal, dict) and
                            all(key in meal for key in ["type", "name", "ingredients", "inventory_match", "missing_ingredients"]) and
                            isinstance(meal["ingredients"], list) and
                            all(isinstance(ing, dict) and all(k in ing for k in ["name", "quantity", "unit"]) 
                                for ing in meal["ingredients"])
                            for meal in meals
                        ):
                            complete_days.append(day)
                    
                    if complete_days:
                        result["meal_plan"]["days"] = complete_days
                        return result
                    else:
                        logger.error("No valid complete days found in meal plan")
                        return None
                
                return result
                
            except json.JSONDecodeError as je:
                logger.error(f"JSON decode error: {str(je)}")
                logger.error(f"Failed JSON text: {cleaned_text}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating JSON content: {str(e)}")
            return None
    
    async def generate_content(self, prompt: str) -> Optional[str]:
        """Generate text content using the Gemini model"""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': self.temperature,
                    'top_p': self.top_p,
                    'top_k': self.top_k
                }
            )
            
            if not response or not response.text:
                logger.error("Empty response from Gemini model")
                return None
            
            # For JSON-like prompts, clean the response
            if '"' in prompt or '{' in prompt or '[' in prompt:
                cleaned_text = self._clean_json_text(response.text)
                return self._validate_json_structure(cleaned_text)
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            return None
