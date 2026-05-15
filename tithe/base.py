from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseSMSProvider(ABC):
    @abstractmethod
    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def send_bulk_sms(self, recipients: list) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_balance(self) -> Dict[str, Any]:
        pass