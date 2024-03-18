class ASRException(Exception):
    """ Custom exception for ASR-related errors. """
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code