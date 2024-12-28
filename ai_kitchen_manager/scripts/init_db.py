from core.database import engine, Base
from models.inventory import InventoryItem
from models.expiration import ExpirationTracker

def init_database():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_database()
    print("Database initialized successfully!") 