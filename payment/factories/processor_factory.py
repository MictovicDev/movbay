from ..processors import FlutterwaveProcessor, PaystackProcessor

class ProcessorFactory:
    @staticmethod
    def create_processor(processor_type):
        processors = {
            'flutterwave': FlutterwaveProcessor,
            'paystack': PaystackProcessor,
        }
        
        processor_class = processors.get(processor_type)
        if not processor_class:
            raise ValueError(f"Unknown processor: {processor_type}")
        
        return processor_class()