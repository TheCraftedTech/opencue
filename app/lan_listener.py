# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
lan_listener.py
Netzwerk-Zugriff (Remote) zur LAUFZEIT ein- und ausschalten - ohne Neustart.

Der Server (uvicorn) lauscht immer nur auf 127.0.0.1: der PyWebView-Client der Konsole ist damit immer erreichbar, und ohne Freigabe kommt aus dem
Netzwerk nichts an (der Port ist dann wirklich zu, nicht nur per Passwort geschuetzt). Ist der Remote-Zugriff eingeschaltet, kommt je Netzwerk-
Adresse der Konsole ein weiterer Listener dazu (auf demselben Port, derselben App, derselben Ereignisschleife); beim Ausschalten werden sie
wieder geschlossen. Bestehende Verbindungen beendet remote.revoke_all() / event_bus.close_remote().

Zusaetzlich lauscht jede Netzwerk-Adresse auf https (Einstellung `https_port`, Standard 8001 - neben http 8000; selbstsigniertes Zertifikat aus app/https_cert.py): Browser bieten WebXR (VR-Brille) und andere Funktionen nur in
einem sicheren Kontext an, und http://<IP> ist keiner. Fehlt das Paket `cryptography`, bleibt https aus (`https_error`), alles andere laeuft wie bisher.

Die Listener haengen sich in die laufende uvicorn-Instanz ein (create_server mit demselben Protokoll-Aufbau wie Server.startup) und stehen in
`server.servers`, damit uvicorn sie beim Beenden mit schliesst.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("opencue.lan")


class LanListeners:
    def __init__(self) -> None:
        self.server = None                                    # uvicorn.Server der Konsole (main.py haengt ihn ein)
        self.listeners: Dict[str, asyncio.base_events.Server] = {}   # IP -> Listener
        self.errors: Dict[str, str] = {}                      # IP -> Fehlertext (z. B. Port belegt)
        self.https_listeners: Dict[str, asyncio.base_events.Server] = {}   # IP -> https-Listener (Port + 1)
        self.https_error: str = ""                            # warum es keine https-Adresse gibt (z. B. Paket fehlt)
        self.https_port: int = 0                              # Port der laufenden https-Listener (0 = keiner)

    def attach(self, server) -> None:
        self.server = server

    @property
    def addresses(self) -> List[str]:
        return list(self.listeners)

    @property
    def https_addresses(self) -> List[str]:
        return list(self.https_listeners)

    def _create_protocol(self):
        server = self.server
        config = server.config

        def factory(_loop: Optional[asyncio.AbstractEventLoop] = None) -> asyncio.Protocol:
            return config.http_protocol_class(config=config, server_state=server.server_state, app_state=server.lifespan.state, _loop=_loop)

        return factory

    async def _close_https(self, ip: str) -> None:
        secure = self.https_listeners.pop(ip, None)
        if secure is None:
            return
        if self.server is not None and secure in getattr(self.server, "servers", []):
            self.server.servers.remove(secure)
        secure.close()
        logger.info("[REMOTE] https-Listener %s beendet", ip)

    async def _close(self, ip: str) -> None:
        """Den http-Listener dieser Adresse schliessen (https hat seinen eigenen Schalter: _close_https)."""
        listener = self.listeners.pop(ip, None)
        if listener is None:
            return
        if self.server is not None and listener in getattr(self.server, "servers", []):
            self.server.servers.remove(listener)
        listener.close()
        logger.info("[REMOTE] Netzwerk-Listener %s beendet", ip)

    async def sync(self, enabled: bool, addresses: Optional[List[str]] = None) -> None:
        """Listener auf den Soll-Zustand bringen: ausgeschaltet = keiner, eingeschaltet = einer je Netzwerk-Adresse (`addresses` ueberschreibt die erkannten)."""
        server = self.server
        if server is None or not getattr(server, "started", False):
            return
        if addresses is None and enabled:
            from app.remote import lan_addresses
            addresses = lan_addresses()
        from app.state_manager import state
        found = list(addresses or []) if enabled else []
        wanted = found if state.http_enabled else []                       # http und https sind getrennte Schalter
        port = server.config.port
        for ip in list(self.listeners):
            if ip not in wanted:
                await self._close(ip)
        self.errors = {}
        loop = asyncio.get_running_loop()
        for ip in wanted:
            if ip in self.listeners:
                continue
            try:
                listener = await loop.create_server(self._create_protocol(), host=ip, port=port, backlog=server.config.backlog)
            except OSError as exc:
                self.errors[ip] = str(exc)
                logger.warning("[REMOTE] OC-3402 %s:%s nicht erreichbar gemacht: %s", ip, port, exc)
                continue
            self.listeners[ip] = listener
            server.servers.append(listener)
            logger.info("[REMOTE] erreichbar unter http://%s:%s", ip, port)
        await self._sync_https(found if state.https_enabled else [], port)
        from app.mdns import mdns
        await mdns.sync()                                                  # Netzwerk-Name (opencue.local) folgt den Listenern

    async def _sync_https(self, wanted: List[str], port: int) -> None:
        """https-Listener neben den http-Listenern: einer je Adresse auf dem Port aus den Einstellungen, solange ein Zertifikat erstellt werden kann. Aenderungen (Port, ein/aus) gelten sofort."""
        from app.state_manager import state
        server = self.server
        target = int(state.https_port)
        self.https_error = ""
        for ip in list(self.https_listeners):                                                           # Port gewechselt, Adresse weggefallen oder https abgeschaltet: schliessen
            if self.https_port != target or ip not in wanted:
                await self._close_https(ip)
        self.https_port = target
        if not wanted:
            return
        if target == port:
            self.https_error = f"Der https-Port {target} ist derselbe wie der http-Port - bitte einen anderen waehlen."
            return
        from app.https_cert import ssl_context
        context, error = ssl_context(wanted)
        if context is None:
            self.https_error = error
            return
        loop = asyncio.get_running_loop()
        for ip in wanted:
            if ip in self.https_listeners:
                continue
            try:
                secure = await loop.create_server(self._create_protocol(), host=ip, port=target, backlog=server.config.backlog, ssl=context)
            except OSError as exc:
                self.errors[ip + " (https)"] = str(exc)
                logger.warning("[REMOTE] OC-3402 https %s:%s nicht erreichbar gemacht: %s", ip, self.https_port, exc)
                continue
            self.https_listeners[ip] = secure
            server.servers.append(secure)
            logger.info("[REMOTE] erreichbar unter https://%s:%s (selbstsigniert, fuer erweiterte Browser-Funktionen wie VR)", ip, self.https_port)

    async def sync_when_started(self, enabled: bool, timeout: float = 15.0) -> None:
        """Nach dem Start des Servers (Lifespan-Start ist vor dem Binden des Ports): erst warten, dann einrichten."""
        if self.server is None:
            return
        waited = 0.0
        while not getattr(self.server, "started", False) and waited < timeout:
            await asyncio.sleep(0.05)
            waited += 0.05
        await self.sync(enabled)


lan = LanListeners()
