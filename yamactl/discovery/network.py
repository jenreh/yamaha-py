"""Network discovery — TCP port scan + HTTP probe for Yamaha receivers."""

from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

from yamactl.core.models import DiscoveryCandidate

_YNCA_PORT = 50000
_HTTP_PORT = 80
_TIMEOUT = 1.0
_MAX_WORKERS = 64

_PRIVATE_NETWORKS = [
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
]

_DEFAULT_SUBNETS = [
    "192.168.0.0/24",
    "192.168.1.0/24",
    "192.168.178.0/24",
    "10.0.0.0/24",
]


def _is_private(ip: str) -> bool:
    addr = ipaddress.IPv4Address(ip)
    return any(addr in net for net in _PRIVATE_NETWORKS)


def _probe_host(host: str) -> DiscoveryCandidate | None:
    ynca_ok = _tcp_probe(host, _YNCA_PORT)
    http_ok, model = _http_probe(host)
    if ynca_ok or http_ok:
        return DiscoveryCandidate(
            host=host,
            model=model,
            ynca_available=ynca_ok,
            http_available=http_ok,
        )
    return None


def _tcp_probe(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=_TIMEOUT):
            return True
    except OSError:
        return False


def _http_probe(host: str) -> tuple[bool, str | None]:
    url = f"http://{host}:{_HTTP_PORT}/YamahaRemoteControl/desc.xml"
    try:
        response = httpx.get(url, timeout=_TIMEOUT, follow_redirects=False)
        if response.status_code == 200 and "YAMAHA" in response.text.upper():
            model = _extract_model(response.text)
            return True, model
    except Exception:  # noqa: S110
        pass
    return False, None


def _extract_model(xml_text: str) -> str | None:
    import xml.etree.ElementTree as ET  # noqa: PLC0415

    try:
        root = ET.fromstring(xml_text)  # noqa: S314
        for tag in ("Model_Name", "modelName", "friendlyName"):
            el = root.find(f".//{tag}")
            if el is not None and el.text:
                return el.text.strip()
    except ET.ParseError:
        pass
    return None


def scan_subnet(
    subnet: str | None = None,
    allow_public_ip: bool = False,
) -> list[DiscoveryCandidate]:
    subnets = [subnet] if subnet else _DEFAULT_SUBNETS
    hosts: list[str] = []

    for net_str in subnets:
        try:
            network = ipaddress.IPv4Network(net_str, strict=False)
        except ValueError:
            continue
        for addr in network.hosts():
            ip = str(addr)
            if not allow_public_ip and not _is_private(ip):
                continue
            hosts.append(ip)

    candidates: list[DiscoveryCandidate] = []
    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        futures = {executor.submit(_probe_host, h): h for h in hosts}
        for future in as_completed(futures):
            result = future.result()
            if result is not None:
                candidates.append(result)

    return sorted(candidates, key=lambda c: c.host)
