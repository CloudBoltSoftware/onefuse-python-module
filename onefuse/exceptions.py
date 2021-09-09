from requests.models import Response


class OneFuseError(Exception):
    """Base class for OneFuse exceptions"""

    def __init__(self, *args, **kwargs):
        self.response = kwargs.pop('response', None)
        super(OneFuseError, self).__init__(*args, **kwargs)


class BackupsUnknownError(OneFuseError):
    """Exception raised for Unknown errors with OneFuse Backups and Restores"""


class RestoreContentError(OneFuseError):
    """Exception raised when restore content cannot be created"""


class ValidationError(OneFuseError):
    """Exception raised when a OneFuse Policy Execution fails on validation"""


class RequiredParameterMissing(OneFuseError):
    """Exception raised when a required OneFuse parameter was not passed in"""


class BadRequest(OneFuseError):
    """Exception raised when a policy restore fails due to a bad payload"""


class PolicyTypeNotFound(OneFuseError):
    """Exception raised when a policy restore fails due to a bad payload"""
