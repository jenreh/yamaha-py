"""mDNS discovery — optional, requires zeroconf package."""

from __future__ import annotations

import time
from typing import Any

from yamactl.core.models import DiscoveryCandidate


def discover_mdns(timeout: float = 3.0) -> list[DiscoveryCandidate]:
    try:
        from zeroconf import ServiceBrowser, Zeroconf  # noqa: PLC0415
    except ImportError:
        return []

    candidates: list[DiscoveryCandidate] = []
    zc = Zeroconf()

    class Handler:
        def add_service(self, zc: Any, type_: str, name: str) -> None:  # type: ignore[no-untyped-def]
            info = zc.get_service_info(type_, name)
            if info is None:
                return
            ip = ".".join(str(b) for b in info.addresses[0]) if info.addresses else None
            if ip:
                candidates.append(
                    DiscoveryCandidate(
                        host=ip,
                        model=info.server,
                        http_available=True,
                    )
                )

        def remove_service(self, *args):  # type: ignore[no-untyped-def]
            pass

        def update_service(self, *args):  # type: ignore[no-untyped-def]
            pass

    ServiceBrowser(zc, "_http._tcp.local.", Handler())
    time.sleep(timeout)
    zc.close()
    return candidates
