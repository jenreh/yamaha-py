# yamaha-py

![Version](https://img.shields.io/badge/version-0.2.0-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE.md)
[![Python](https://img.shields.io/badge/python-3.14%2B-orange)](https://www.python.org)

**yamaha-py** talks directly to your Yamaha AV receiver over the local network — no cloud, no Yamaha account, no internet required.

---

## Features

- **Pure local control** — two protocols: YNCA over TCP (port 50000) and HTTP XML (Yamaha Remote Control API)
- **Rich CLI** — human-readable output or `--json` for scripting and pipes
- **Multi-profile config** — manage multiple receivers, each with host, protocol, zone, timeout, and retries
- **Zone support** — control `main` and `zone2` independently
- **Net Radio** — stream URLs via UPnP; manage presets per profile
- **Tuner** — FM/AM band, frequency, RDS, presets
- **Receiver discovery** — parallel `/24` subnet scan with optional profile save
- **Stable exit codes** — every error maps to a predictable shell exit code

---

## Installation

```bash
pip install yamaha-py
# or with uv
uv add yamaha-py
```

Requires Python 3.14+.

> [!NOTE]
> For mDNS discovery, install the optional dependency:
>
> ```bash
> pip install "yamaha-py[discovery]"
> ```

---

## Quick start

### 1. Create a profile

```bash
yamactl config init --name livingroom --host 192.168.178.42 --protocol ynca
```

### 2. Check the receiver

```bash
yamactl status
```

```text
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Receiver Status                ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Host       192.168.178.42      │
│ Model      RX-V475             │
│ Power      on                  │
│ Input      HDMI1               │
│ Volume     -45.0 dB            │
│ Mute       off                 │
│ DSP        5ch Stereo          │
└────────────────────────────────┘
```

### 3. Control it

```bash
yamactl power on
yamactl volume set -- -40
yamactl volume up --steps 4
yamactl input set HDMI2
yamactl mute toggle
yamactl scene load 1
```

---

## CLI reference

```text
yamactl [--profile NAME] [--zone main|zone2] [--json]
```

### Status & discovery

| Command | Description |
| --- | --- |
| `yamactl status` | Full receiver status |
| `yamactl discover --subnet 192.168.178.0/24` | Scan subnet for Yamaha receivers |

### Power

| Command | Description |
| --- | --- |
| `yamactl power on` | Power on |
| `yamactl power standby` | Standby |
| `yamactl power toggle` | Toggle power state |

### Volume

| Command | Description |
| --- | --- |
| `yamactl volume get` | Get current volume in dB |
| `yamactl volume set <dB>` | Set absolute volume (use `-- -48` for negative) |
| `yamactl volume up [--steps N]` | Increase by N × 0.5 dB |
| `yamactl volume down [--steps N]` | Decrease by N × 0.5 dB |

### Input & sound

| Command | Description |
| --- | --- |
| `yamactl input set <source>` | Switch input (HDMI1, AV1, NET RADIO, …) |
| `yamactl input list` | List available inputs |
| `yamactl sound dsp <mode>` | Set DSP / surround mode |
| `yamactl sound straight on\|off` | Straight mode |
| `yamactl sound sleep <minutes>` | Sleep timer (or `off`) |

### Tuner

| Command | Description |
| --- | --- |
| `yamactl tuner status` | Band, frequency, RDS |
| `yamactl tuner band fm\|am` | Switch band |
| `yamactl tuner freq <MHz>` | Set FM frequency |
| `yamactl tuner preset <N>` | Load preset |

### Net Radio

| Command | Description |
| --- | --- |
| `yamactl netradio status` | Now-playing info |
| `yamactl netradio play <name>` | Play a saved URL preset |
| `yamactl netradio stop` | Stop playback |
| `yamactl netradio url add <name> <url>` | Save a streaming URL preset |
| `yamactl netradio url list` | List saved URL presets |
| `yamactl netradio url remove <name>` | Remove a URL preset |

### Config management

| Command | Description |
| --- | --- |
| `yamactl config init --name NAME --host IP` | Create or update a profile |
| `yamactl config show` | Show all profiles |
| `yamactl config set-default --name NAME` | Change default profile |

### Diagnostics

| Command | Description |
| --- | --- |
| `yamactl raw ynca "@MAIN:VOL=?"` | Send raw YNCA command |
| `yamactl raw xml "<YAMAHA_AV ...>"` | Send raw HTTP XML envelope |

Use `--json` for machine-readable output on any read command. All log output goes to stderr; stdout stays scriptable.

### Exit codes

| Code | Error |
| --- | --- |
| `0` | success |
| `2` | config / usage error |
| `10` | receiver unreachable |
| `11` | receiver busy (YNCA port in use) |
| `12` | command timeout |
| `20` | invalid input source |
| `21` | operation unsupported by protocol |
| `30` | unexpected receiver response |

---

## Protocols

yamaha-py supports two protocol adapters, selectable per profile:

| Protocol | `--protocol` | Port | Notes |
| --- | --- | --- | --- |
| YNCA (default) | `ynca` | 50000 (TCP) | Full bidirectional control via the ynca library |
| HTTP XML | `http_xml` | 80 (HTTP) | Yamaha Remote Control API; no extra dependency |

> [!TIP]
> YNCA gives richer status feedback and is the recommended choice. Use `http_xml` if YNCA port 50000 is blocked on your network.

---

## Configuration

Config file: `~/.config/yamaha-local/config.yaml`

```yaml
default_profile: livingroom
profiles:
  livingroom:
    host: 192.168.178.42
    protocol: ynca
    zone: main
    timeout_seconds: 3.0
    retries: 1
    netradio_presets:
      wdr3: "http://wdr-wdr3-live.icecastssl.wdr.de/wdr/wdr3/live/128/stream.mp3"
      swr2: "http://swr-swr2-live.icecast.t-systems.de/swr/swr2/live/128/stream.mp3"
```

Precedence: `--profile` flag > `default_profile` > first profile in file.

---

## Development

```bash
git clone https://github.com/jenreh/yamaha-py
cd yamaha-py
uv sync
task test    # pytest with coverage
task lint    # ruff
task format  # ruff format
```

> [!NOTE]
> Real-device integration tests require a reachable receiver. Set `YAMACTL_TEST_HOST=<IP>` and run `pytest -m rxv475`.
