from abc import ABC, abstractmethod



# Abstract base class for logistics services
class LogisticsService(ABC):
    @abstractmethod
    def deliver(self, package_id: str) -> str:
        pass

# Concrete implementations for each logistics aspect
class MovbayExpress(LogisticsService):
    def deliver(self, package_id: str) -> str:
        return f"MovbayExpress: Delivering package {package_id} with express shipping."


class SpeedyDispatch(LogisticsService):
    
    def deliver(self, package_id: str) -> str:
        return f"SpeedyDispatch: Dispatching package {package_id} with high-speed delivery."


class PickupHub(LogisticsService):
    def deliver(self, package_id: str) -> str:
        return f"PickupHub: Package {package_id} ready for pickup at the hub."
    

# Factory class to create logistics service instances
class LogisticsFactory:
    @staticmethod
    def get_logistics_service(service_type: str) -> LogisticsService:
        service_type = service_type.lower()
        if service_type == "movbay_express":
            return MovbayExpress()
        elif service_type == "speedy_dispatch":
            return SpeedyDispatch()
        elif service_type == "pickup_hub":
            return PickupHub()
        else:
            raise ValueError(f"Unknown logistics service type: {service_type}")