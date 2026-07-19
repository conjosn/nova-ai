from utils.logger import NovaLogger

logger = NovaLogger()

class ErrorHandler:
    @staticmethod
    def handle_exception(exception, context=""):
        error_msg = f"[{context}] {type(exception).__name__}: {str(exception)}"
        logger.error(error_msg)
        return f"An error occurred: {str(exception)}"