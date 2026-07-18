"""Stable exception boundary for yfinance and its HTTP transport."""

import requests
from yfinance import exceptions as yf_exceptions

try:
    from curl_cffi.requests.exceptions import RequestException as CurlRequestException
except ImportError:  # pragma: no cover - older yfinance transports
    CurlRequestException = None


_exceptions = [
    requests.RequestException,
    TimeoutError,
    ConnectionError,
    ValueError,
    KeyError,
    TypeError,
    AttributeError,
    IndexError,
]
if CurlRequestException is not None:
    _exceptions.append(CurlRequestException)
for name in (
    "YFInvalidPeriodError",
    "YFNotImplementedError",
    "YFPricesMissingError",
    "YFRateLimitError",
    "YFTickerMissingError",
    "YFTzMissingError",
):
    exception_type = getattr(yf_exceptions, name, None)
    if exception_type is not None:
        _exceptions.append(exception_type)

YFINANCE_EXCEPTIONS = tuple(dict.fromkeys(_exceptions))
