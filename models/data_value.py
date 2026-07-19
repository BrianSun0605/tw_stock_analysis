from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class DataValue:
    """A displayed value together with the evidence needed to interpret it."""

    value: Any
    source: str
    observed_at: str
    fetched_at: str
    unit: str
    currency: Optional[str] = None
    status: str = "official"
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
