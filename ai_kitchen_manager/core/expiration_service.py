from datetime import datetime, timedelta, date
from models.expiration import ExpirationTracker, ExpirationStatus
from core.logger import logger
from sqlalchemy.orm import Session
from typing import List

class ExpirationService:
    def __init__(self, db: Session):
        self.db = db
    
    def update_expiration_statuses(self):
        """Update expiration statuses for all tracked items"""
        try:
            tracked_items = self.db.query(ExpirationTracker).all()
            
            for item in tracked_items:
                days_until_expiration = item.days_until_expiration
                
                if days_until_expiration is None:
                    continue
                
                if days_until_expiration <= 0:
                    item.status = ExpirationStatus.EXPIRED
                elif days_until_expiration <= 7:
                    item.status = ExpirationStatus.EXPIRING_SOON
                else:
                    item.status = ExpirationStatus.FRESH
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating expiration statuses: {str(e)}")
            self.db.rollback()
            return False
    
    def get_expiring_items(self, days_threshold: int = 7) -> List[ExpirationTracker]:
        """Get items expiring within the specified number of days"""
        current_date = datetime.utcnow().date()
        threshold_date = current_date + timedelta(days=days_threshold)
        
        return self.db.query(ExpirationTracker).filter(
            ExpirationTracker.expiration_date <= threshold_date,
            ExpirationTracker.status != ExpirationStatus.EXPIRED
        ).all()
    
    def get_expired_items(self) -> List[ExpirationTracker]:
        """Get all expired items"""
        return self.db.query(ExpirationTracker).filter(
            ExpirationTracker.status == ExpirationStatus.EXPIRED
        ).all()
    
    def suggest_consumption_priority(self) -> List[dict]:
        """Generate prioritized list of items to consume"""
        expiring_items = self.get_expiring_items()
        
        prioritized_items = []
        for item in expiring_items:
            prioritized_items.append({
                'item_name': item.item.name,
                'days_remaining': item.days_until_expiration,
                'quantity': item.current_quantity,
                'freshness': item.freshness_percentage,
                'priority_score': self._calculate_priority_score(item)
            })
        
        return sorted(prioritized_items, key=lambda x: x['priority_score'], reverse=True)
    
    def _calculate_priority_score(self, item: ExpirationTracker) -> float:
        """Calculate priority score based on expiration and quantity"""
        days_remaining = max(item.days_until_expiration, 0)
        freshness = item.freshness_percentage or 0
        
        # Higher score = higher priority to consume
        return (1 / (days_remaining + 1)) * 100 + (100 - freshness) * 0.5 