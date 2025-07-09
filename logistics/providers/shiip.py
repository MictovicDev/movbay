from typing import Dict, Any
from .base import Dispatcher
import logging

logger = logging.getLogger(__name__)



class ShiipDispatcher(Dispatcher):
    
    def __init__(self, name):
        super().__init__()
        self.name = name
        
    