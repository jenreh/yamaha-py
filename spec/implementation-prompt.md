# Implementation Prompt: `yamactl` — Offline LAN CLI for Yamaha RX-V475

## Context

Build a Python CLI application called `yamactl` (project: `yamaha-py`) that controls a Yamaha RX-V475 AV receiver over the local network. No internet access at runtime. All communication is LAN-only.

The receiver is confirmed to support two local protocols:
- **YNCA over TCP port 50000** — primary, structured, supported by the `ynca>=6` Python package (RX-V475 explicitly listed)
- **Yamaha HTTP XML (YNC-style) on port 80** — fallback, POST XML to `http://<ip>/YamahaRemoteControl/ctrl`

---

## Deliverables

A fully working Python package installable with `pip install -e .` that provides:

1. A `yamactl` CLI entry point powered by Typer
2. YNCA TCP adapter (primary) using the `ynca` library
3. HTTP XML adapter (fallback) using `httpx` and stdlib `xml.etree.ElementTree`
4. Named profile config system (`~/.config/yamactl/config.yaml`)
5. Full command set (see section: CLI Command Tree)
6. Error hierarchy with stable exit codes
7. Human-readable Rich output + `--json` flag on every data-returning command
8. LAN device discovery
9. Unit tests + protocol-mocked tests

---

## Tech Stack

| Layer | Library |
|---|---|
| CLI | `typer>=0.12` + `rich>=13` |
| HTTP adapter | `httpx>=0.27` |
| YNCA adapter | `ynca>=6` |
| XML parsing | `xml.etree.ElementTree` (stdlib) |
| Config | `pyyaml>=6` + `platformdirs>=4` |
| Domain models | `pydantic>=2` |
| Discovery (optional) | `zeroconf>=0.132` |
| Testing | `pytest`, `pytest-mock`, `respx`, `ruff`, `mypy` |

---

## File Structure

```
yamaha-py/
├── pyproject.toml
├── yamactl/
│   ├── __init__.py
│   ├── cli/
│   │   ├── app.py           # root Typer app, sub-app registration
│   │   ├── power.py         # on / standby
│   │   ├── volume.py        # get / set / up / down
│   │   ├── mute.py          # on / off / toggle
│   │   ├── input_.py        # list / set
│   │   ├── sound.py         # mode / straight / direct / sleep
│   │   ├── scene.py         # load 1-4
│   │   ├── raw.py           # ynca <cmd> / xml <xml>
│   │   ├── status.py        # full status
│   │   └── config_cmds.py   # init / show / set-host / set-protocol
│   ├── core/
│   │   ├── config.py        # load/save YAML, profile resolution
│   │   ├── models.py        # ReceiverConfig, ReceiverStatus (Pydantic)
│   │   ├── service.py       # ReceiverService, adapter selection, retry
│   │   ├── ports.py         # ReceiverProtocol structural typing interface
│   │   └── errors.py        # exception hierarchy + exit code mapping
│   ├── protocols/
│   │   ├── ynca_tcp.py      # primary adapter — wraps ynca lib
│   │   └── ync_http.py      # fallback adapter — httpx + XML templates
│   ├── discovery/
│   │   ├── network.py       # TCP port 50000 scan + HTTP probe
│   │   ├── mdns.py          # zeroconf mDNS (optional import)
│   │   └── ssdp.py          # SSDP
│   └── output/
│       ├── formatters.py    # domain model → str / dict
│       └── rich_ui.py       # Rich table renderers
└── tests/
    ├── unit/
    ├── protocol_fixtures/   # canned XML + YNCA response strings
    └── integration/         # real-device tests, gated by env var
```

---

## Domain Models (`yamactl/core/models.py`)

```python
from typing import Literal
from pydantic import BaseModel, Field

PowerState = Literal["on", "standby"]
ProtocolName = Literal["ynca", "http_xml"]
ZoneName = Literal["main", "zone2"]


class ReceiverConfig(BaseModel):
    name: str
    host: str
    protocol: ProtocolName = "ynca"
    port: int | None = None
    zone: ZoneName = "main"
    timeout_seconds: float = 3.0
    retries: int = 1


class ReceiverStatus(BaseModel):
    profile: str | None = None
    host: str
    model: str | None = None
    power: PowerState | None = None
    input: str | None = None
    mute: bool | None = None
    volume_db: float | None = None  # -80.5 to +16.5, step 0.5 dB
    dsp_mode: str | None = None
    sleep_minutes: int | None = None
    raw: dict[str, str] = Field(default_factory=dict)
```

---

## Protocol Interface (`yamactl/core/ports.py`)

Use structural typing (`typing.Protocol`) so adapters are duck-typed, not inheritance-coupled.

```python
from typing import Protocol
from yamactl.core.models import ReceiverStatus, PowerState


class ReceiverProtocol(Protocol):
    def __enter__(self) -> "ReceiverProtocol": ...
    def __exit__(self, *args: object) -> None: ...
    def get_status(self) -> ReceiverStatus: ...
    def set_power(self, state: PowerState) -> None: ...
    def get_mute(self) -> bool: ...
    def set_mute(self, enabled: bool) -> None: ...
    def get_volume_db(self) -> float: ...
    def set_volume_db(self, value: float) -> None: ...
    def volume_up(self, steps: int = 1) -> None: ...
    def volume_down(self, steps: int = 1) -> None: ...
    def set_input(self, source: str) -> None: ...
    def list_inputs(self) -> list[str]: ...
    def load_scene(self, scene: int) -> None: ...
    def set_dsp_mode(self, mode: str) -> None: ...
    def set_straight(self, enabled: bool) -> None: ...
    def set_direct(self, enabled: bool) -> None: ...
    def set_sleep(self, minutes: int | None) -> None: ...
    def send_raw_ynca(self, command: str) -> str: ...
    def send_raw_xml(self, xml: str) -> str: ...
```

---

## Error Hierarchy (`yamactl/core/errors.py`)

```python
class YamaCtlError(Exception): ...
class ConfigError(YamaCtlError): ...           # exit 2
class ReceiverUnavailable(YamaCtlError): ...   # exit 10
class ReceiverBusy(YamaCtlError): ...          # exit 11
class CommandTimeout(YamaCtlError): ...         # exit 12
class InvalidInputSource(YamaCtlError): ...    # exit 20
class ProtocolUnsupported(YamaCtlError): ...   # exit 21
class UnexpectedResponse(YamaCtlError): ...    # exit 30
```

Map these in `cli/app.py` via a top-level exception handler that calls `raise typer.Exit(code=N)`.

Exit code 0 = success. Exit code 1 = unhandled/unexpected error.

---

## Service Layer (`yamactl/core/service.py`)

The service layer owns:
- Adapter selection based on config protocol field
- Volume range validation (-80.5 to +16.5 dB, step 0.5)
- Retry logic (config.retries)
- Zone routing (pass zone to adapters)

```python
class ReceiverService:
    def __init__(self, config: ReceiverConfig) -> None: ...

    @classmethod
    def from_profile(cls, profile: str | None = None) -> "ReceiverService": ...

    def _make_protocol(self) -> ReceiverProtocol:
        if self.config.protocol == "ynca":
            return YncaTcpProtocol(
                host=self.config.host,
                port=self.config.port or 50000,
                zone=self.config.zone,
                timeout=self.config.timeout_seconds,
            )
        return YncHttpProtocol(
            host=self.config.host,
            port=self.config.port or 80,
            zone=self.config.zone,
            timeout=self.config.timeout_seconds,
        )

    # All public methods open protocol as context manager, execute, close.
    def get_status(self) -> ReceiverStatus: ...
    def set_power(self, state: PowerState) -> None: ...
    def set_mute(self, enabled: bool) -> None: ...
    def get_volume_db(self) -> float: ...
    def set_volume_db(self, value: float) -> None: ...
    def volume_up(self, steps: int) -> None: ...
    def volume_down(self, steps: int) -> None: ...
    def set_input(self, source: str) -> None: ...
    def list_inputs(self) -> list[str]: ...
    def load_scene(self, scene: int) -> None: ...
    def set_dsp_mode(self, mode: str) -> None: ...
    def set_straight(self, enabled: bool) -> None: ...
    def set_direct(self, enabled: bool) -> None: ...
    def set_sleep(self, minutes: int | None) -> None: ...
    def send_raw_ynca(self, command: str) -> str: ...
    def send_raw_xml(self, xml: str) -> str: ...
```

Each method wraps the call in retry logic up to `config.retries` times, catching `CommandTimeout` and `ReceiverUnavailable`.

---

## YNCA TCP Adapter (`yamactl/protocols/ynca_tcp.py`)

Primary adapter. Wrap the `ynca` library. Do not re-implement the YNCA protocol.

```python
import ynca
from yamactl.core.models import ReceiverStatus, PowerState, ZoneName
from yamactl.core.errors import ReceiverBusy, ReceiverUnavailable


class YncaTcpProtocol:
    def __init__(self, host: str, port: int = 50000, zone: ZoneName = "main", timeout: float = 3.0) -> None:
        self._url = f"socket://{host}:{port}"
        self._zone = zone
        self._timeout = timeout
        self._api: ynca.YncaApi | None = None

    def __enter__(self) -> "YncaTcpProtocol":
        try:
            self._api = ynca.YncaApi(self._url)
            self._api.initialize()
        except Exception as exc:
            # Map ynca connection errors to yamactl errors
            raise ReceiverUnavailable(str(exc)) from exc
        return self

    def __exit__(self, *args: object) -> None:
        if self._api:
            self._api.close()
            self._api = None

    @property
    def _zone_obj(self):
        if not self._api:
            raise RuntimeError("Not connected")
        return self._api.main if self._zone == "main" else self._api.zone2

    def set_power(self, state: PowerState) -> None:
        from ynca.enums import Pwr
        self._zone_obj.pwr = Pwr.ON if state == "on" else Pwr.STANDBY

    def set_mute(self, enabled: bool) -> None:
        from ynca.enums import Mute
        self._zone_obj.mute = Mute.ON if enabled else Mute.OFF

    def get_volume_db(self) -> float:
        return float(self._zone_obj.vol)

    def set_volume_db(self, value: float) -> None:
        self._zone_obj.vol = value

    def volume_up(self, steps: int = 1) -> None:
        self._zone_obj.vol_up(steps)

    def volume_down(self, steps: int = 1) -> None:
        self._zone_obj.vol_down(steps)

    def set_input(self, source: str) -> None:
        self._zone_obj.inp = source

    def list_inputs(self) -> list[str]:
        return list(self._api.sys.inpname or [])

    def load_scene(self, scene: int) -> None:
        self._zone_obj.scene = scene

    def get_status(self) -> ReceiverStatus:
        from ynca.enums import Pwr
        z = self._zone_obj
        return ReceiverStatus(
            host=self._url,
            model=getattr(self._api.sys, "modelname", None),
            power="on" if z.pwr == Pwr.ON else "standby",
            input=str(z.inp) if z.inp else None,
            mute=z.mute is not None and str(z.mute) == "On",
            volume_db=float(z.vol) if z.vol is not None else None,
            dsp_mode=str(z.soundprg) if hasattr(z, "soundprg") and z.soundprg else None,
        )

    def set_dsp_mode(self, mode: str) -> None:
        self._zone_obj.soundprg = mode

    def set_straight(self, enabled: bool) -> None:
        from ynca.enums import Straight
        self._zone_obj.straight = Straight.ON if enabled else Straight.OFF

    def set_direct(self, enabled: bool) -> None:
        from ynca.enums import TwoChDecoder
        # YNCA uses PUREDIRMODE for direct
        self._zone_obj.puredirmode = "On" if enabled else "Off"

    def set_sleep(self, minutes: int | None) -> None:
        self._zone_obj.sleep = minutes if minutes is not None else 0

    def send_raw_ynca(self, command: str) -> str:
        # Send raw YNCA string e.g. "@MAIN:VOL=?" and return raw response
        raise NotImplementedError("Raw YNCA requires direct socket; implement via self._api internals")

    def send_raw_xml(self, xml: str) -> str:
        raise ProtocolUnsupported("Raw XML not supported on YNCA adapter; use --protocol http_xml")
```

**Adapter implementation notes:**
- Verify exact attribute names against `ynca>=6` API before finalizing (they may differ from stubs above).
- Map all `ynca` exceptions to the `YamaCtlError` hierarchy in `__enter__`.
- If YNCA reports receiver busy (one connection limit), raise `ReceiverBusy` with a helpful message.

---

## HTTP XML Adapter (`yamactl/protocols/ync_http.py`)

Fallback adapter. Direct HTTP XML, no third-party protocol library.

```python
import xml.etree.ElementTree as ET
import httpx
from yamactl.core.models import ReceiverStatus, PowerState, ZoneName
from yamactl.core.errors import ReceiverUnavailable, CommandTimeout, UnexpectedResponse


_ZONE_TAG = {"main": "Main_Zone", "zone2": "Zone_2"}


class YncHttpProtocol:
    def __init__(self, host: str, port: int = 80, zone: ZoneName = "main", timeout: float = 3.0) -> None:
        self._url = f"http://{host}:{port}/YamahaRemoteControl/ctrl"
        self._zone_tag = _ZONE_TAG[zone]
        self._client = httpx.Client(timeout=timeout)

    def __enter__(self) -> "YncHttpProtocol":
        return self

    def __exit__(self, *args: object) -> None:
        self._client.close()

    def _post(self, xml: str) -> ET.Element:
        try:
            response = self._client.post(
                self._url,
                content=xml.encode("utf-8"),
                headers={"Content-Type": "text/xml"},
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise CommandTimeout(str(exc)) from exc
        except httpx.ConnectError as exc:
            raise ReceiverUnavailable(str(exc)) from exc
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as exc:
            raise UnexpectedResponse(f"Invalid XML: {exc}") from exc
        rc = root.get("RC", "0")
        if rc != "0":
            raise UnexpectedResponse(f"Receiver RC={rc}")
        return root

    def _put(self, inner_xml: str) -> None:
        self._post(f'<YAMAHA_AV cmd="PUT"><{self._zone_tag}>{inner_xml}</{self._zone_tag}></YAMAHA_AV>')

    def _get(self, inner_xml: str) -> ET.Element:
        return self._post(f'<YAMAHA_AV cmd="GET"><{self._zone_tag}>{inner_xml}</{self._zone_tag}></YAMAHA_AV>')

    def set_power(self, state: PowerState) -> None:
        value = "On" if state == "on" else "Standby"
        self._put(f"<Power_Control><Power>{value}</Power></Power_Control>")

    def set_mute(self, enabled: bool) -> None:
        value = "On" if enabled else "Off"
        self._put(f"<Volume><Mute>{value}</Mute></Volume>")

    def get_mute(self) -> bool:
        root = self._get("<Volume><Mute>GetParam</Mute></Volume>")
        el = root.find(f".//{self._zone_tag}/Volume/Mute")
        return el is not None and el.text == "On"

    def get_volume_db(self) -> float:
        root = self._get("<Volume><Lvl><Val>GetParam</Val></Lvl></Volume>")
        el = root.find(f".//{self._zone_tag}/Volume/Lvl/Val")
        if el is None or el.text is None:
            raise UnexpectedResponse("No volume value in response")
        return int(el.text) / 10.0

    def set_volume_db(self, value: float) -> None:
        # Receiver expects value * 10 as integer string
        raw = str(int(value * 10))
        self._put(f"<Volume><Lvl><Val>{raw}</Val><Exp>1</Exp><Unit>dB</Unit></Lvl></Volume>")

    def volume_up(self, steps: int = 1) -> None:
        current = self.get_volume_db()
        self.set_volume_db(min(current + steps * 0.5, 16.5))

    def volume_down(self, steps: int = 1) -> None:
        current = self.get_volume_db()
        self.set_volume_db(max(current - steps * 0.5, -80.5))

    def set_input(self, source: str) -> None:
        self._put(f"<Input><Input_Sel>{source}</Input_Sel></Input>")

    def list_inputs(self) -> list[str]:
        # Parse desc.xml for available inputs; fallback to known RX-V475 list
        return [
            "HDMI1", "HDMI2", "HDMI3", "HDMI4",
            "AV1", "AV2", "AV3",
            "V-AUX", "AUDIO1", "AUDIO2",
            "TUNER", "USB", "NET RADIO", "SERVER", "AirPlay",
        ]

    def load_scene(self, scene: int) -> None:
        self._put(f"<Scene><Scene_Load>Scene {scene}</Scene_Load></Scene>")

    def get_status(self) -> ReceiverStatus:
        root = self._get("<Basic_Status>GetParam</Basic_Status>")
        z = root.find(f".//{self._zone_tag}")

        def _text(path: str) -> str | None:
            el = z.find(path) if z is not None else None
            return el.text if el is not None else None

        vol_raw = _text("Volume/Lvl/Val")
        return ReceiverStatus(
            host=self._url,
            power="on" if _text("Power_Control/Power") == "On" else "standby",
            input=_text("Input/Input_Sel"),
            mute=_text("Volume/Mute") == "On",
            volume_db=int(vol_raw) / 10.0 if vol_raw else None,
            dsp_mode=_text("Surround/Program_Sel"),
        )

    def set_dsp_mode(self, mode: str) -> None:
        self._put(f"<Surround><Program_Sel>{mode}</Program_Sel></Surround>")

    def set_straight(self, enabled: bool) -> None:
        value = "On" if enabled else "Off"
        self._put(f"<Surround><Straight>{value}</Straight></Surround>")

    def set_direct(self, enabled: bool) -> None:
        value = "On" if enabled else "Off"
        self._put(f"<Surround><Direct>{value}</Direct></Surround>")

    def set_sleep(self, minutes: int | None) -> None:
        value = str(minutes) if minutes is not None else "Off"
        self._put(f"<Power_Control><Sleep>{value}</Sleep></Power_Control>")

    def send_raw_xml(self, xml: str) -> str:
        root = self._post(xml)
        return ET.tostring(root, encoding="unicode")

    def send_raw_ynca(self, command: str) -> str:
        raise ProtocolUnsupported("Raw YNCA not supported on http_xml adapter; use --protocol ynca")
```

---

## Configuration (`yamactl/core/config.py`)

Default config path: `platformdirs.user_config_dir("yamactl") / "config.yaml"`

```python
from pathlib import Path
import yaml
import platformdirs
from yamactl.core.models import ReceiverConfig
from yamactl.core.errors import ConfigError


def config_path() -> Path:
    return Path(platformdirs.user_config_dir("yamactl")) / "config.yaml"


def load_profile(profile: str | None = None) -> ReceiverConfig:
    path = config_path()
    if not path.exists():
        raise ConfigError(f"No config found at {path}. Run: yamactl config init")
    with path.open() as f:
        data = yaml.safe_load(f)
    name = profile or data.get("default_profile")
    if not name:
        raise ConfigError("No default_profile set. Pass --profile NAME or run: yamactl config init")
    profiles = data.get("profiles", {})
    if name not in profiles:
        raise ConfigError(f"Profile '{name}' not found in {path}")
    return ReceiverConfig(name=name, **profiles[name])


def save_profile(cfg: ReceiverConfig, set_default: bool = False) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if path.exists():
        with path.open() as f:
            data = yaml.safe_load(f) or {}
    data.setdefault("profiles", {})[cfg.name] = cfg.model_dump(exclude={"name"})
    if set_default or "default_profile" not in data:
        data["default_profile"] = cfg.name
    with path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False)
```

Example config file (`~/.config/yamactl/config.yaml`):

```yaml
default_profile: livingroom

profiles:
  livingroom:
    host: 192.168.178.42
    protocol: ynca
    zone: main
    timeout_seconds: 3.0
    retries: 1

  livingroom-http:
    host: 192.168.178.42
    protocol: http_xml
    zone: main
    timeout_seconds: 3.0
    retries: 1
```

---

## CLI Root App (`yamactl/cli/app.py`)

```python
import typer
import rich
from yamactl.core.errors import (
    YamaCtlError, ConfigError, ReceiverUnavailable, ReceiverBusy,
    CommandTimeout, InvalidInputSource, ProtocolUnsupported, UnexpectedResponse,
)
from yamactl.cli import power, volume, mute, input_, sound, scene, raw, status, config_cmds

app = typer.Typer(no_args_is_help=True, pretty_exceptions_enable=False)
app.add_typer(power.app, name="power")
app.add_typer(volume.app, name="volume")
app.add_typer(mute.app, name="mute")
app.add_typer(input_.app, name="input")
app.add_typer(sound.app, name="sound")
app.add_typer(scene.app, name="scene")
app.add_typer(raw.app, name="raw")
app.add_typer(config_cmds.app, name="config")

_EXIT_CODES: dict[type, int] = {
    ConfigError: 2,
    ReceiverUnavailable: 10,
    ReceiverBusy: 11,
    CommandTimeout: 12,
    InvalidInputSource: 20,
    ProtocolUnsupported: 21,
    UnexpectedResponse: 30,
}


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    pass


def run() -> None:
    try:
        app()
    except YamaCtlError as exc:
        code = _EXIT_CODES.get(type(exc), 1)
        rich.print(f"[red]Error:[/red] {exc}", err=True)
        raise SystemExit(code)
```

Every sub-command module receives `--profile` and `--zone` options and constructs `ReceiverService.from_profile(profile)` with an optional zone override.

---

## CLI Command Tree (full)

```
yamactl [--profile PROFILE] [--zone main|zone2]
│
├── status          [--json]
├── discover        [--subnet CIDR]
│
├── config
│   ├── init        --name NAME --host IP [--protocol ynca|http_xml] [--zone main|zone2]
│   ├── show        [--json]
│   ├── set-host    HOST
│   └── set-protocol  ynca|http_xml
│
├── power
│   ├── on
│   └── standby
│
├── mute
│   ├── on
│   ├── off
│   └── toggle
│
├── volume
│   ├── get         [--json]
│   ├── set         DB_VALUE          # float, -80.5..+16.5
│   ├── up          [--steps N]       # default 1 step = 0.5 dB
│   └── down        [--steps N]
│
├── input
│   ├── list        [--json]
│   └── set         SOURCE
│
├── sound
│   ├── mode        MODE_NAME
│   ├── straight    on|off
│   ├── direct      on|off
│   └── sleep       MINUTES|off
│
├── scene
│   └── load        1|2|3|4
│
└── raw
    ├── ynca        COMMAND           # e.g. "@MAIN:VOL=?"
    └── xml         XML_STRING        # full YAMAHA_AV envelope
```

### Example usage

```bash
yamactl config init --name livingroom --host 192.168.178.42 --protocol ynca
yamactl status
yamactl status --json
yamactl power on
yamactl power standby
yamactl mute toggle
yamactl volume get
yamactl volume set -- -45.5
yamactl volume up --steps 4
yamactl input list
yamactl input set HDMI1
yamactl sound mode "7ch Surround"
yamactl sound straight on
yamactl sound sleep 60
yamactl scene load 3
yamactl --zone zone2 volume set -- -50.0
yamactl --profile livingroom-http raw xml '<YAMAHA_AV cmd="GET"><Main_Zone><Basic_Status>GetParam</Basic_Status></Main_Zone></YAMAHA_AV>'
```

---

## Discovery (`yamactl/discovery/network.py`)

```
yamactl discover [--subnet 192.168.178.0/24]

Flow:
1. For each host in subnet (skip broadcast/network):
   a. TCP connect attempt to port 50000 (YNCA) — mark YNCA confident if success
   b. HTTP GET http://<ip>/YamahaRemoteControl/desc.xml — mark HTTP confident if 200
2. Optionally run mDNS/SSDP scan (if zeroconf installed)
3. Print Rich table: IP | Model | YNCA | HTTP | Confidence
4. Prompt user: "Save as profile? [y/N]"
5. If yes: yamactl config init flow

Security: reject non-RFC-1918 target IPs unless --allow-public-ip flag passed.
```

---

## Output Layer (`yamactl/output/`)

`formatters.py` — converts `ReceiverStatus` to:
- `to_dict(status)` → plain dict for JSON output
- `to_plain(status)` → single-line string for piping

`rich_ui.py` — renders:
- `render_status(status)` → Rich table with power/input/volume/mute/dsp rows
- `render_inputs(inputs)` → Rich list
- `render_discovery(candidates)` → Rich table with confidence column

All CLI commands print via output layer, never format in command handlers.

---

## Testing

### Unit tests (no receiver)

- `tests/unit/test_config.py` — config load, profile resolution, missing profile errors
- `tests/unit/test_models.py` — Pydantic validation, volume range
- `tests/unit/test_service.py` — adapter selection, volume clamping, retry logic
- `tests/unit/test_xml_builder.py` — XML strings generated by `ync_http.py` match expected
- `tests/unit/test_xml_parser.py` — parse fixture XML responses to `ReceiverStatus`
- `tests/unit/test_formatters.py` — output formatting, JSON output

### Protocol-mocked tests

- `tests/protocol_fixtures/` — canned XML response strings for all commands
- Use `respx` to mock HTTP XML endpoint
- Use a fake TCP socket server to simulate YNCA responses
- Verify: connection opened and closed per command, retry behavior on timeout

### Real-device tests (opt-in)

```bash
YAMACTL_TEST_HOST=192.168.178.42 pytest -m rxv475
```

Markers:
- `rxv475` — requires real receiver
- `rxv475_destructive` — changes volume/input (run only when explicitly approved)

---

## `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "yamactl"
version = "0.1.0"
description = "Offline LAN CLI for Yamaha RX-V475 AV receiver"
requires-python = ">=3.11"
dependencies = [
  "typer>=0.12",
  "rich>=13",
  "pydantic>=2",
  "platformdirs>=4",
  "pyyaml>=6",
  "httpx>=0.27",
  "ynca>=6",
]

[project.optional-dependencies]
discovery = ["zeroconf>=0.132"]
dev = ["pytest", "pytest-mock", "respx", "ruff", "mypy"]

[project.scripts]
yamactl = "yamactl.cli.app:run"

[tool.ruff]
target-version = "py311"
line-length = 100
```

Offline install from local wheelhouse:

```bash
pip wheel -r requirements.txt -w ./wheelhouse
pip install --no-index --find-links ./wheelhouse yamactl
```

---

## Implementation Roadmap

| Phase | Scope |
|---|---|
| 1 — Foundation | `pyproject.toml`, error classes, Pydantic models, config load/save, Typer root app skeleton |
| 2 — HTTP XML adapter | `ync_http.py`: status, power, mute, volume, input, scene, raw XML. Unit + mocked tests. |
| 3 — YNCA adapter | `ynca_tcp.py`: all commands. Verify exact `ynca>=6` API. Unit + fake-socket tests. |
| 4 — Sound + Zone 2 | DSP mode, straight, direct, sleep, zone2 routing in service + both adapters |
| 5 — CLI polish | JSON output, Rich tables, exit codes, error messages, `--zone` flag |
| 6 — Discovery | Subnet TCP scan, HTTP probe, mDNS/SSDP, confidence table, save-to-profile |
| 7 — Daemon (future) | Persistent YNCA connection, Unix socket API, prevents receiver connection contention |

---

## Security and Privacy Constraints

- No telemetry. No cloud calls. No internet access at runtime.
- Reject non-RFC-1918 target IPs unless `--allow-public-ip` explicitly passed.
- Discovery requires explicit `--subnet` argument — no auto-scan.
- No credentials stored anywhere.
- Logs contain only local commands and receiver responses, not user environment.

---

## Protocol Reference

| Feature | XML path (Main_Zone) | Values |
|---|---|---|
| Power | `Power_Control/Power` | `On` / `Standby` |
| Volume | `Volume/Lvl/Val` | integer (value × 10), range -805..165 |
| Mute | `Volume/Mute` | `On` / `Off` |
| Input | `Input/Input_Sel` | `HDMI1`..`HDMI4`, `AV1`..`AV3`, `TUNER`, `USB`, `NET RADIO`, etc. |
| Scene load | `Scene/Scene_Load` | `Scene 1`..`Scene 4` |
| DSP mode | `Surround/Program_Sel` | named mode strings |
| Straight | `Surround/Straight` | `On` / `Off` |
| Direct | `Surround/Direct` | `On` / `Off` |
| Sleep | `Power_Control/Sleep` | integer minutes or `Off` |
| Zone 2 power | `Zone_2/Power_Control/Power` | same values |
| Zone 2 volume | `Zone_2/Volume/Lvl/Val` | same encoding |
| Zone 2 input | `Zone_2/Input/Input_Sel` | same values |

HTTP control endpoint: `POST http://<ip>/YamahaRemoteControl/ctrl`  
HTTP description endpoint: `GET http://<ip>/YamahaRemoteControl/desc.xml`  
YNCA endpoint: TCP socket `<ip>:50000`

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| YNCA primary, HTTP XML fallback | YNCA is structured and supported by `ynca>=6`; RX-V475 explicitly listed |
| Short-lived connections by default | YNCA receiver allows only one connection at a time |
| Named profiles in YAML | Enables multiple receivers and per-device protocol config |
| Structural `Protocol` interface | Adapters are duck-typed; no inheritance coupling |
| `-80.5` to `+16.5` dB volume range | Actual RX-V475 hardware spec, 0.5 dB steps |
| `power standby` not `power off` | Matches XML protocol value; receiver never fully powers off via network |
| `mute` as top-level group | Cleaner UX; mute is a primary operation, not a volume sub-concern |
| Stable exit codes | Enables use from shell scripts, cron, systemd, Home Assistant shell commands |
