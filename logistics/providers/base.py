from abc import abstractmethod, ABC



class Dispatcher(ABC):
    
    @abstractmethod
    def find_ride(self):
        pass
    

       
