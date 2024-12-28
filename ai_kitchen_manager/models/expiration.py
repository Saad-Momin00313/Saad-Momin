from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Float, Boolean, Date
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime, timedelta, date
import enum

class ExpirationStatus(enum.Enum):
    FRESH = "fresh"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"

class ExpirationTracker(Base):
    __tablename__ = "expiration_tracking"
    
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"))
    initial_quantity = Column(Float)
    current_quantity = Column(Float)
    purchase_date = Column(DateTime, default=datetime.utcnow)
    expiration_date = Column(Date)
    status = Column(Enum(ExpirationStatus))
    notification_sent = Column(Boolean, default=False)
    
    item = relationship("InventoryItem", back_populates="expiration_tracking")
    
    @property
    def days_until_expiration(self):
        if self.expiration_date:
            return (self.expiration_date - datetime.utcnow().date()).days
        return None
    
    @property
    def freshness_percentage(self):
        if not self.expiration_date or not self.purchase_date:
            return None
        
        purchase_date = self.purchase_date.date()
        total_shelf_life = (self.expiration_date - purchase_date).days
        remaining_life = (self.expiration_date - datetime.utcnow().date()).days
        
        return (remaining_life / total_shelf_life) * 100 if total_shelf_life > 0 else 0 