import streamlit as st
from ai.gemini_service import GeminiService
from models.inventory import InventoryItem
from core.database import get_db, init_db, engine, Base
from core.expiration_service import ExpirationService
from core.inventory_service import InventoryService
from datetime import datetime, timedelta
from core.recommendation_service import RecommendationService
import logging
from sqlalchemy import func
import asyncio
import json
import pandas as pd

# Initialize database tables
init_db()

logger = logging.getLogger(__name__)

# Price estimates per unit (in USD)
PRICE_ESTIMATES = {
    "rice_kg": 2.50,      # per kg
    "chicken_kg": 8.00,    # per kg
    "tomatoes_unit": 0.50, # per unit
    "milk_l": 3.50,       # per liter
    "onions_unit": 0.40,   # per unit
    # Default prices by unit
    "kilograms": 5.00,
    "units": 1.00,
    "liters": 3.00,
    "grams": 0.01,
    "milliliters": 0.003
}

async def estimate_item_value(item, gemini_service):
    """Use AI to estimate the value of an item based on current market prices"""
    try:
        prompt = f"""
        You are a grocery price estimation AI. Estimate the current market price for this item:
        Item: {item.name}
        Quantity: {item.quantity}
        Unit: {item.unit}
        Category: {item.category}

        Return ONLY a JSON response in this exact format:
        {{
            "estimated_price": price in USD as a number (total price for the given quantity),
            "unit_price": price per unit in USD as a number,
            "confidence": confidence level as a number between 0 and 1,
            "reasoning": "Brief explanation of the estimate"
        }}
        """
        
        response = await gemini_service.generate_json_content(prompt)
        if response and "estimated_price" in response:
            return float(response["estimated_price"])
        return 0.0
    except Exception as e:
        logger.error(f"Error estimating value for {getattr(item, 'name', 'unknown')}: {str(e)}")
        return 0.0

def clear_all():
    """Clear database and Streamlit cache"""
    # Clear database
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    # Clear Streamlit cache
    st.cache_data.clear()
    st.cache_resource.clear()
    st.rerun()

async def main():
    st.set_page_config(
        page_title="AI Kitchen Inventory Manager",
        page_icon="🏪",
        layout="wide"
    )
    
    # Add clear database button in sidebar
    if st.sidebar.button("Clear Database", type="primary"):
        clear_all()
    
    # Main navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a page",
        ["Dashboard", "Inventory", "Recommendations"]
    )
    
    if page == "Dashboard":
        await show_dashboard()
    elif page == "Inventory":
        await show_inventory()
    elif page == "Recommendations":
        await show_recommendations()

def parse_gemini_response(response_text: str) -> dict:
    """Parse Gemini response and ensure valid JSON"""
    try:
        # Clean the response text to extract only the JSON part
        json_str = response_text.strip()
        if json_str.startswith("```json"):
            json_str = json_str.split("```json")[1]
        if json_str.endswith("```"):
            json_str = json_str.rsplit("```", 1)[0]
        return json.loads(json_str.strip())
    except Exception as e:
        logger.error(f"Error parsing Gemini response: {str(e)}")
        return {}

async def show_dashboard():
    st.title("Kitchen Inventory Dashboard")
    
    try:
        # Get database connection and services
        db = next(get_db())
        inventory_service = InventoryService(db)
        expiration_service = ExpirationService(db)
        gemini_service = GeminiService()
        
        # Get all inventory items and prepare analysis data
        all_items = db.query(InventoryItem).all()
        
        if not all_items:
            st.info("No items in inventory. Add some items to see the dashboard!")
            return
        
        # Calculate total inventory value using AI
        total_value = 0.0
        value_details = []
        
        with st.spinner("Calculating inventory value..."):
            for item in all_items:
                item_value = await estimate_item_value(item, gemini_service)
                total_value += item_value
                value_details.append({
                    "name": item.name,
                    "value": item_value
                })
        
        # Enhanced inventory data with more details
        inventory_data = []
        for item in all_items:
            try:
                days_until_exp = None
                if item.expiration_date:
                    try:
                        current_date = datetime.now().date()
                        days_until_exp = (item.expiration_date - current_date).days
                    except Exception as exp_err:
                        logger.error(f"Error calculating expiration for {item.name}: {str(exp_err)}")
                
                # Handle quantity conversion
                try:
                    quantity = float(item.quantity) if item.quantity is not None else 0.0
                except (ValueError, TypeError) as qty_err:
                    logger.error(f"Error converting quantity for {item.name}: {str(qty_err)}")
                    quantity = 0.0
                
                # Create item data with safe defaults
                item_data = {
                    "name": str(item.name) if item.name else "Unnamed Item",
                    "quantity": quantity,
                    "unit": str(item.unit) if item.unit else "units",
                    "category": str(item.category) if item.category else "Uncategorized",
                    "expiration_date": item.expiration_date.isoformat() if item.expiration_date else None,
                    "created_at": item.created_at.isoformat() if item.created_at else datetime.now().isoformat(),
                    "updated_at": item.updated_at.isoformat() if item.updated_at else datetime.now().isoformat(),
                    "days_until_expiration": days_until_exp,
                    "is_low_stock": quantity <= 3,
                    "last_updated": (datetime.now() - (item.updated_at or datetime.now())).days,
                    "value": next((detail["value"] for detail in value_details if detail["name"] == item.name), 0.0)
                }
                inventory_data.append(item_data)
                logger.info(f"Successfully processed item: {item.name}")
            except Exception as e:
                logger.error(f"Error processing item {getattr(item, 'name', 'unknown')}: {str(e)}")
                continue
        
        if not inventory_data:
            st.warning("Could not process any inventory items. Please check the data format.")
            return
        
        # Calculate additional metrics
        category_summary = {}
        expiring_items = []
        low_stock_items = []
        
        for item in inventory_data:
            try:
                # Category summary
                cat = item["category"]
                if cat not in category_summary:
                    category_summary[cat] = {
                        "total_items": 0,
                        "low_stock_items": 0,
                        "expiring_soon": 0,
                        "total_quantity": 0,
                        "items": []
                    }
                category_summary[cat]["total_items"] += 1
                category_summary[cat]["total_quantity"] += item["quantity"]
                category_summary[cat]["items"].append(item)
                
                # Track low stock items
                if item["is_low_stock"]:
                    category_summary[cat]["low_stock_items"] += 1
                    low_stock_items.append(item)
                
                # Track expiring items
                if item.get("days_until_expiration") is not None and item["days_until_expiration"] <= 7:
                    category_summary[cat]["expiring_soon"] += 1
                    expiring_items.append(item)
            except Exception as e:
                logger.error(f"Error processing category data for {item.get('name', 'unknown')}: {str(e)}")
                continue

        # Enhanced analysis data
        analysis_data = {
            "inventory": inventory_data,
            "category_summary": category_summary,
            "total_items": len(all_items),
            "categories": list(category_summary.keys()),
            "low_stock_items": low_stock_items,
            "expiring_items": expiring_items,
            "metrics": {
                "total_categories": len(category_summary),
                "low_stock_count": len(low_stock_items),
                "expiring_soon_count": len(expiring_items),
                "recently_updated": len([i for i in inventory_data if i["last_updated"] <= 1])
            }
        }

        # Top Row - Key Metrics with Tabs
        st.markdown("### 📊 Inventory Status")
        metric_tabs = st.tabs(["Overview", "Categories", "Alerts", "Charts"])
        
        with metric_tabs[0]:
            col1, col2, col3 = st.columns(3)
            with st.spinner("Analyzing inventory..."):
                try:
                    metrics_prompt = f"""
                    You are a kitchen inventory analysis AI. Analyze this detailed inventory data and return ONLY a JSON response.
                    Focus on monetary value, health balance, and sustainability metrics.
                    
                    Current inventory summary:
                    {json.dumps(analysis_data, indent=2)}
                    
                    The total calculated inventory value is: ${total_value:.2f}
                    
                    Return JSON in this exact format:
                    {{
                        "total_value": {total_value},
                        "health_score": nutritional balance score 0-100 (number),
                        "sustainability_score": environmental impact score 0-100 (number),
                        "health_trend": "improving" or "declining" or "stable",
                        "sustainability_trend": "improving" or "declining" or "stable",
                        "summary": "One sentence summary of overall inventory health"
                    }}
                    """
                    
                    response = gemini_service.chat_model.generate_content(metrics_prompt)
                    metrics_data = parse_gemini_response(response.text) if response and response.text else {}
                    
                    # Display metrics with error handling
                    with col1:
                        st.metric(
                            "Inventory Value", 
                            f"${total_value:.2f}",
                            help="Total value of current inventory"
                        )
                    
                    with col2:
                        try:
                            health_score = int(metrics_data.get('health_score', 0))
                            st.metric(
                                "Health Score", 
                                f"{health_score}/100",
                                delta=metrics_data.get('health_trend', 'stable'),
                                help="Based on nutritional balance and variety"
                            )
                        except (TypeError, ValueError):
                            st.metric("Health Score", "0/100")
                    
                    with col3:
                        try:
                            sustainability_score = int(metrics_data.get('sustainability_score', 0))
                            st.metric(
                                "Sustainability", 
                                f"{sustainability_score}/100",
                                delta=metrics_data.get('sustainability_trend', 'stable'),
                                help="Based on packaging, waste, and environmental impact"
                            )
                        except (TypeError, ValueError):
                            st.metric("Sustainability", "0/100")
                    
                    if metrics_data.get('summary'):
                        st.info(f"📊 {metrics_data['summary']}")
                except Exception as e:
                    logger.error(f"Error getting metrics: {str(e)}")
                    # Fallback metrics with proper formatting
                    with col1:
                        st.metric("Total Items", str(len(all_items)))
                    with col2:
                        st.metric("Categories", str(len(category_summary)))
                    with col3:
                        st.metric("Active Items", str(len([i for i in all_items if i.quantity > 0])))
        
        with metric_tabs[1]:
            try:
                # Category Overview
                if category_summary:
                    category_df = pd.DataFrame([{
                        "Category": cat,
                        "Total Items": data["total_items"],
                        "Total Quantity": f"{data['total_quantity']:.1f}",
                        "Low Stock": data["low_stock_items"],
                        "Expiring Soon": data["expiring_soon"]
                    } for cat, data in category_summary.items()])
                    
                    if not category_df.empty:
                        st.dataframe(
                            category_df,
                            use_container_width=True
                        )
                    else:
                        st.info("No category data available")
                else:
                    st.info("No categories defined yet")
            except Exception as e:
                logger.error(f"Error displaying category overview: {str(e)}")
                st.error("Error displaying category overview")
        
        with metric_tabs[2]:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### 🚨 Low Stock Items")
                try:
                    if low_stock_items:
                        low_stock_df = pd.DataFrame([{
                            "Item": item["name"],
                            "Quantity": f"{item['quantity']} {item['unit']}",
                            "Category": item["category"]
                        } for item in low_stock_items])
                        st.dataframe(low_stock_df, use_container_width=True)
                    else:
                        st.success("No items running low!")
                except Exception as e:
                    logger.error(f"Error displaying low stock items: {str(e)}")
                    st.error("Error displaying low stock items")
            
            with col2:
                st.markdown("##### ⚠️ Expiring Soon")
                try:
                    if expiring_items:
                        expiring_df = pd.DataFrame([{
                            "Item": item["name"],
                            "Expires In": f"{item['days_until_expiration']} days",
                            "Quantity": f"{item['quantity']} {item['unit']}"
                        } for item in expiring_items])
                        st.dataframe(expiring_df, use_container_width=True)
                    else:
                        st.success("No items expiring soon!")
                except Exception as e:
                    logger.error(f"Error displaying expiring items: {str(e)}")
                    st.error("Error displaying expiring items")
        
        with metric_tabs[3]:
            st.subheader("�� Inventory Visualizations")
            
            # Create two columns for charts
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                # Category Distribution Pie Chart
                st.write("#### Category Distribution")
                category_counts = pd.DataFrame([{
                    "Category": cat,
                    "Items": data["total_items"]
                } for cat, data in category_summary.items()])
                
                if not category_counts.empty:
                    fig = {
                        "data": [{
                            "values": category_counts["Items"],
                            "labels": category_counts["Category"],
                            "type": "pie",
                            "hole": 0.4,
                            "hoverinfo": "label+percent",
                            "textinfo": "value"
                        }],
                        "layout": {
                            "showlegend": True,
                            "height": 400,
                            "margin": {"t": 0, "b": 0, "l": 0, "r": 0}
                        }
                    }
                    st.plotly_chart(fig, use_container_width=True)
            
            with chart_col2:
                # Stock Levels Bar Chart
                st.write("#### Stock Levels by Category")
                stock_data = pd.DataFrame([{
                    "Category": cat,
                    "Total Quantity": data["total_quantity"]
                } for cat, data in category_summary.items()])
                
                if not stock_data.empty:
                    st.bar_chart(stock_data.set_index("Category"))
            
            # Full width charts
            st.write("#### Expiration Timeline")
            expiring_data = []
            for item in inventory_data:
                if item.get("days_until_expiration") is not None:
                    expiring_data.append({
                        "Item": item["name"],
                        "Days Until Expiration": item["days_until_expiration"]
                    })
            
            if expiring_data:
                exp_df = pd.DataFrame(expiring_data)
                exp_df = exp_df.sort_values("Days Until Expiration")
                
                fig = {
                    "data": [{
                        "type": "bar",
                        "x": exp_df["Item"],
                        "y": exp_df["Days Until Expiration"],
                        "marker": {
                            "color": ["red" if x <= 7 else "yellow" if x <= 14 else "green" for x in exp_df["Days Until Expiration"]]
                        }
                    }],
                    "layout": {
                        "title": "Days Until Expiration by Item",
                        "xaxis": {"title": "Items"},
                        "yaxis": {"title": "Days Until Expiration"},
                        "height": 400,
                        "margin": {"t": 30}
                    }
                }
                st.plotly_chart(fig, use_container_width=True)
            
            # Stock Status Distribution
            st.write("#### Stock Status Distribution")
            status_data = pd.DataFrame([{
                "Status": "Low Stock",
                "Count": len([i for i in inventory_data if i["is_low_stock"]])
            }, {
                "Status": "Expiring Soon",
                "Count": len([i for i in inventory_data if i.get("days_until_expiration") is not None and i["days_until_expiration"] <= 7])
            }, {
                "Status": "Good",
                "Count": len([i for i in inventory_data if not i["is_low_stock"] and (i.get("days_until_expiration") is None or i["days_until_expiration"] > 7)])
            }])
            
            fig = {
                "data": [{
                    "values": status_data["Count"],
                    "labels": status_data["Status"],
                    "type": "pie",
                    "marker": {
                        "colors": ["#ff9999", "#ffcc99", "#99ff99"]
                    }
                }],
                "layout": {
                    "title": "Inventory Status Distribution",
                    "height": 400,
                    "margin": {"t": 30}
                }
            }
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        logger.error(f"Error in dashboard: {str(e)}")
        st.error("Error loading dashboard. Please try refreshing the page.")

def show_expiration_tracking():
    st.subheader("Expiration Tracking")
    
    db = next(get_db())
    expiration_service = ExpirationService(db)
    
    # Show expiring items
    st.write("Items Expiring Soon")
    expiring_items = expiration_service.get_expiring_items()
    
    if expiring_items:
        expiring_df = pd.DataFrame([{
            'Item': item.item.name,
            'Days Remaining': item.days_until_expiration,
            'Quantity': item.current_quantity,
            'Freshness': f"{item.freshness_percentage:.1f}%"
        } for item in expiring_items])
        
        st.dataframe(expiring_df)
    else:
        st.info("No items are expiring soon!")
    
    # Show consumption priorities
    st.write("Consumption Priority List")
    priorities = expiration_service.suggest_consumption_priority()
    
    if priorities:
        priority_df = pd.DataFrame(priorities)
        st.dataframe(priority_df)

async def show_inventory():
    st.title("Kitchen Inventory Management")
    
    # Get database and services
    db = next(get_db())
    inventory_service = InventoryService(db)
    recommendation_service = RecommendationService(db)
    
    # Fetch all items
    items = db.query(InventoryItem).all()
    
    # Create tabs for different views
    tabs = st.tabs([
        "Overview",  # Combined Current Inventory and Category View
        "Smart Management",  # Combined AI features
        "Item Actions"  # Add/Remove items
    ])
    
    with tabs[0]:
        # Top metrics row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Items", len(items))
        with col2:
            st.metric("Low Stock Items", len([i for i in items if i.is_low_stock]))
        with col3:
            st.metric("Categories", len(set(i.category for i in items)))
        with col4:
            st.metric("Expiring Soon", len([i for i in items if i.expiration_date and i.will_expire_soon()]))
        
        # Main inventory view with filters
        st.subheader("📦 Current Inventory")
        
        # Filters in a single row
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 1, 1, 1])
        with filter_col1:
            search_term = st.text_input("🔍 Search items", "").lower()
        with filter_col2:
            selected_categories = st.multiselect(
                "Category",
                list(set(item.category for item in items if item.category))
            )
        with filter_col3:
            status_filter = st.multiselect(
                "Status",
                ["Low Stock", "Expiring Soon", "Good"]
            )
        with filter_col4:
            sort_by = st.selectbox(
                "Sort by",
                ["Name", "Category", "Quantity", "Expiration"],
                index=0
            )
        
        # Apply filters
        filtered_items = items
        if search_term:
            filtered_items = [i for i in filtered_items if search_term in i.name.lower()]
        if selected_categories:
            filtered_items = [i for i in filtered_items if i.category in selected_categories]
        if status_filter:
            filtered_items = [i for i in filtered_items if (
                ("Low Stock" in status_filter and i.is_low_stock) or
                ("Expiring Soon" in status_filter and i.expiration_date and i.will_expire_soon()) or
                ("Good" in status_filter and not i.is_low_stock and (not i.expiration_date or not i.will_expire_soon()))
            )]
        
        # Create and sort DataFrame
        inventory_df = pd.DataFrame([{
            "Name": item.name,
            "Category": item.category or "Uncategorized",
            "Quantity": f"{item.quantity} {item.unit}",
            "Expiration": item.expiration_date.strftime("%Y-%m-%d") if item.expiration_date else "N/A",
            "Days Left": item.days_until_expiration if item.expiration_date else None,
            "Status": "Low Stock" if item.is_low_stock else (
                "Expiring Soon" if item.expiration_date and item.will_expire_soon()
                else "Good"
            )
        } for item in filtered_items])
        
        if not inventory_df.empty:
            # Sort DataFrame
            sort_col = {
                "Name": "Name",
                "Category": "Category",
                "Quantity": "Quantity",
                "Expiration": "Days Left"
            }[sort_by]
            inventory_df = inventory_df.sort_values(sort_col)
            
            # Style and display DataFrame
            styled_df = inventory_df.style.apply(lambda x: [
                'background-color: #ffcdd2' if v == "Low Stock"
                else 'background-color: #fff9c4' if v == "Expiring Soon"
                else 'background-color: #c8e6c9' if v == "Good"
                else '' for v in x
            ], subset=['Status'])
            
            st.dataframe(styled_df, use_container_width=True, height=400)
        else:
            st.info("No items found matching your filters")
        
        # Category summary in expandable section
        with st.expander("📊 Category Summary"):
            # Group items by category
            categories = {}
            for item in items:
                cat = item.category or "Uncategorized"
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)
            
            # Display category metrics
            category_df = pd.DataFrame([{
                "Category": cat,
                "Total Items": len(items),
                "Low Stock": len([i for i in items if i.is_low_stock]),
                "Expiring Soon": len([i for i in items if i.expiration_date and i.will_expire_soon()])
            } for cat, items in categories.items()])
            
            st.dataframe(category_df, use_container_width=True)
    
    with tabs[1]:
        st.subheader("🧠 Smart Inventory Management")
        
        # AI action buttons in a single row
        ai_col1, ai_col2, ai_col3 = st.columns(3)
        
        with ai_col1:
            insights_btn = st.button("🔍 Generate Insights", key="insights_btn", use_container_width=True)
        with ai_col2:
            reorder_btn = st.button("🛒 Reorder Suggestions", key="reorder_btn", use_container_width=True)
        with ai_col3:
            waste_btn = st.button("♻️ Waste Reduction", key="waste_btn", use_container_width=True)
        
        if insights_btn:
            with st.spinner("Analyzing inventory data..."):
                insights = await recommendation_service.get_inventory_insights()
                if insights:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("### 🚨 Urgent Actions")
                        for action in insights.get("urgent_actions", []):
                            with st.expander(f"{action['item']} - {action['priority'].upper()}"):
                                st.write(f"**Issue:** {action['issue']}")
                                st.write(f"**Recommendation:** {action['recommendation']}")
                    
                    with col2:
                        st.write("### 📈 Usage Patterns")
                        for pattern in insights.get("usage_patterns", []):
                            with st.expander(pattern['pattern']):
                                st.write("**Affected Items:**")
                                for item in pattern['affected_items']:
                                    st.write(f"- {item}")
                                st.write(f"**Suggestion:** {pattern['suggestion']}")
        
        if reorder_btn:
            with st.spinner("Analyzing reordering needs..."):
                suggestions = await recommendation_service.get_smart_reorder_suggestions()
                if suggestions:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("### 🚨 Immediate Reorders")
                        for reorder in suggestions.get("immediate_reorders", []):
                            with st.expander(f"{reorder['item']} - {reorder['priority'].upper()}"):
                                st.write(f"**Current Quantity:** {reorder['current_quantity']}")
                                st.write(f"**Suggested Order:** {reorder['suggested_order']}")
                                st.write(f"**Reason:** {reorder['reason']}")
                    
                    with col2:
                        st.write("### 💰 Bulk Opportunities")
                        for bulk in suggestions.get("bulk_opportunities", []):
                            with st.expander(f"Potential Savings: {bulk['potential_savings']}"):
                                st.write("**Items:**")
                                for item in bulk['items']:
                                    st.write(f"- {item}")
                                st.write(f"**Suggestion:** {bulk['suggestion']}")
        
        if waste_btn:
            with st.spinner("Analyzing waste reduction opportunities..."):
                plan = await recommendation_service.get_waste_reduction_plan()
                if plan:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("### 🚨 Priority Actions")
                        for action in plan.get("priority_actions", []):
                            with st.expander(f"{action['item']} - {action['days_left']} days left"):
                                st.write(f"**Quantity:** {action['quantity']}")
                                st.write(f"**Action:** {action['recommended_action']}")
                                st.write(f"**Method:** {action['preservation_method']}")
                    
                    with col2:
                        st.write("### 👩‍🍳 Recipe Suggestions")
                        for recipe in plan.get("recipe_suggestions", []):
                            with st.expander(recipe['name']):
                                st.write("**Uses Items:**")
                                for item in recipe['uses_items']:
                                    st.write(f"- {item}")
                                st.write(f"**Prep Time:** {recipe['preparation_time']}")
    
    with tabs[2]:
        st.markdown("### 📝 Item Management")
        
        # Create two columns for the main layout
        main_col1, main_col2 = st.columns([2, 1])
        
        with main_col1:
            # Tabs for action selection
            action = st.tabs(["➕ Add Item", "➖ Remove Item"])
            
            with action[0]:  # Add Item
                # Get existing item names and categories
                existing_items = db.query(InventoryItem.name).distinct().all()
                existing_names = sorted([item[0] for item in existing_items])
                existing_categories = sorted(list(set([item.category for item in items if item.category])))
                
                # Item name with autocomplete
                name = st.selectbox(
                    "Item Name",
                    options=existing_names,
                    key="item_name",
                    placeholder="Type to search or add new item...",
                    index=None
                )

                with st.form("add_item_form", clear_on_submit=True):
                    # Create three columns for a more compact layout
                    col1, col2, col3 = st.columns([1, 1, 1])
                    
                    with col1:
                        quantity = st.number_input(
                            "Quantity",
                            min_value=0.0,
                            step=0.1,
                            format="%.1f"
                        )
                    
                    with col2:
                        unit = st.selectbox(
                            "Unit",
                            ["units", "grams", "kilograms", "liters", "milliliters"]
                        )
                    
                    with col3:
                        category = st.selectbox(
                            "Category",
                            options=existing_categories,
                            key="category",
                            placeholder="Type to search or add new category...",
                            index=None
                        )
                    
                    # Expiration date with better formatting
                    expiration = st.date_input(
                        "Expiration Date (optional)",
                        min_value=datetime.now().date()
                    )
                    
                    # Show current selection summary
                    if name:
                        st.info(f"Adding: **{name}** ({quantity} {unit}){f' in {category}' if category else ''}")
                    
                    # Submit button
                    submitted = st.form_submit_button(
                        "Add to Inventory",
                        type="primary",
                        use_container_width=True
                    )
                    
                    if submitted:
                        try:
                            if not name:
                                st.error("Please enter an item name")
                                return

                            # Normalize the name to title case for consistency
                            normalized_name = name.strip().title()
                            normalized_category = category.strip().title() if category else None
                            
                            # Check if item exists
                            existing_item = db.query(InventoryItem).filter(
                                func.lower(InventoryItem.name) == func.lower(normalized_name)
                            ).first()
                            
                            if existing_item:
                                existing_item.quantity += quantity
                                existing_item.updated_at = datetime.utcnow()
                                message = f"Updated quantity of {existing_item.name}"
                            else:
                                new_item = InventoryItem(
                                    name=normalized_name,
                                    quantity=quantity,
                                    unit=unit,
                                    category=normalized_category,
                                    expiration_date=expiration
                                )
                                db.add(new_item)
                                message = f"Added {normalized_name} to inventory!"
                            
                            db.commit()
                            st.success(message)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            db.rollback()
        
            with action[1]:  # Remove Item
                if not items:
                    st.warning("No items in inventory to remove")
                else:
                    # Sort items and create a clean display format
                    items.sort(key=lambda x: x.name.lower())
                    item_options = [
                        f"{item.name} ({item.quantity:.1f} {item.unit})"
                        for item in items
                    ]
                    
                    selected_item_idx = st.selectbox(
                        "Select item to remove",
                        range(len(item_options)),
                        format_func=lambda x: item_options[x]
                    )
                    selected_item = items[selected_item_idx]

                    # Show current quantity info
                    st.info(f"Current quantity: **{selected_item.quantity:.1f} {selected_item.unit}**")
                    
                    # Create columns for removal options
                    col1, col2 = st.columns(2)
                    with col1:
                        # Default to partial removal
                        remove_all = st.checkbox("Remove entire item", value=False)
                        
                        if not remove_all:
                            remove_quantity = st.number_input(
                                "Quantity to remove",
                                min_value=0.1,
                                max_value=float(selected_item.quantity),
                                value=min(1.0, float(selected_item.quantity)),
                                step=0.1,
                                format="%.1f"
                            )
                    
                    with col2:
                        reason = st.selectbox(
                            "Reason for removal",
                            ["Consumed", "Expired", "Damaged/Spoiled", "Given Away", "Other"]
                        )
                        
                        if reason == "Other":
                            reason = st.text_input("Specify reason")
                    
                    # Show removal summary with clear quantity indication
                    if remove_all:
                        summary = f"Removing: **Entire stock of {selected_item.name}** ({selected_item.quantity:.1f} {selected_item.unit})"
                    else:
                        remaining = selected_item.quantity - remove_quantity
                        summary = (
                            f"Removing: **{remove_quantity:.1f} {selected_item.unit}** of {selected_item.name}\n\n"
                            f"Remaining: {remaining:.1f} {selected_item.unit}"
                        )
                    
                    st.info(summary + f"\n\nReason: {reason}")
                    
                    if st.button("Remove from Inventory", type="primary", use_container_width=True):
                        try:
                            if remove_all:
                                db.delete(selected_item)
                                message = f"Removed entire stock of {selected_item.name}"
                            else:
                                new_quantity = selected_item.quantity - remove_quantity
                                if new_quantity <= 0:
                                    db.delete(selected_item)
                                    message = f"Removed all remaining {selected_item.name}"
                                else:
                                    selected_item.quantity = new_quantity
                                    selected_item.updated_at = datetime.utcnow()
                                    message = f"Removed {remove_quantity:.1f} {selected_item.unit} of {selected_item.name}"
                            
                            db.commit()
                            st.success(message)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                            db.rollback()

        with main_col2:
            # Quick inventory summary
            st.subheader("Quick Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Items", len(items))
            with col2:
                st.metric("Categories", len(set(i.category for i in items if i.category)))
            with col3:
                st.metric("Low Stock", len([i for i in items if i.is_low_stock]))

async def show_recommendations():
    st.subheader("Smart Kitchen Recommendations")
    
    db = next(get_db())
    recommendation_service = RecommendationService(db)
    
    # Meal Planning
    st.write("### Meal Planning")
    days = st.slider("Number of days to plan", 1, 14, 7)
    meal_plan_instructions = st.text_area(
        "Custom Instructions for Meal Planning",
        placeholder="E.g., vegetarian meals only, low-carb options, kid-friendly recipes, etc.",
        help="Add any specific requirements or preferences for your meal plan"
    )
    
    if st.button("Generate Meal Plan"):
        with st.spinner("Generating meal plan..."):
            try:
                meal_plan = await recommendation_service.get_meal_plans(days, meal_plan_instructions)
                if "meal_plan" in meal_plan and "days" in meal_plan["meal_plan"]:
                    st.write("### Generated Meal Plan")
                    
                    # Track complete days
                    complete_days = []
                    for day in meal_plan["meal_plan"]["days"]:
                        try:
                            # Validate day structure
                            if not isinstance(day, dict) or "day" not in day or "meals" not in day:
                                continue
                            
                            # Validate meals
                            if not isinstance(day["meals"], list) or len(day["meals"]) != 3:
                                continue
                                
                            # Check if all meals are complete
                            meals_complete = True
                            for meal in day["meals"]:
                                if not isinstance(meal, dict) or not all(key in meal for key in ["type", "name", "ingredients", "inventory_match", "missing_ingredients"]):
                                    meals_complete = False
                                    break
                                if not isinstance(meal["ingredients"], list) or not all(isinstance(ing, dict) and all(k in ing for k in ["name", "quantity", "unit"]) for ing in meal["ingredients"]):
                                    meals_complete = False
                                    break
                            
                            if meals_complete:
                                complete_days.append(day)
                        except Exception as e:
                            logger.error(f"Error validating day {day.get('day', '?')}: {str(e)}")
                            continue
                    
                    if complete_days:
                        # Display complete days
                        for day in complete_days:
                            st.write(f"#### Day {day['day']}")
                            for meal in day["meals"]:
                                with st.expander(f"**{meal['type'].title()}**: {meal['name']}"):
                                    st.write("Ingredients:")
                                    ingredients_df = pd.DataFrame([{
                                        "Ingredient": ing["name"],
                                        "Amount": f"{ing['quantity']} {ing['unit']}"
                                    } for ing in meal["ingredients"]])
                                    st.dataframe(ingredients_df, use_container_width=True)
                                    
                                    if meal["missing_ingredients"]:
                                        st.write("Missing Ingredients:")
                                        st.error("\n".join(f"- {ing}" for ing in meal["missing_ingredients"]))
                                    
                                    # Show inventory match with color
                                    match_value = float(meal["inventory_match"])
                                    if match_value >= 90:
                                        st.success(f"Inventory Match: {match_value}%")
                                    elif match_value >= 70:
                                        st.warning(f"Inventory Match: {match_value}%")
                                    else:
                                        st.error(f"Inventory Match: {match_value}%")
                            st.write("---")
                        
                        if len(complete_days) < days:
                            st.warning(f"Note: Only {len(complete_days)} out of {days} days were generated completely. Try regenerating for the full plan.")
                    else:
                        st.error("No complete meal plans were generated. Please try again.")
                elif "error" in meal_plan:
                    st.error(f"Error: {meal_plan['error']}")
                    if "details" in meal_plan:
                        st.error(f"Details: {meal_plan['details']}")
                else:
                    st.error("Invalid meal plan format. Please try again.")
            except Exception as e:
                logger.error(f"Error generating meal plan: {str(e)}")
                st.error("Please try again with different parameters")
    
    # Shopping Recommendations
    st.write("### Shopping Recommendations")
    shopping_instructions = st.text_area(
        "Custom Instructions for Shopping List",
        placeholder="E.g., focus on organic products, budget-friendly options, bulk items, etc.",
        help="Add any specific requirements or preferences for your shopping list"
    )
    
    if st.button("Get Shopping List"):
        with st.spinner("Analyzing inventory and generating recommendations..."):
            try:
                shopping_list = await recommendation_service.get_shopping_recommendations(shopping_instructions)
                if "shopping_list" in shopping_list:
                    shopping_data = shopping_list["shopping_list"]
                    
                    # Create tabs for different types of items
                    list_tabs = st.tabs(["Meal Plan Items", "Essential Items", "Recommended Items"])
                    
                    with list_tabs[0]:
                        st.write("### Items Needed for Meal Plan")
                        meal_items = shopping_data.get("meal_plan_items", [])
                        if meal_items:
                            items_df = pd.DataFrame([{
                                "Item": item["name"],
                                "Quantity": item["quantity"],
                                "Priority": item["priority"],
                                "Reason": item.get("reason", "Required for planned meals")
                            } for item in meal_items if isinstance(item, dict) and "name" in item])
                            
                            if not items_df.empty:
                                st.dataframe(
                                    items_df.style.apply(lambda x: [
                                        'background-color: #ffcdd2' if v == "high"
                                        else 'background-color: #fff9c4' if v == "medium"
                                        else 'background-color: #c8e6c9' if v == "low"
                                        else '' for v in x
                                    ], subset=['Priority']),
                                    use_container_width=True
                                )
                            else:
                                st.info("No meal plan items needed")
                        else:
                            st.info("No meal plan items needed")
                    
                    with list_tabs[1]:
                        st.write("### Essential Items")
                        essential_items = shopping_data.get("essential_items", [])
                        if essential_items:
                            items_df = pd.DataFrame([{
                                "Item": item["name"],
                                "Quantity": item["quantity"],
                                "Priority": item["priority"],
                                "Reason": item.get("reason", "Essential item running low")
                            } for item in essential_items if isinstance(item, dict) and "name" in item])
                            
                            if not items_df.empty:
                                st.dataframe(
                                    items_df.style.apply(lambda x: [
                                        'background-color: #ffcdd2' if v == "high"
                                        else 'background-color: #fff9c4' if v == "medium"
                                        else 'background-color: #c8e6c9' if v == "low"
                                        else '' for v in x
                                    ], subset=['Priority']),
                                    use_container_width=True
                                )
                            else:
                                st.info("No essential items needed")
                        else:
                            st.info("No essential items needed")
                    
                    with list_tabs[2]:
                        st.write("### Recommended Items")
                        recommended_items = shopping_data.get("recommended_items", [])
                        if recommended_items:
                            items_df = pd.DataFrame([{
                                "Item": item["name"],
                                "Quantity": item["quantity"],
                                "Reason": item.get("reason", "Recommended for inventory optimization")
                            } for item in recommended_items if isinstance(item, dict) and "name" in item])
                            
                            if not items_df.empty:
                                st.dataframe(items_df, use_container_width=True)
                            else:
                                st.info("No recommended items")
                        else:
                            st.info("No recommended items")
                    
                    # Show summary if available
                    if any(len(items) > 0 for items in [meal_items, essential_items, recommended_items]):
                        total_items = len(meal_items) + len(essential_items) + len(recommended_items)
                        st.success(f"Generated shopping list with {total_items} items total")
                    else:
                        st.warning("No items needed at this time")
                        
                elif "error" in shopping_list:
                    st.error(f"Error: {shopping_list['error']}")
                    if "details" in shopping_list:
                        st.error(f"Details: {shopping_list['details']}")
                else:
                    st.error("Invalid shopping list format. Please try again.")
            except Exception as e:
                logger.error(f"Error generating shopping list: {str(e)}")
                st.error("Error generating shopping list. Please try again.")

if __name__ == "__main__":
    asyncio.run(main()) 