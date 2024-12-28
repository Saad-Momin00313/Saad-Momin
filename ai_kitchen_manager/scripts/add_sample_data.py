from core.database import get_db
from models.inventory import InventoryItem
from datetime import datetime, timedelta, date

def add_sample_data():
    db = next(get_db())
    
    # Sample inventory items
    sample_items = [
        {
            "name": "Rice",
            "quantity": 2.0,
            "unit": "kilograms",
            "category": "grains",
            "expiration_date": date.today() + timedelta(days=180)
        },
        {
            "name": "Chicken",
            "quantity": 0.5,
            "unit": "kilograms",
            "category": "meat",
            "expiration_date": date.today() + timedelta(days=2)
        },
        {
            "name": "Tomatoes",
            "quantity": 4.0,
            "unit": "units",
            "category": "produce",
            "expiration_date": date.today() + timedelta(days=5)
        },
        {
            "name": "Milk",
            "quantity": 1.0,
            "unit": "liters",
            "category": "dairy",
            "expiration_date": date.today() + timedelta(days=7)
        },
        {
            "name": "Onions",
            "quantity": 3.0,
            "unit": "units",
            "category": "produce",
            "expiration_date": date.today() + timedelta(days=14)
        }
    ]
    
    try:
        # Clear existing items
        db.query(InventoryItem).delete()
        
        # Add items to database
        for item_data in sample_items:
            item = InventoryItem(**item_data)
            db.add(item)
        
        db.commit()
        print("Sample data added successfully!")
        
    except Exception as e:
        print(f"Error adding sample data: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    add_sample_data() 