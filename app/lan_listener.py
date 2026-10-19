"""
lan_listener.py
Netzwerk-Zugriff (Remote) zur LAUFZEIT ein- und ausschalten - ohne Neustart.

Der Server (uvicorn) lauscht immer nur auf 127.0.0.1: der PyWebView-Client der Konsole ist damit immer erreichbar, und ohne Freigabe kommt aus dem
Netzwerk nichts an (der Port ist dann wirklich zu, nicht nur per Passwort geschuetzt). Ist der Remote-Zugriff eingeschaltet, kommt je Netzwerk-
Adresse der Konsole ein weiterer Listener dazu (auf demselben Port, derselben App, derselben Ereignisschleife); beim Ausschalten werden sie
wieder geschlossen. Bestehende Verbindungen beendet remote.revoke_all() / event_bus.close_remote().

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

    def attach(self, server) -> None:
        self.server = server

    @property
    def addresses(self) -> List[str]:
        return list(self.listeners)

    def _create_protocol(self):
        server = self.server
        config = server.config

        def factory(_loop: Optional[asyncio.AbstractEventLoop] = None) -> asyncio.Protocol:
            return config.http_protocol_class(config=config, server_state=server.server_state, app_state=server.lifespan.state, _loop=_loop)

        return factory

    async def _close(self, ip: str) -> None:
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
        wanted = list(addresses or []) if enabled else []
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
                logger.warning("[REMOTE] %s:%s nicht erreichbar gemacht: %s", ip, port, exc)
                continue
            self.listeners[ip] = listener
            server.servers.append(listener)
            logger.info("[REMOTE] erreichbar unter http://%s:%s", ip, port)

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
