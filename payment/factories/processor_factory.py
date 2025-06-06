from ..processors import FlutterWaveProcessor, PayStackProcessor

class ProcessorFactory:
    
    @staticmethod
    def create_processor(processor_type, url):
        processors = {
            'flutterwave': FlutterWaveProcessor,
            'paystack': PayStackProcessor,
        }
        
        processor_class = processors.get(processor_type)
        if not processor_class:
            raise ValueError(f"Unknown processor: {processor_type}")
        
        return processor_class(url=url)