from proc.processor import Processor


class Pipeline:
    def __init__(self, processor: Processor) -> None:
        self.processor = processor

    def execute(self, item: str) -> dict[str, str]:
        result = self.processor.run(item)
        return {"item": item, "result": result}
