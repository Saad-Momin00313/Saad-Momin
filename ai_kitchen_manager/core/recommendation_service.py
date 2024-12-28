from typing import List, Dict
from models.inventory import InventoryItem
from ai.gemini_service import GeminiService
from datetime import datetime, timedelta, date
from core.logger import logger
import json
import re

class RecommendationService:
    def __init__(self, db):
        self.db = db
        self.gemini = GeminiService()
        self.last_meal_plan = None  # Store the last generated meal plan
    
    async def get_meal_plans(self, days: int = 7, custom_instructions: str = "") -> Dict:
        """Generate meal plans based on available inventory and custom instructions"""
        try:
            # Create a minimal valid response for empty meal plan
            empty_response = {
                "meal_plan": {
                    "days": []
                }
            }
            
            items = self.db.query(InventoryItem).all()
            ingredients = [{"name": item.name, "quantity": item.quantity, "unit": item.unit}
                         for item in items]
            
            # Format custom instructions for better prompt handling
            formatted_instructions = custom_instructions.strip().lower() if custom_instructions else ""
            is_vegetarian = any(word in formatted_instructions for word in ["vegetarian", "vegetrian", "veg"])
            
            # Create dietary restrictions section
            dietary_restrictions = []
            if is_vegetarian:
                dietary_restrictions.append(
                    "STRICT VEGETARIAN REQUIREMENTS: No meat, fish, poultry, or seafood allowed in any meals."
                )
            
            # Process days in batches of 3 with retry logic
            all_days = []
            max_retries = 2  # Number of retries per batch
            
            for batch_start in range(1, days + 1, 3):
                batch_days = min(3, days - batch_start + 1)
                if batch_days <= 0:
                    break

                batch_success = False
                retry_count = 0
                
                while not batch_success and retry_count < max_retries:
                    try:
                        # Create a more concise prompt for meal planning
                        custom_prompt = f"""
                        Generate a meal plan JSON for exactly {batch_days} days (days {batch_start}-{batch_start + batch_days - 1}).
                        Available ingredients: {json.dumps(ingredients)}
                        Dietary restrictions: {json.dumps(dietary_restrictions)}
                        Additional instructions: {json.dumps(custom_instructions)}

                        CRITICAL: Generate ONLY valid JSON with this EXACT structure for {batch_days} days:
                        {{
                            "meal_plan": {{
                                "days": [
                                    {{
                                        "day": (number from {batch_start} to {batch_start + batch_days - 1}),
                                        "meals": [
                                            {{
                                                "type": "breakfast|lunch|dinner",
                                                "name": "string",
                                                "ingredients": [
                                                    {{
                                                        "name": "string",
                                                        "quantity": "string",
                                                        "unit": "string"
                                                    }}
                                                ],
                                                "inventory_match": (number 0-100),
                                                "missing_ingredients": []
                                            }}
                                        ]
                                    }}
                                ]
                            }}
                        }}

                        RULES:
                        1. Generate EXACTLY {batch_days} days, numbered {batch_start} to {batch_start + batch_days - 1}
                        2. Each day MUST have EXACTLY 3 meals (breakfast, lunch, dinner)
                        3. Use ONLY double quotes, NO single quotes
                        4. NO trailing commas
                        5. Keep meals realistic and varied
                        6. Follow dietary restrictions strictly
                        """
                        
                        # Get response from model
                        batch_meal_plan = await self.gemini.generate_json_content(custom_prompt)
                        if not batch_meal_plan:
                            retry_count += 1
                            continue
                        
                        # Clean and validate JSON
                        if isinstance(batch_meal_plan, str):
                            # Remove any non-JSON content
                            json_start = batch_meal_plan.find('{')
                            json_end = batch_meal_plan.rfind('}') + 1
                            if json_start >= 0 and json_end > json_start:
                                batch_meal_plan = batch_meal_plan[json_start:json_end]
                            
                            try:
                                batch_meal_plan = json.loads(batch_meal_plan)
                            except json.JSONDecodeError as e:
                                logger.error(f"Failed to parse meal plan JSON for batch {batch_start}: {str(e)}")
                                retry_count += 1
                                continue
                        
                        # Validate and sanitize batch meal plan
                        sanitized = self._sanitize_meal_plan(batch_meal_plan, batch_days)
                        if sanitized and self._validate_meal_plan(sanitized):
                            # Verify day numbers are correct
                            days_in_range = all(
                                batch_start <= day["day"] <= batch_start + batch_days - 1 
                                for day in sanitized["meal_plan"]["days"]
                            )
                            if days_in_range:
                                all_days.extend(sanitized["meal_plan"]["days"])
                                batch_success = True
                            else:
                                logger.error(f"Invalid day numbers in batch {batch_start}")
                                retry_count += 1
                        else:
                            retry_count += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing batch {batch_start}: {str(e)}")
                        retry_count += 1

                if not batch_success:
                    logger.warning(f"Failed to generate valid meal plan for days {batch_start}-{batch_start + batch_days - 1} after {max_retries} attempts")

            # If we have any valid days, return them
            if all_days:
                # Sort days by day number to ensure correct order
                all_days.sort(key=lambda x: x["day"])
                result = {
                    "meal_plan": {
                        "days": all_days
                    }
                }
                
                # Final validation of complete structure
                try:
                    json_str = json.dumps(result)
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    logger.error("Failed final JSON validation")
                    return empty_response
            
            return empty_response

        except Exception as e:
            logger.error(f"Error generating meal plans: {str(e)}")
            return empty_response

    def _sanitize_meal_plan(self, data: Dict, expected_days: int) -> Dict:
        """Sanitize and normalize the meal plan data"""
        try:
            if not isinstance(data, dict):
                logger.error("Data is not a dictionary")
                return None
            
            if "meal_plan" not in data:
                logger.error("No meal_plan key in data")
                return None
            
            meal_plan = data.get("meal_plan", {})
            if not isinstance(meal_plan, dict):
                logger.error("meal_plan is not a dictionary")
                return None
            
            days = meal_plan.get("days", [])
            if not isinstance(days, list):
                logger.error("days is not a list")
                return None
            
            # Initialize result structure
            result = {
                "meal_plan": {
                    "days": []
                }
            }
            
            # Process each day
            valid_days = []
            for day_data in days:
                try:
                    if not isinstance(day_data, dict):
                        continue
                    
                    day_num = day_data.get("day")
                    if not isinstance(day_num, (int, float)) or day_num < 1:
                        continue
                    
                    meals = day_data.get("meals", [])
                    if not isinstance(meals, list) or len(meals) != 3:
                        continue
                    
                    sanitized_meals = []
                    for meal in meals:
                        if not isinstance(meal, dict):
                            continue
                        
                        meal_type = str(meal.get("type", "")).strip().lower()
                        if meal_type not in ["breakfast", "lunch", "dinner"]:
                            continue
                        
                        name = str(meal.get("name", "")).strip()
                        if not name:
                            continue
                        
                        ingredients = meal.get("ingredients", [])
                        if not isinstance(ingredients, list):
                            continue
                        
                        sanitized_ingredients = []
                        for ingredient in ingredients:
                            if not isinstance(ingredient, dict):
                                continue
                            
                            ing_name = str(ingredient.get("name", "")).strip()
                            ing_quantity = str(ingredient.get("quantity", "")).strip()
                            ing_unit = str(ingredient.get("unit", "")).strip() if ingredient.get("unit") is not None else "unit"
                            
                            if not ing_name or not ing_quantity:
                                continue
                            
                            sanitized_ingredients.append({
                                "name": ing_name,
                                "quantity": ing_quantity,
                                "unit": ing_unit
                            })
                        
                        if not sanitized_ingredients:
                            continue
                        
                        # Handle inventory match and missing ingredients
                        try:
                            inventory_match = float(meal.get("inventory_match", 0))
                            inventory_match = max(0, min(100, inventory_match))
                        except (ValueError, TypeError):
                            inventory_match = 0
                        
                        missing_ingredients = []
                        raw_missing = meal.get("missing_ingredients", [])
                        if isinstance(raw_missing, list):
                            for item in raw_missing:
                                if isinstance(item, dict) and "name" in item:
                                    missing_ingredients.append(str(item["name"]).strip())
                                elif isinstance(item, str):
                                    missing_ingredients.append(item.strip())
                        
                        sanitized_meal = {
                            "type": meal_type,
                            "name": name,
                            "ingredients": sanitized_ingredients,
                            "inventory_match": inventory_match,
                            "missing_ingredients": missing_ingredients
                        }
                        
                        sanitized_meals.append(sanitized_meal)
                    
                    if len(sanitized_meals) == 3:
                        valid_days.append({
                            "day": int(day_num),
                            "meals": sanitized_meals
                        })
                except Exception as e:
                    logger.error(f"Error processing day: {str(e)}")
                    continue
            
            # Sort days by day number
            valid_days.sort(key=lambda x: x["day"])
            result["meal_plan"]["days"] = valid_days
            
            return result
            
        except Exception as e:
            logger.error(f"Error sanitizing meal plan: {str(e)}")
            return None
    
    def _validate_meal_plan(self, meal_plan: Dict) -> bool:
        """Validate the structure of the generated meal plan"""
        try:
            if not isinstance(meal_plan, dict):
                logger.error("Meal plan is not a dictionary")
                return False
            
            if "meal_plan" not in meal_plan:
                logger.error("Missing meal_plan key")
                return False
            
            if not isinstance(meal_plan["meal_plan"], dict):
                logger.error("meal_plan value is not a dictionary")
                return False
            
            if "days" not in meal_plan["meal_plan"]:
                logger.error("Missing days key in meal_plan")
                return False
            
            days = meal_plan["meal_plan"]["days"]
            if not isinstance(days, list):
                logger.error("days is not a list")
                return False
            
            if not days:
                logger.error("days list is empty")
                return False
            
            # Track meal types per day to ensure completeness
            expected_meal_types = {"breakfast", "lunch", "dinner"}
            
            # Validate each day
            day_numbers = set()
            for day in days:
                if not isinstance(day, dict):
                    logger.error("Day entry is not a dictionary")
                    return False
                
                if "day" not in day or "meals" not in day:
                    logger.error("Day missing required fields")
                    return False
                
                day_num = day["day"]
                if not isinstance(day_num, (int, float)) or day_num < 1:
                    logger.error(f"Invalid day number: {day_num}")
                    return False
                
                if day_num in day_numbers:
                    logger.error(f"Duplicate day number: {day_num}")
                    return False
                day_numbers.add(day_num)
                
                meals = day["meals"]
                if not isinstance(meals, list) or len(meals) != 3:
                    logger.error(f"Invalid meals list for day {day_num}")
                    return False
                
                # Validate meals
                meal_types = set()
                for meal in meals:
                    if not isinstance(meal, dict):
                        logger.error(f"Meal is not a dictionary in day {day_num}")
                        return False
                    
                    required_fields = ["type", "name", "ingredients", "inventory_match", "missing_ingredients"]
                    if not all(field in meal for field in required_fields):
                        logger.error(f"Missing required fields in meal for day {day_num}")
                        return False
                    
                    meal_type = str(meal["type"]).lower()
                    if meal_type not in expected_meal_types:
                        logger.error(f"Invalid meal type {meal_type} in day {day_num}")
                        return False
                    
                    if meal_type in meal_types:
                        logger.error(f"Duplicate meal type {meal_type} in day {day_num}")
                        return False
                    meal_types.add(meal_type)
                    
                    # Validate ingredients
                    ingredients = meal["ingredients"]
                    if not isinstance(ingredients, list) or not ingredients:
                        logger.error(f"Invalid ingredients list in day {day_num}")
                        return False
                    
                    for ingredient in ingredients:
                        if not isinstance(ingredient, dict):
                            logger.error(f"Ingredient is not a dictionary in day {day_num}")
                            return False
                        
                        if not all(field in ingredient for field in ["name", "quantity", "unit"]):
                            logger.error(f"Missing ingredient fields in day {day_num}")
                            return False
                        
                        if not all(isinstance(ingredient[field], str) for field in ["name", "quantity", "unit"]):
                            logger.error(f"Invalid ingredient field types in day {day_num}")
                            return False
                    
                    # Validate inventory match
                    inventory_match = meal["inventory_match"]
                    if not isinstance(inventory_match, (int, float)) or not (0 <= inventory_match <= 100):
                        logger.error(f"Invalid inventory_match in day {day_num}")
                        return False
                    
                    # Validate missing ingredients
                    missing_ingredients = meal["missing_ingredients"]
                    if not isinstance(missing_ingredients, list):
                        logger.error(f"Invalid missing_ingredients list in day {day_num}")
                        return False
                    
                    if not all(isinstance(item, str) for item in missing_ingredients):
                        logger.error(f"Invalid missing_ingredients items in day {day_num}")
                        return False
                
                if meal_types != expected_meal_types:
                    logger.error(f"Missing meal types in day {day_num}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating meal plan: {str(e)}")
            return False

    def _get_missing_ingredients_from_meal_plan(self) -> List[Dict]:
        """Extract missing ingredients from the last generated meal plan"""
        missing_ingredients = []
        if self.last_meal_plan and "meal_plan" in self.last_meal_plan:
            for day in self.last_meal_plan["meal_plan"]["days"]:
                for meal in day["meals"]:
                    if "missing_ingredients" in meal:
                        missing_ingredients.extend(meal["missing_ingredients"])
        return missing_ingredients

    async def get_shopping_recommendations(self, custom_instructions: str = "") -> Dict:
        """Generate smart shopping recommendations based on inventory, meal plan, and custom instructions"""
        try:
            # Create a minimal valid response for empty lists
            empty_response = {
                "shopping_list": {
                    "meal_plan_items": [],
                    "essential_items": [],
                    "recommended_items": []
                }
            }
            
            # Get all inventory items
            items = self.db.query(InventoryItem).all()
            
            # Get missing ingredients from meal plan
            missing_ingredients = self._get_missing_ingredients_from_meal_plan()
            
            # Process custom instructions with AI if provided
            if custom_instructions:
                # Create inventory context for AI
                inventory_context = [{
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit": item.unit
                } for item in items]
                
                # Create prompt for AI
                prompt = f"""
                Analyze this recipe request and determine required ingredients:
                Recipe: {custom_instructions}

                Current inventory:
                {json.dumps(inventory_context, indent=2)}

                Return ONLY valid JSON with this structure:
                {{
                    "required_ingredients": [
                        {{
                            "name": "ingredient name",
                            "quantity": "required amount",
                            "unit": "measurement unit",
                            "reason": "why this ingredient is needed"
                        }}
                    ],
                    "missing_ingredients": [
                        {{
                            "name": "ingredient name",
                            "quantity": "suggested amount",
                            "unit": "measurement unit",
                            "reason": "why this ingredient is missing and needed"
                        }}
                    ]
                }}

                Consider:
                1. Standard recipe ingredients and quantities
                2. Check against current inventory
                3. Only include missing ingredients that are actually needed
                4. Suggest appropriate quantities based on typical recipe needs
                """
                
                try:
                    # Get AI response
                    ai_response = await self.gemini.generate_json_content(prompt)
                    if ai_response and "missing_ingredients" in ai_response:
                        # Add AI-suggested missing ingredients
                        for ingredient in ai_response["missing_ingredients"]:
                            missing_ingredients.append({
                                "name": ingredient["name"],
                                "quantity": ingredient["quantity"],
                                "unit": ingredient.get("unit", "units"),
                                "reason": ingredient["reason"]
                            })
                except Exception as e:
                    logger.error(f"Error processing custom instructions with AI: {str(e)}")
            
            # Initialize shopping list sections
            shopping_list = {
                "meal_plan_items": [],
                "essential_items": [],
                "recommended_items": []
            }
            
            # Process meal plan items and custom instruction items
            for item in missing_ingredients:
                if isinstance(item, dict):
                    # Handle AI-generated recommendations
                    shopping_list["meal_plan_items"].append({
                        "name": item["name"],
                        "quantity": item["quantity"],
                        "priority": "high",
                        "reason": item.get("reason", "Required for recipe")
                    })
                else:
                    # Handle simple string ingredients from meal plan
                    shopping_list["meal_plan_items"].append({
                        "name": item,
                        "quantity": "1",
                        "priority": "high",
                        "reason": "Required for planned meals"
                    })
            
            # Process inventory items
            current_date = datetime.utcnow().date()
            processed_items = set()  # Track processed items to avoid duplicates
            
            for item in items:
                # Skip if we've already processed this item
                item_key = (item.name, item.unit)
                if item_key in processed_items:
                    continue
                processed_items.add(item_key)
                
                # Get all instances of this item
                similar_items = [i for i in items if i.name == item.name and i.unit == item.unit]
                total_quantity = sum(i.quantity for i in similar_items)
                
                # Check expiration dates
                expiring_soon = False
                for similar_item in similar_items:
                    if similar_item.expiration_date:
                        exp_date = similar_item.expiration_date
                        if isinstance(exp_date, datetime):
                            exp_date = exp_date.date()
                        days_until_expiry = (exp_date - current_date).days
                        if days_until_expiry <= 7:
                            expiring_soon = True
                            break
                
                # Determine item status and add to appropriate list
                if expiring_soon or total_quantity <= 2:
                    reason = "expiring in less than 7 days" if expiring_soon else "low stock"
                    shopping_list["essential_items"].append({
                        "name": item.name,
                        "quantity": "4.0" if total_quantity <= 2 else "1.0",
                        "priority": "high",
                        "reason": f"{reason} ({total_quantity} {item.unit})"
                    })
                elif total_quantity <= 3:
                    shopping_list["recommended_items"].append({
                        "name": item.name,
                        "quantity": "1.0",
                        "reason": f"medium stock ({total_quantity} {item.unit})"
                    })
            
            return {"shopping_list": shopping_list}
            
        except Exception as e:
            logger.error(f"Error generating shopping recommendations: {str(e)}")
            return empty_response

    def _validate_exact_structure(self, data: Dict) -> bool:
        """Validate that the JSON structure exactly matches the expected format"""
        try:
            # Validate basic structure
            if not isinstance(data, dict) or len(data) != 1 or "shopping_list" not in data:
                return False
            
            shopping_list = data["shopping_list"]
            if not isinstance(shopping_list, dict) or len(shopping_list) != 3:
                return False
            
            required_sections = ["meal_plan_items", "essential_items", "recommended_items"]
            if set(shopping_list.keys()) != set(required_sections):
                return False
            
            # Validate each section
            for section in required_sections:
                if not isinstance(shopping_list[section], list):
                    return False
                
                # For empty lists, ensure they're properly formatted
                if not shopping_list[section]:
                    shopping_list[section] = []
                    continue
                
                for item in shopping_list[section]:
                    if not isinstance(item, dict):
                        return False
                    
                    required_fields = ["name", "quantity"]
                    if section in ["meal_plan_items", "essential_items"]:
                        required_fields.extend(["priority", "reason"])
                    else:
                        required_fields.append("reason")
                    
                    if set(item.keys()) != set(required_fields):
                        return False
                    
                    for field in required_fields:
                        if not isinstance(item[field], str) or not item[field].strip():
                            return False
            
            # Verify the JSON can be serialized without any extra whitespace
            # and is properly terminated
            compact_json = json.dumps(data, separators=(',', ':'))
            if not compact_json.startswith('{"shopping_list":') or not compact_json.endswith('}'):
                return False
            
            # Final validation - parse it back to ensure it's complete
            try:
                json.loads(compact_json)
                return True
            except json.JSONDecodeError:
                return False
            
        except Exception:
            return False

    def _sanitize_shopping_list(self, data: Dict) -> Dict:
        """Sanitize and normalize the shopping list data"""
        try:
            if not isinstance(data, dict) or "shopping_list" not in data:
                return None
            
            result = {
                "shopping_list": {
                    "meal_plan_items": [],
                    "essential_items": [],
                    "recommended_items": []
                }
            }
            
            shopping_list = data.get("shopping_list", {})
            if not isinstance(shopping_list, dict):
                return result
            
            sections = ["meal_plan_items", "essential_items", "recommended_items"]
            
            for section in sections:
                items = shopping_list.get(section, [])
                if not isinstance(items, list):
                    continue
                
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    sanitized_item = {}
                    
                    # Required fields for all sections
                    name = item.get("name", "").strip()
                    quantity = item.get("quantity", "")
                    # Handle both string and numeric quantity values
                    quantity = str(quantity).strip() if isinstance(quantity, str) else str(quantity)
                    if not name or not quantity:
                        continue
                    
                    sanitized_item["name"] = name
                    sanitized_item["quantity"] = quantity
                    
                    # Additional fields for meal_plan_items and essential_items
                    if section in ["meal_plan_items", "essential_items"]:
                        priority = item.get("priority", "").strip()
                        reason = item.get("reason", "").strip()
                        if not priority or not reason:
                            continue
                        sanitized_item["priority"] = priority
                        sanitized_item["reason"] = reason
                    
                    # Reason field for recommended_items
                    elif section == "recommended_items":
                        reason = item.get("reason", "").strip()
                        if not reason:
                            continue
                        sanitized_item["reason"] = reason
                    
                    result["shopping_list"][section].append(sanitized_item)
            
            return result
            
        except Exception as e:
            logger.error(f"Error sanitizing shopping list: {str(e)}")
            return None

    def _validate_shopping_list(self, shopping_list: Dict) -> bool:
        """Validate the structure of the generated shopping list"""
        try:
            # Check basic structure
            if not isinstance(shopping_list, dict) or "shopping_list" not in shopping_list:
                logger.error("Invalid shopping list structure: missing shopping_list key")
                return False
            
            shopping_list_data = shopping_list["shopping_list"]
            required_sections = ["meal_plan_items", "essential_items", "recommended_items"]
            
            # Check all required sections exist and are lists
            for section in required_sections:
                if section not in shopping_list_data:
                    logger.error(f"Invalid shopping list structure: missing {section} key")
                    return False
                if not isinstance(shopping_list_data[section], list):
                    logger.error(f"Invalid shopping list structure: {section} is not a list")
                    return False
            
            # Validate each item in each section
            for section in required_sections:
                items = shopping_list_data[section]
                for item_index, item in enumerate(items, 1):
                    if not isinstance(item, dict):
                        logger.error(f"Invalid item structure in {section}, item {item_index}")
                        return False
                    
                    # Check required fields for each section
                    required_fields = ["name", "quantity"]
                    if section in ["meal_plan_items", "essential_items"]:
                        required_fields.extend(["priority", "reason"])
                    elif section == "recommended_items":
                        required_fields.append("reason")
                    
                    if not all(field in item for field in required_fields):
                        missing_fields = [field for field in required_fields if field not in item]
                        logger.error(f"Missing required fields {missing_fields} in {section}, item {item_index}")
                        return False
                    
                    # Validate field types and content
                    for field in required_fields:
                        if not isinstance(item[field], str):
                            logger.error(f"Invalid {field} type in {section}, item {item_index}")
                            return False
                        if not item[field].strip():
                            logger.error(f"Empty {field} in {section}, item {item_index}")
                            return False
            
            # Verify JSON can be properly serialized
            json_str = json.dumps(shopping_list)
            parsed = json.loads(json_str)
            if parsed != shopping_list:
                logger.error("JSON serialization validation failed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating shopping list: {str(e)}")
            return False

    async def get_inventory_insights(self) -> Dict:
        """Get AI-powered insights about the current inventory state"""
        try:
            items = self.db.query(InventoryItem).all()
            inventory_data = [{
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "category": item.category,
                "expiration_date": item.expiration_date.isoformat() if item.expiration_date else None,
                "days_until_expiration": item.days_until_expiration,
                "is_low_stock": item.is_low_stock,
                "created_at": item.created_at.isoformat(),
                "updated_at": item.updated_at.isoformat()
            } for item in items]

            prompt = f"""
            Analyze this inventory data and provide insights in JSON format:
            {json.dumps(inventory_data)}

            Generate insights about:
            1. Items that need immediate attention (expiring soon or low stock)
            2. Category-based analysis (which categories need restocking)
            3. Usage patterns (items frequently running low)
            4. Storage optimization suggestions
            5. Waste reduction opportunities

            Return ONLY valid JSON with this structure:
            {{
                "urgent_actions": [
                    {{
                        "item": "string",
                        "issue": "string",
                        "recommendation": "string",
                        "priority": "high|medium|low"
                    }}
                ],
                "category_analysis": [
                    {{
                        "category": "string",
                        "status": "string",
                        "recommendations": ["string"]
                    }}
                ],
                "usage_patterns": [
                    {{
                        "pattern": "string",
                        "affected_items": ["string"],
                        "suggestion": "string"
                    }}
                ],
                "storage_optimization": [
                    {{
                        "suggestion": "string",
                        "benefit": "string",
                        "affected_items": ["string"]
                    }}
                ],
                "waste_reduction": [
                    {{
                        "item": "string",
                        "risk": "string",
                        "action": "string"
                    }}
                ]
            }}
            """

            insights = await self.gemini.generate_json_content(prompt)
            return insights if insights else {}

        except Exception as e:
            logger.error(f"Error generating inventory insights: {str(e)}")
            return {}

    async def get_smart_reorder_suggestions(self) -> Dict:
        """Get AI-powered suggestions for reordering items"""
        try:
            items = self.db.query(InventoryItem).all()
            inventory_data = [{
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "category": item.category,
                "is_low_stock": item.is_low_stock,
                "usage_history": self._get_item_usage_history(item.id)
            } for item in items]

            prompt = f"""
            Analyze this inventory data and provide smart reordering suggestions:
            {json.dumps(inventory_data)}

            Consider:
            1. Current stock levels vs. thresholds
            2. Historical usage patterns
            3. Category-based ordering optimization
            4. Bulk ordering opportunities
            5. Seasonal factors

            Return ONLY valid JSON with this structure:
            {{
                "immediate_reorders": [
                    {{
                        "item": "string",
                        "current_quantity": "string",
                        "suggested_order": "string",
                        "reason": "string",
                        "priority": "high|medium|low"
                    }}
                ],
                "upcoming_reorders": [
                    {{
                        "item": "string",
                        "timeframe": "string",
                        "suggested_order": "string",
                        "reason": "string"
                    }}
                ],
                "bulk_opportunities": [
                    {{
                        "items": ["string"],
                        "suggestion": "string",
                        "potential_savings": "string"
                    }}
                ],
                "seasonal_recommendations": [
                    {{
                        "season": "string",
                        "items": ["string"],
                        "action": "string"
                    }}
                ]
            }}
            """

            suggestions = await self.gemini.generate_json_content(prompt)
            return suggestions if suggestions else {}

        except Exception as e:
            logger.error(f"Error generating reorder suggestions: {str(e)}")
            return {}

    def _get_item_usage_history(self, item_id: int) -> List[Dict]:
        """Get usage history for an item from the database"""
        # This would typically query a usage_history table
        # For now, return a simplified history based on updated_at timestamps
        try:
            item = self.db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
            if not item:
                return []

            # Calculate approximate usage based on quantity changes
            # In a real implementation, this would come from a proper usage_history table
            return [{
                "date": item.updated_at.isoformat(),
                "quantity_change": -1,  # Placeholder for actual quantity change
                "type": "usage"  # or "restock"
            }]
        except Exception as e:
            logger.error(f"Error getting item usage history: {str(e)}")
            return []

    async def get_waste_reduction_plan(self) -> Dict:
        """Generate an AI-powered plan to reduce waste in inventory"""
        try:
            items = self.db.query(InventoryItem).all()
            expiring_items = [item for item in items if item.expiration_date and item.will_expire_soon()]
            
            inventory_data = {
                "expiring_items": [{
                    "name": item.name,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "days_until_expiration": item.days_until_expiration,
                    "category": item.category
                } for item in expiring_items],
                "current_meal_plan": self.last_meal_plan
            }

            prompt = f"""
            Generate a waste reduction plan based on this data:
            {json.dumps(inventory_data)}

            Focus on:
            1. Using expiring items efficiently
            2. Portion optimization
            3. Storage recommendations
            4. Creative recipes for at-risk items
            5. Preservation techniques

            Return ONLY valid JSON with this structure:
            {{
                "priority_actions": [
                    {{
                        "item": "string",
                        "quantity": "string",
                        "days_left": number,
                        "recommended_action": "string",
                        "preservation_method": "string"
                    }}
                ],
                "recipe_suggestions": [
                    {{
                        "name": "string",
                        "uses_items": ["string"],
                        "preparation_time": "string",
                        "storage_life": "string"
                    }}
                ],
                "storage_adjustments": [
                    {{
                        "item": "string",
                        "current_storage": "string",
                        "recommended_storage": "string",
                        "expected_benefit": "string"
                    }}
                ],
                "portion_recommendations": [
                    {{
                        "item": "string",
                        "current_usage": "string",
                        "suggested_usage": "string",
                        "benefit": "string"
                    }}
                ]
            }}
            """

            plan = await self.gemini.generate_json_content(prompt)
            return plan if plan else {}

        except Exception as e:
            logger.error(f"Error generating waste reduction plan: {str(e)}")
            return {}

    async def get_inventory_optimization_report(self) -> Dict:
        """Generate a comprehensive inventory optimization report"""
        try:
            items = self.db.query(InventoryItem).all()
            inventory_data = [{
                "name": item.name,
                "quantity": item.quantity,
                "unit": item.unit,
                "category": item.category,
                "expiration_date": item.expiration_date.isoformat() if item.expiration_date else None,
                "is_low_stock": item.is_low_stock,
                "storage_duration": item.get_storage_duration()
            } for item in items]

            prompt = f"""
            Generate a comprehensive inventory optimization report based on this data:
            {json.dumps(inventory_data)}

            Analyze:
            1. Stock level efficiency
            2. Storage space utilization
            3. Category distribution
            4. Turnover rates
            5. Cost-saving opportunities

            Return ONLY valid JSON with this structure:
            {{
                "efficiency_metrics": {{
                    "overall_score": number,
                    "key_metrics": [
                        {{
                            "metric": "string",
                            "value": "string",
                            "benchmark": "string",
                            "improvement_potential": "string"
                        }}
                    ]
                }},
                "space_utilization": {{
                    "analysis": "string",
                    "recommendations": ["string"],
                    "potential_savings": "string"
                }},
                "category_insights": [
                    {{
                        "category": "string",
                        "status": "string",
                        "optimization_suggestions": ["string"]
                    }}
                ],
                "turnover_analysis": [
                    {{
                        "item_group": "string",
                        "current_rate": "string",
                        "optimal_rate": "string",
                        "action_items": ["string"]
                    }}
                ],
                "cost_optimization": [
                    {{
                        "area": "string",
                        "current_cost": "string",
                        "potential_savings": "string",
                        "recommendations": ["string"]
                    }}
                ]
            }}
            """

            report = await self.gemini.generate_json_content(prompt)
            return report if report else {}

        except Exception as e:
            logger.error(f"Error generating optimization report: {str(e)}")
            return {}