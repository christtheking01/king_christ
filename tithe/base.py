from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseSMSProvider(ABC):
    """Abstract base class for all SMS providers"""
    
    @abstractmethod
    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS to a single number"""
        pass
    
    @abstractmethod
    def send_bulk_sms(self, recipients: list) -> Dict[str, Any]:
        """Send SMS to multiple numbers"""
        pass
    
    @abstractmethod
    def get_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        pass