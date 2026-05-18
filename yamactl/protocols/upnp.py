"""UPnP AVTransport helper — plays a streaming URL on the receiver's media renderer."""

from __future__ import annotations

import html as _html

import httpx

from yamactl.core.errors import CommandTimeout, ReceiverUnavailable

_UPNP_PORT = 8080
_AVT_SERVICE = "urn:schemas-upnp-org:service:AVTransport:1"
_AVT_CTRL = "/AVTransport/ctrl"


def _soap(action: str, inner: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        f"<s:Body>{inner}</s:Body>"
        "</s:Envelope>"
    ).encode()


def _didl(url: str, title: str) -> str:
    didl = (
        '<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">'
        '<item id="1" parentID="0" restricted="1">'
        f"<dc:title>{_html.escape(title)}</dc:title>"
        "<upnp:class>object.item.audioItem.audioBroadcast</upnp:class>"
        f'<res protocolInfo="http-get:*:audio/mpeg:*">{url}</res>'
        "</item></DIDL-Lite>"
    )
    return _html.escape(didl)


def _headers(action: str) -> dict[str, str]:
    return {
        "Content-Type": 'text/xml; charset="utf-8"',
        "SOAPACTION": f'"{_AVT_SERVICE}#{action}"',
    }


def _avt_action(host: str, action: str, inner: str, timeout: float) -> None:
    ctrl = f"http://{host}:{_UPNP_PORT}{_AVT_CTRL}"
    try:
        with httpx.Client(timeout=timeout) as client:
            client.post(
                ctrl, content=_soap(action, inner), headers=_headers(action)
            ).raise_for_status()
    except httpx.TimeoutException as exc:
        raise CommandTimeout(f"UPnP timeout at {host}:{_UPNP_PORT}") from exc
    except httpx.ConnectError as exc:
        raise ReceiverUnavailable(f"UPnP connect error at {host}:{_UPNP_PORT}") from exc


def pause_url(host: str, timeout: float = 8.0) -> None:
    # Streaming radio cannot be paused (no buffer); fall back to Stop.
    try:
        _avt_action(
            host,
            "Pause",
            f'<u:Pause xmlns:u="{_AVT_SERVICE}"><InstanceID>0</InstanceID></u:Pause>',
            timeout,
        )
    except httpx.HTTPStatusError:
        stop_url(host, timeout=timeout)


def stop_url(host: str, timeout: float = 8.0) -> None:
    _avt_action(
        host,
        "Stop",
        f'<u:Stop xmlns:u="{_AVT_SERVICE}"><InstanceID>0</InstanceID></u:Stop>',
        timeout,
    )


def play_url(host: str, url: str, title: str, timeout: float = 8.0) -> None:
    """Switch receiver to SERVER input is caller's responsibility before calling."""
    from yamactl.core.errors import UnexpectedResponse  # noqa: PLC0415

    # Pre-2015 Yamaha receivers cannot fetch HTTPS streams; downgrade transparently.
    stream_url = (
        url.replace("https://", "http://", 1) if url.startswith("https://") else url
    )

    ctrl = f"http://{host}:{_UPNP_PORT}{_AVT_CTRL}"
    set_body = (
        f'<u:SetAVTransportURI xmlns:u="{_AVT_SERVICE}">'
        f"<InstanceID>0</InstanceID>"
        f"<CurrentURI>{stream_url}</CurrentURI>"
        f"<CurrentURIMetaData>{_didl(stream_url, title)}</CurrentURIMetaData>"
        f"</u:SetAVTransportURI>"
    )
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(
                ctrl,
                content=_soap("SetAVTransportURI", set_body),
                headers=_headers("SetAVTransportURI"),
            )
            if r.status_code >= 400:
                raise UnexpectedResponse(
                    f"UPnP SetAVTransportURI failed (HTTP {r.status_code}): {r.text[:200]}"
                )
    except httpx.TimeoutException as exc:
        raise CommandTimeout(f"UPnP timeout at {host}:{_UPNP_PORT}") from exc
    except httpx.ConnectError as exc:
        raise ReceiverUnavailable(f"UPnP connect error at {host}:{_UPNP_PORT}") from exc

    _avt_action(
        host,
        "Play",
        f'<u:Play xmlns:u="{_AVT_SERVICE}"><InstanceID>0</InstanceID><Speed>1</Speed></u:Play>',
        timeout,
    )
