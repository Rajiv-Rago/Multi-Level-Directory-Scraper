"""Validation collector for accumulating warnings and stats across pipeline stages."""

import time
from dataclasses import dataclass, field


@dataclass
class ValidationCollector:
    warnings: list[dict] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)

    def add_warning(self, field_name: str, value: str, reason: str, source_url: str):
        self.warnings.append({
            "field": field_name,
            "value": value,
            "reason": reason,
            "source_url": source_url,
        })

    def add_stat(self, key: str, count: int):
        self.stats[key] = self.stats.get(key, 0) + count

    @property
    def duration_seconds(self) -> float:
        return time.time() - self.start_time
