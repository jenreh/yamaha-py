"""SSDP discovery — multicast UPnP device search."""

from __future__ import annotations

import socket

from yamactl.core.models import DiscoveryCandidate

_SSDP_ADDR = "239.255.255.250"
_SSDP_PORT = 1900
_SSDP_MX = 2
_MSEARCH = (
    "M-SEARCH * HTTP/1.1\r\n"
    f"HOST: {_SSDP_ADDR}:{_SSDP_PORT}\r\n"
    'MAN: "ssdp:discover"\r\n'
    f"MX: {_SSDP_MX}\r\n"
    "ST: ssdp:all\r\n"
    "\r\n"
)


def discover_ssdp(timeout: float = 3.0) -> list[DiscoveryCandidate]:
    candidates: list[DiscoveryCandidate] = []
    seen: set[str] = set()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.settimeout(timeout)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

    try:
        sock.sendto(_MSEARCH.encode(), (_SSDP_ADDR, _SSDP_PORT))
        while True:
            try:
                data, addr = sock.recvfrom(4096)
                ip = addr[0]
                if ip in seen:
                    continue
                text = data.decode(errors="ignore")
                if "yamaha" in text.lower():
                    seen.add(ip)
                    model = _extract_model(text)
                    candidates.append(
                        DiscoveryCandidate(
                            host=ip,
                            model=model,
                            http_available=True,
                        )
                    )
            except TimeoutError:
                break
    finally:
        sock.close()

    return candidates


def _extract_model(response: str) -> str | None:
    for line in response.splitlines():
        if line.lower().startswith("server:"):
            return line.split(":", 1)[1].strip()
    return None
