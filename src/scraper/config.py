"""Configuration models and YAML loading."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator


class RequestDelayConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    min: float = 1.0
    max: float = 3.0

    @model_validator(mode="after")
    def min_le_max(self) -> RequestDelayConfig:
        if self.min > self.max:
            msg = f"request_delay.min ({self.min}) must be <= max ({self.max})"
            raise ValueError(msg)
        return self


class PaginationConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    type: Literal["next_page", "load_more", "infinite_scroll", "none"]
    selector: str | None = None
    max_pages: int = 100


class FieldMapping(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    selector: str
    attribute: str = "text"
    default: str | None = None


class LevelConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    depth: int
    link_selector: str | None = None
    context_selector: str | None = None
    renderer: Literal["static", "browser"] = "static"
    wait_selector: str | None = None
    pagination: PaginationConfig | None = None
    fields: list[FieldMapping]

    @field_validator("depth")
    @classmethod
    def depth_non_negative(cls, v: int) -> int:
        if v < 0:
            msg = "depth must be >= 0"
            raise ValueError(msg)
        return v

    @field_validator("fields")
    @classmethod
    def at_least_one_field(cls, v: list[FieldMapping]) -> list[FieldMapping]:
        if len(v) < 1:
            msg = "each level must have at least one field"
            raise ValueError(msg)
        return v


class SiteConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    base_url: str
    output_dir: str = "./output"
    request_delay: RequestDelayConfig = RequestDelayConfig()
    max_pages: int | None = None
    log_level: Literal["debug", "info", "warning"] = "info"

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            msg = "base_url must start with http:// or https://"
            raise ValueError(msg)
        return v


class ScrapeConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    site: SiteConfig
    levels: list[LevelConfig]

    @field_validator("levels")
    @classmethod
    def at_least_one_level(cls, v: list[LevelConfig]) -> list[LevelConfig]:
        if len(v) < 1:
            msg = "at least one level is required"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_levels(self) -> ScrapeConfig:
        names = [level.name for level in self.levels]
        if len(names) != len(set(names)):
            msg = "level names must be unique"
            raise ValueError(msg)

        depths = [level.depth for level in self.levels]
        expected = list(range(len(depths)))
        if depths != expected:
            msg = f"level depths must be sequential starting from 0, got {depths}"
            raise ValueError(msg)

        return self


def load_config(path: Path) -> ScrapeConfig:
    """Load and validate a YAML config file."""
    try:
        raw = path.read_text()
    except FileNotFoundError:
        print(f"Error: config file not found: {path}", file=sys.stderr)
        raise SystemExit(1)

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        print(f"Error: invalid YAML in {path}: {e}", file=sys.stderr)
        raise SystemExit(1)

    try:
        return ScrapeConfig.model_validate(data)
    except ValidationError as e:
        print(f"Error: config validation failed:\n{e}", file=sys.stderr)
        raise SystemExit(1)


def apply_overrides(config: ScrapeConfig, overrides: dict) -> ScrapeConfig:
    """Create a new config with CLI overrides applied. Only non-None values are applied."""
    site_updates: dict = {}
    for key in ("output_dir", "max_pages", "log_level"):
        if overrides.get(key) is not None:
            site_updates[key] = overrides[key]

    delay_min = overrides.get("delay_min")
    delay_max = overrides.get("delay_max")
    if delay_min is not None or delay_max is not None:
        new_min = delay_min if delay_min is not None else config.site.request_delay.min
        new_max = delay_max if delay_max is not None else config.site.request_delay.max
        site_updates["request_delay"] = RequestDelayConfig(min=new_min, max=new_max)

    if not site_updates:
        return config

    new_site = config.site.model_copy(update=site_updates)
    return config.model_copy(update={"site": new_site})
