from providers import ShiipDispatcher, MovbayDispatcher

class DispatchFactory:
    """Dispatch Factory to create a Dispatch Method"""
    

    def __init__(self, delivery_method):
        if delivery_method == 'MovBay_Dispatch':
            self.rider = MovbayDispatcher()
        if delivery_method == 'Speedy_Dispatch':
            self.rider = ShiipDispatcher()
            