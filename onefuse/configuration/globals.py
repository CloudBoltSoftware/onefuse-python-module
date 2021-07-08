from os import path

# Logging
# Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = 'DEBUG'

# OneFuse Certificate Validation
VERIFY_CERTS = False

# Returns 3 levels up from file. This allows you to 'from onefuse_python...'
ROOT_PATH = path.dirname(path.dirname(path.dirname(path.abspath(__file__))))

# Async Timeouts (in minutes)
ONEFUSE_ASYNC_TIMEOUT_NAMING = 10
ONEFUSE_ASYNC_TIMEOUT_IPAM = 10
ONEFUSE_ASYNC_TIMEOUT_DNS = 10
ONEFUSE_ASYNC_TIMEOUT_AD = 15
ONEFUSE_ASYNC_TIMEOUT_SCRIPTING = 90
ONEFUSE_ASYNC_TIMEOUT_ANSIBLETOWER = 120
ONEFUSE_ASYNC_TIMEOUT_VRA = 120
ONEFUSE_ASYNC_TIMEOUT_OTHER = 10

# Upstream Provider
UPSTREAM_VERSION = '1.3.0'

# Property Toolkit
STATIC_PROPERTY_SET_PREFIX = 'OneFuse_SPS_'  # Global Prefix
MAX_RUNS = 3
IGNORE_PROPERTIES = ["OneFuse_VRA7_Props", "OneFuse_VRA8_Props",
                     "OneFuse_TF_Props"]
UPSTREAM_PROPERTY = "OneFuse_CB_Props"
