from sqlalchemy import Column, Integer, String, Float, DateTime, Date
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime, timedelta, date
from models.expiration import ExpirationTracker
from typing import Optional

class InventoryItem(Base):
    __tablename__ = "inventory_items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    quantity = Column(Float)
    unit = Column(String)
    expiration_date = Column(Date)
    category = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add relationship to ExpirationTracker
    expiration_tracking = relationship("ExpirationTracker", back_populates="item", cascade="all, delete-orphan")

    # Unit conversion mappings
    VOLUME_CONVERSIONS = {
        'ml': {'l': 0.001, 'cups': 0.00416667},
        'l': {'ml': 1000, 'cups': 4.16667},
        'cups': {'ml': 240, 'l': 0.24}
    }
    
    WEIGHT_CONVERSIONS = {
        'g': {'kg': 0.001, 'oz': 0.035274},
        'kg': {'g': 1000, 'oz': 35.274},
        'oz': {'g': 28.3495, 'kg': 0.0283495}
    }

    LOW_STOCK_THRESHOLDS = {
        'default': 5,
        'spices': 100,  # in grams
        'dairy': 2,     # in units
        'produce': 3    # in units
    }

    @property
    def is_expired(self) -> bool:
        """Check if the item is expired."""
        if not self.expiration_date:
            return False
        expiration_datetime = datetime.combine(self.expiration_date, datetime.min.time())
        return datetime.utcnow() > expiration_datetime

    @property
    def days_until_expiration(self) -> Optional[int]:
        """Calculate days until expiration."""
        if not self.expiration_date:
            return None
        # Convert expiration_date to datetime at midnight UTC
        expiration_datetime = datetime.combine(self.expiration_date, datetime.min.time())
        delta = expiration_datetime - datetime.utcnow()
        return max(0, delta.days)

    @property
    def is_low_stock(self) -> bool:
        """Check if the item is running low on stock."""
        threshold = self.LOW_STOCK_THRESHOLDS.get(self.category, self.LOW_STOCK_THRESHOLDS['default'])
        return self.quantity <= threshold

    def convert_quantity(self, to_unit: str) -> Optional[float]:
        """Convert quantity to a different unit."""
        if self.unit == to_unit:
            return self.quantity

        # Check volume conversions
        if self.unit in self.VOLUME_CONVERSIONS and to_unit in self.VOLUME_CONVERSIONS[self.unit]:
            return self.quantity * self.VOLUME_CONVERSIONS[self.unit][to_unit]

        # Check weight conversions
        if self.unit in self.WEIGHT_CONVERSIONS and to_unit in self.WEIGHT_CONVERSIONS[self.unit]:
            return self.quantity * self.WEIGHT_CONVERSIONS[self.unit][to_unit]

        return None

    def update_quantity(self, amount: float, operation: str = 'add') -> None:
        """Update item quantity with validation."""
        if operation == 'add':
            self.quantity += amount
        elif operation == 'subtract':
            if self.quantity - amount < 0:
                raise ValueError("Cannot reduce quantity below 0")
            self.quantity -= amount
        self.updated_at = datetime.utcnow()

    def will_expire_soon(self, days_threshold: int = 7) -> bool:
        """Check if item will expire within the specified number of days."""
        if not self.expiration_date:
            return False
        expiration_datetime = datetime.combine(self.expiration_date, datetime.min.time())
        threshold_date = datetime.utcnow() + timedelta(days=days_threshold)
        return datetime.utcnow() <= expiration_datetime <= threshold_date

    def get_storage_duration(self) -> Optional[int]:
        """Get the duration this item has been in storage in days."""
        return (datetime.utcnow() - self.created_at).days

    def __str__(self) -> str:
        """String representation of the inventory item."""
        status = []
        if self.is_expired:
            status.append("EXPIRED")
        elif self.will_expire_soon():
            status.append(f"Expires in {self.days_until_expiration} days")
        if self.is_low_stock:
            status.append("LOW STOCK")
        
        status_str = f" ({', '.join(status)})" if status else ""
        return f"{self.name}: {self.quantity} {self.unit}{status_str}"