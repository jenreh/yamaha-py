"""Domain models — protocol-independent data structures."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PowerState = Literal["on", "standby"]
ProtocolName = Literal["ynca", "http_xml"]
ZoneName = Literal["main", "zone2"]
TunerBand = Literal["FM", "AM"]

VOLUME_MIN = -80.5
VOLUME_MAX = 16.5
VOLUME_STEP = 0.5

DSP_MODES: list[str] = [
    "Hall in Munich",
    "Hall in Vienna",
    "Hall in Amsterdam",
    "Church in Freiburg",
    "Church in Royaumont",
    "Chamber",
    "Village Vanguard",
    "Warehouse Loft",
    "Cellar Club",
    "The Roxy Theatre",
    "The Bottom Line",
    "Sports",
    "Action Game",
    "Roleplaying Game",
    "Music Video",
    "Standard",
    "Spectacle",
    "Sci-Fi",
    "Adventure",
    "Drama",
    "Mono Movie",
    "2ch Stereo",
    "5ch Stereo",
    "7ch Stereo",
    "Surround Decoder",
]


class ReceiverConfig(BaseModel):
    name: str
    host: str
    protocol: ProtocolName = "ynca"
    port: int | None = None
    zone: ZoneName = "main"
    timeout_seconds: float = 3.0
    retries: int = 1
    netradio_presets: dict[str, str] = Field(default_factory=dict)
    netradio_last: str | None = None


class ReceiverStatus(BaseModel):
    profile: str | None = None
    host: str
    model: str | None = None
    power: PowerState | None = None
    input: str | None = None
    mute: bool | None = None
    volume_db: float | None = None
    dsp_mode: str | None = None
    sleep_minutes: int | None = None
    raw: dict[str, str] = Field(default_factory=dict)


class NetRadioListEntry(BaseModel):
    line: int
    text: str
    attribute: str  # Container, Item, Unselectable


class NetRadioListInfo(BaseModel):
    layer: int | None = None
    layer_name: str | None = None
    current_line: int | None = None
    max_line: int | None = None
    entries: list[NetRadioListEntry] = Field(default_factory=list)


class NetRadioStatus(BaseModel):
    available: bool | None = None
    playback: str | None = None
    station: str | None = None
    song: str | None = None
    album: str | None = None
    elapsed_time: str | None = None


class TunerStatus(BaseModel):
    band: str | None = None
    fm_freq_mhz: float | None = None
    am_freq_khz: int | None = None
    preset: str | None = None
    fm_mode: str | None = None
    rds_station: str | None = None
    tuned: bool | None = None


class DiscoveryCandidate(BaseModel):
    host: str
    model: str | None = None
    ynca_available: bool = False
    http_available: bool = False

    @property
    def confidence(self) -> str:
        if self.ynca_available and self.http_available:
            return "high"
        if self.ynca_available or self.http_available:
            return "medium"
        return "low"

    @property
    def protocol(self) -> ProtocolName:
        return "ynca" if self.ynca_available else "http_xml"
