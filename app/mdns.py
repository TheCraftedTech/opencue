# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
mdns.py
Netzwerk-Name der Konsole per mDNS ("Bonjour"): `http://opencue.local:8000` statt einer IP-Adresse, die sich mit jedem Netzwerk aendert.

Der Name ist immer `opencue.local`. Ein Name darf im Netzwerk nur einmal vorkommen: bevor die Konsole ihn beansprucht, fragt sie per mDNS, ob ihn schon ein anderes
Geraet (eine zweite OpenCue-Konsole, ein Mac mit diesem Namen ...) mit einer ANDEREN Adresse benutzt. Ist er belegt, nimmt sie `opencue-2.local`, dann
`opencue-3.local` usw. (ein Unterstrich waere kein gueltiger Rechnername; Browser und iPadOS lehnen ihn teils ab). Beansprucht wird erst nach dieser Pruefung.

Veroeffentlicht werden die Dienste `_http._tcp` (Port aus den Einstellungen) und `_https._tcp` (https-Port) - nur die, deren Schalter an ist - mit dem Rechnernamen
`<name>.local` und den Netzwerk-Adressen der Konsole. iPad/iPhone/Mac loesen `.local` von selbst auf, Windows ab Version 10 ebenfalls; Android je nach Geraet/Browser.

Die Namensregistrierung ist an den Netzwerk-Zugriff gekoppelt (lan_listener.py ruft `mdns.sync()` nach jedem Abgleich der Listener): ohne offenen Zugang gibt es nichts,
was ein Name erreichen koennte. Das Paket `zeroconf` ist die einzige Abhaengigkeit; fehlt es oder scheitert das Netzwerk, bleibt die Konsole wie bisher unter ihren
IP-Adressen erreichbar (`error` sagt in den Einstellungen warum).
"""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import List, Optional, Set, Tuple

logger = logging.getLogger("opencue.mdns")

BASE_NAME = "opencue"
MAX_SUFFIX = 9                          # opencue, opencue-2 ... opencue-9
PROBE_SECONDS = 1.6                     # so lange auf Antworten anderer Geraete warten (3 Anfragen im Abstand von 0,4 s)


def labels() -> List[str]:
    """Die Namen, die in Frage kommen (in Reihenfolge): opencue, opencue-2, ..."""
    return [BASE_NAME] + [f"{BASE_NAME}-{n}" for n in range(2, MAX_SUFFIX + 1)]


def host_names() -> List[str]:
    """`<name>.local` fuer alle moeglichen Namen (das https-Zertifikat gilt fuer alle)."""
    return [f"{label}.local" for label in labels()]


def _packed(ips: List[str]) -> Set[bytes]:
    out: Set[bytes] = set()
    for ip in ips:
        try:
            out.add(socket.inet_aton(ip))
        except OSError:
            continue
    return out


def _collector_class():
    """Die Listener-Klasse erbt von zeroconf (Import erst bei Bedarf: ohne das Paket bleibt die Konsole lauffaehig)."""
    from zeroconf import DNSAddress, RecordUpdateListener

    class Collector(RecordUpdateListener):
        """Sammelt Adress-Eintraege (A) zu einem Namen, die andere Geraete im Netzwerk melden."""

        def __init__(self, fqdn: str) -> None:
            self.fqdn = fqdn.lower()
            self.addresses: Set[bytes] = set()

        def async_update_records(self, zc, now, records) -> None:
            for update in records:
                record = update.new
                if isinstance(record, DNSAddress) and record.name.lower() == self.fqdn and len(record.address) == 4:
                    self.addresses.add(bytes(record.address))

        def async_update_records_complete(self) -> None:
            pass

    return Collector


def collector(fqdn: str):
    return _collector_class()(fqdn)


class Mdns:
    def __init__(self) -> None:
        self.zc = None                                         # AsyncZeroconf
        self.label: str = ""                                   # beanspruchter Name (ohne ".local"), "" = keiner
        self.error: str = ""                                   # warum es keinen Namen gibt (Paket fehlt, kein Netzwerk ...)
        self._signature: Optional[Tuple] = None
        self._lock = asyncio.Lock()
        self._services: list = []
        self.on_change = None                                  # async Funktion ohne Argumente: wird aufgerufen, wenn sich Name oder Fehler geaendert haben (die Oberflaeche zeigt es dann sofort)

    # ------------------------------------------------------------------ Abfragen
    @property
    def host(self) -> str:
        """Der beanspruchte Rechnername mit ".local" ("" = keiner)."""
        return f"{self.label}.local" if self.label else ""

    def urls(self, http_port: int, https_port: int, http_on: bool, https_on: bool) -> Tuple[List[str], List[str]]:
        """(http-Adressen, https-Adressen) unter dem Namen - leer, solange er nicht beansprucht ist."""
        if not self.label:
            return [], []
        return ([f"http://{self.host}:{http_port}"] if http_on else []), ([f"https://{self.host}:{https_port}"] if https_on else [])

    # ------------------------------------------------------------------ Name pruefen
    async def _taken(self, zc, label: str, ours: Set[bytes]) -> bool:
        """Benutzt schon ein anderes Geraet `label.local` (mit einer anderen Adresse als wir)?"""
        from zeroconf import DNSOutgoing, DNSQuestion, const
        fqdn = f"{label}.local."
        found = collector(fqdn)
        question = DNSQuestion(fqdn, const._TYPE_A, const._CLASS_IN)
        zc.zeroconf.async_add_listener(found, question)
        try:
            for _ in range(4):
                query = DNSOutgoing(const._FLAGS_QR_QUERY)
                query.add_question(question)
                zc.zeroconf.async_send(query)
                await asyncio.sleep(PROBE_SECONDS / 4)
        finally:
            zc.zeroconf.async_remove_listener(found)
        others = found.addresses - ours
        if others:
            logger.info("[MDNS] %s.local ist schon vergeben (%s)", label, ", ".join(socket.inet_ntoa(a) for a in others))
        return bool(others)

    # ------------------------------------------------------------------ Start / Stop
    async def _stop(self) -> None:
        zc, self.zc = self.zc, None
        self.label = ""
        self._services = []
        if zc is not None:
            try:
                await zc.async_unregister_all_services()
            except Exception as exc:                           # noqa: BLE001 - Abmelden darf nie etwas blockieren
                logger.debug("[MDNS] Abmelden: %s", exc)
            try:
                await zc.async_close()
            except Exception as exc:                           # noqa: BLE001
                logger.debug("[MDNS] Schliessen: %s", exc)

    async def _start(self, addresses: List[str], http_port: Optional[int], https_port: Optional[int]) -> None:
        try:
            from zeroconf import IPVersion, NonUniqueNameException, ServiceInfo
            from zeroconf.asyncio import AsyncZeroconf
        except ImportError:
            self.error = "The package 'zeroconf' is missing (pip install zeroconf) - without it there is no network name."
            return
        ours = _packed(addresses)
        if not ours:
            self.error = "No network found."
            return
        try:
            zc = AsyncZeroconf(interfaces=list(addresses), ip_version=IPVersion.V4Only)
        except Exception as exc:                               # noqa: BLE001 - Port 5353 gesperrt, kein Multicast ...
            self.error = f"mDNS not available: {exc}"
            logger.warning("[MDNS] OC-3401 %s", self.error)
            return
        self.zc = zc
        try:
            for label in labels():
                if await self._taken(zc, label, ours):
                    continue
                infos = []
                if http_port:
                    infos.append(ServiceInfo("_http._tcp.local.", f"OpenCue {label}._http._tcp.local.", port=http_port, server=f"{label}.local.",
                                             addresses=[socket.inet_aton(ip) for ip in addresses], properties={"path": "/"}))
                if https_port:
                    infos.append(ServiceInfo("_https._tcp.local.", f"OpenCue {label} (https)._https._tcp.local.", port=https_port, server=f"{label}.local.",
                                             addresses=[socket.inet_aton(ip) for ip in addresses], properties={"path": "/"}))
                try:
                    for info in infos:
                        await zc.async_register_service(info, allow_name_change=False)
                        self._services.append(info)
                except NonUniqueNameException:                 # jemand war schneller: aufraeumen, naechster Name
                    await zc.async_unregister_all_services()
                    self._services = []
                    continue
                self.label = label
                self.error = ""
                logger.info("[MDNS] erreichbar als %s.local (http %s, https %s)", label, http_port or "-", https_port or "-")
                return
            self.error = "Alle Namen von opencue.local bis opencue-%d.local sind im Netzwerk belegt." % MAX_SUFFIX
            await self._stop()
        except Exception as exc:                               # noqa: BLE001
            self.error = f"mDNS error: {exc}"
            logger.warning("[MDNS] OC-3401 %s", self.error)
            await self._stop()

    async def sync(self, force: bool = False) -> None:
        """Auf den Soll-Zustand bringen: Name an, wenn der Schalter an ist und mindestens ein Zugang (http/https) im Netzwerk lauscht. `force`: auch ohne Aenderung neu pruefen (Namen neu suchen)."""
        from app.lan_listener import lan
        from app.state_manager import state
        async with self._lock:
            addresses = sorted(set(lan.addresses) | set(lan.https_addresses))
            http_port = int(lan.server.config.port) if (state.mdns_enabled and lan.addresses and lan.server is not None) else None
            https_port = int(lan.https_port) if (state.mdns_enabled and lan.https_addresses) else None
            wanted = bool(state.mdns_enabled and (http_port or https_port))
            signature = (tuple(addresses), http_port, https_port) if wanted else None
            if not force and signature == self._signature and (not wanted or self.label or self.error):
                return
            before = (self.label, self.error)
            await self._stop()
            self._signature = signature
            self.error = ""
            if wanted:
                await self._start(addresses, http_port, https_port)
            changed = (self.label, self.error) != before
        if changed and self.on_change is not None:            # ausserhalb des Locks; auch beim Programmstart: ohne das zeigte die Oberflaeche ewig "Name wird gesucht"
            try:
                await self.on_change()
            except Exception:                                  # noqa: BLE001 - eine Anzeige darf nie die Namenssuche stoeren
                logger.debug("[MDNS] Anzeige nicht aktualisiert", exc_info=True)

    async def shutdown(self) -> None:
        async with self._lock:
            self._signature = None
            await self._stop()


mdns = Mdns()
