from typing import Dict, Type, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseNotificationService
from app.utils.logging import get_logger

logger = get_logger()


class NotificationServiceRegistry:
    """Registry for mapping notification types to their service classes"""
    
    _registry: Dict[uuid.UUID, Type[BaseNotificationService]] = {}
    _code_registry: Dict[str, Type[BaseNotificationService]] = {}
    
    @classmethod
    def register(cls, notification_type_id: uuid.UUID, service_class: Type[BaseNotificationService]):
        """Register a notification service class for a specific type ID"""
        cls._registry[notification_type_id] = service_class
        logger.info(f"Registered {service_class.__name__} for notification type {notification_type_id}")
    
    @classmethod
    def register_by_code(cls, notification_code: str, service_class: Type[BaseNotificationService]):
        """Register a notification service class for a specific notification code"""
        cls._code_registry[notification_code] = service_class
        logger.info(f"Registered {service_class.__name__} for notification code {notification_code}")
    
    @classmethod
    def get_service_class(cls, notification_type_id: uuid.UUID) -> Optional[Type[BaseNotificationService]]:
        """Get the service class for a notification type ID"""
        return cls._registry.get(notification_type_id)
    
    @classmethod
    def get_service_class_by_code(cls, notification_code: str) -> Optional[Type[BaseNotificationService]]:
        """Get the service class for a notification code"""
        return cls._code_registry.get(notification_code)
    
    @classmethod
    def create_service(cls, notification_type_id: uuid.UUID, db_session: AsyncSession) -> Optional[BaseNotificationService]:
        """Create an instance of the notification service for the given type ID"""
        service_class = cls.get_service_class(notification_type_id)
        if service_class:
            return service_class(db_session)
        return None
    
    @classmethod
    def create_service_by_code(cls, notification_code: str, db_session: AsyncSession) -> Optional[BaseNotificationService]:
        """Create an instance of the notification service for the given notification code"""
        service_class = cls.get_service_class_by_code(notification_code)
        if service_class:
            return service_class(db_session)
        return None
    
    @classmethod
    def list_registered_types(cls) -> Dict[uuid.UUID, str]:
        """List all registered notification types and their class names"""
        return {
            type_id: service_class.__name__ 
            for type_id, service_class in cls._registry.items()
        }
    
    @classmethod 
    def list_registered_codes(cls) -> Dict[str, str]:
        """List all registered notification codes and their class names"""
        return {
            code: service_class.__name__
            for code, service_class in cls._code_registry.items()
        }


def notification_service(notification_code: str):
    """Decorator to automatically register notification service classes using notification code"""
    def decorator(cls: Type[BaseNotificationService]):
        # We'll need to register using the code and resolve UUID later
        NotificationServiceRegistry.register_by_code(notification_code, cls)
        return cls
    return decorator