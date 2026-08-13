class DocumentProcessingError(Exception):
    """Base class for expected document-processing failures."""


class UnsupportedFileError(DocumentProcessingError):
    pass


class CorruptedFileError(DocumentProcessingError):
    pass


class OCRProcessingError(DocumentProcessingError):
    pass


class LLMExtractionError(DocumentProcessingError):
    pass


class LLMTimeoutError(LLMExtractionError):
    pass


class MalformedLLMOutputError(LLMExtractionError):
    pass

