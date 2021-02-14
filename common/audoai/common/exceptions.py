class AudoException(RuntimeError):
    """Base class for all Audo exceptions"""
    pass


class MalformedFile(AudoException):
    """Exception raised when the provided file could not be understood"""
    pass


class NoiseRemovalFailed(AudoException):
    """Raised when noise removal failed for an unknown reason"""
    pass

class Unauthorized(AudoException):
    """Raised when the provided API key is incorrect"""
    pass
