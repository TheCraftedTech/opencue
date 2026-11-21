# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
https_cert.py
Zertifikate fuer die https-Adresse des Netzwerk-Zugriffs (Remote).

Browser bieten manche Funktionen nur in einem "sicheren Kontext" an - fuer OpenCue vor allem WebXR (VR-Brille), den Service Worker der installierten Web-App (iPad),
das Wachhalten des Bildschirms und Mikrofon / Kamera. Ein sicherer Kontext ist https:// oder localhost; http://<IP-im-Netzwerk> zaehlt nicht. Deshalb lauscht die Konsole
bei eingeschaltetem Remote zusaetzlich auf https (Port + 1, siehe lan_listener.py).

Aufbau (seit 2026-11): eine EIGENE ZERTIFIZIERUNGSSTELLE ("OpenCue Local CA", `https/ca.pem` + `ca-key.pem`, einmal erstellt, 10 Jahre gueltig) unterschreibt das Server-Zertifikat
(`https/cert.pem` + `key.pem`, gilt fuer localhost und alle erkannten Netzwerk-Adressen / -Namen und wird bei neuer IP-Adresse oder kurz vor dem Ablauf neu ausgestellt).
Warum nicht nur ein selbst unterschriebenes Zertifikat: iOS vertraut einer "Ausnahme" (Weiter trotz Warnung) nur im Safari-Tab - eine zum Home-Bildschirm hinzugefuegte Web-App bleibt
weiss, und der Service Worker wird nicht zugelassen. Wer die CA EINMAL auf dem Geraet installiert und ihr vertraut, hat dauerhaft ein gueltiges https - auch wenn sich die IP-Adresse
des Rechners aendert (das Server-Zertifikat wird neu ausgestellt, die CA bleibt). Die CA darf per Namensbeschraenkung nur .local, localhost und private Adressbereiche beglaubigen.
Der Download steht unter /remote/opencue.mobileconfig (iPad / iPhone: Profil) und /remote/opencue-ca.crt (Android, Windows, macOS).

Das Paket `cryptography` erzeugt die Zertifikate; fehlt es, bleibt https aus (die Konsole sagt es in den Einstellungen) und alles andere funktioniert wie bisher.
"""

from __future__ import annotations

import datetime
import ipaddress
import logging
import plistlib
import ssl
import uuid
from pathlib import Path
from typing import Iterable, Optional, Tuple

logger = logging.getLogger("opencue.https")

VALID_DAYS = 800              # iOS verlangt hoechstens 825 Tage (von "gueltig ab" bis "gueltig bis"; "gueltig ab" liegt 1 Tag zurueck)
CA_DAYS = 3650
RENEW_BEFORE_DAYS = 30
CA_NAME = "OpenCue Local CA"


def _folder() -> Path:
    from app import paths
    folder = Path(paths.get_data_root()) / "https"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _expires(cert) -> datetime.datetime:
    try:
        return cert.not_valid_after_utc
    except AttributeError:                                   # aeltere cryptography-Versionen
        return cert.not_valid_after.replace(tzinfo=datetime.timezone.utc)


def _dns_names() -> list:
    """Namen im Zertifikat: localhost und die moeglichen Netzwerk-Namen (opencue.local, opencue-2.local ...; siehe app/mdns.py)."""
    from app.mdns import host_names
    return ["localhost"] + host_names()


# ---- Die eigene Zertifizierungsstelle --------------------------------------------------------------------------

def _create_ca(ca_path: Path, ca_key_path: Path):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, CA_NAME), x509.NameAttribute(NameOID.ORGANIZATION_NAME, "OpenCue")])
    now = datetime.datetime.now(datetime.timezone.utc)
    networks = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16", "127.0.0.0/8", "::1/128", "fe80::/10", "fc00::/7"]
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=CA_DAYS))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False, data_encipherment=False, key_agreement=False,
                                     key_cert_sign=True, crl_sign=True, encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        # Die Stelle darf nur Namen im lokalen Netz beglaubigen (nicht kritisch: ein Geraet, das das nicht kennt, ignoriert es statt das Zertifikat abzulehnen)
        .add_extension(x509.NameConstraints(
            permitted_subtrees=[x509.DNSName("local"), x509.DNSName("localhost")] + [x509.IPAddress(ipaddress.ip_network(n)) for n in networks],
            excluded_subtrees=None), critical=False)
    )
    cert = builder.sign(key, hashes.SHA256())
    ca_key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    ca_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    logger.info("[HTTPS] neue Zertifizierungsstelle '%s' erstellt", CA_NAME)
    return cert, key


def _load_ca():
    """(Zertifikat, Schluessel) der eigenen Stelle; wird beim ersten Mal erstellt. Eine abgelaufene oder beschaedigte wird ersetzt (dann muss sie auf den Geraeten neu installiert werden)."""
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    folder = _folder()
    ca_path, ca_key_path = folder / "ca.pem", folder / "ca-key.pem"
    if ca_path.is_file() and ca_key_path.is_file():
        try:
            cert = x509.load_pem_x509_certificate(ca_path.read_bytes())
            key = serialization.load_pem_private_key(ca_key_path.read_bytes(), password=None)
            if _expires(cert) - datetime.datetime.now(datetime.timezone.utc) > datetime.timedelta(days=RENEW_BEFORE_DAYS):
                return cert, key
        except Exception:
            logger.warning("[HTTPS] Zertifizierungsstelle beschaedigt - wird neu erstellt")
    return _create_ca(ca_path, ca_key_path)


def ca_certificate():
    """Das Zertifikat der eigenen Stelle (cryptography-Objekt) oder None (nicht erstellt / Paket fehlt)."""
    try:
        from cryptography import x509
        path = _folder() / "ca.pem"
        return x509.load_pem_x509_certificate(path.read_bytes()) if path.is_file() else None
    except Exception:
        return None


def ca_der() -> Optional[bytes]:
    cert = ca_certificate()
    if cert is None:
        return None
    from cryptography.hazmat.primitives import serialization
    return cert.public_bytes(serialization.Encoding.DER)


def ca_fingerprint() -> str:
    """SHA-256-Fingerabdruck der Stelle (hex, mit Doppelpunkten) - zum Vergleichen auf dem Geraet (Einstellungen -> Info -> Zertifikatsvertrauen)."""
    cert = ca_certificate()
    if cert is None:
        return ""
    from cryptography.hazmat.primitives import hashes
    raw = cert.fingerprint(hashes.SHA256()).hex().upper()
    return ":".join(raw[i:i + 2] for i in range(0, len(raw), 2))


def mobileconfig() -> Optional[bytes]:
    """Konfigurationsprofil fuer iPad / iPhone: installiert die Stelle als Stammzertifikat (danach unter Einstellungen -> Allgemein -> Info -> Zertifikatsvertrauen einschalten)."""
    der = ca_der()
    if der is None:
        return None
    seed = ca_fingerprint().replace(":", "")[:32]
    cert_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "opencue-ca-cert-" + seed)).upper()
    profile_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, "opencue-ca-profile-" + seed)).upper()
    payload = {
        "PayloadContent": [{
            "PayloadCertificateFileName": "OpenCue-Local-CA.cer",
            "PayloadContent": der,
            "PayloadDescription": "OpenCue Local CA",
            "PayloadDisplayName": CA_NAME,
            "PayloadIdentifier": "app.opencue.ca." + seed[:16].lower(),
            "PayloadType": "com.apple.security.root",
            "PayloadUUID": cert_uuid,
            "PayloadVersion": 1,
        }],
        "PayloadDescription": "Vertraut der OpenCue-Zertifizierungsstelle, damit die https-Adresse von OpenCue ohne Warnung und als App funktioniert.",
        "PayloadDisplayName": "OpenCue",
        "PayloadIdentifier": "app.opencue.profile." + seed[:16].lower(),
        "PayloadOrganization": "OpenCue",
        "PayloadRemovalDisallowed": False,
        "PayloadType": "Configuration",
        "PayloadUUID": profile_uuid,
        "PayloadVersion": 1,
    }
    return plistlib.dumps(payload, fmt=plistlib.FMT_XML)


# ---- Das Server-Zertifikat ---------------------------------------------------------------------------------------

def _covers(cert, wanted: set, ca_cert) -> bool:
    """Gilt das Zertifikat noch lange genug, ist es von unserer Stelle unterschrieben und gilt es fuer alle gewuenschten Adressen?"""
    from cryptography import x509
    if _expires(cert) - datetime.datetime.now(datetime.timezone.utc) < datetime.timedelta(days=RENEW_BEFORE_DAYS):
        return False
    try:
        cert.verify_directly_issued_by(ca_cert)
    except Exception:
        return False                                         # alt (selbst unterschrieben) oder von einer ersetzten Stelle
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
    except x509.ExtensionNotFound:
        return False
    have = {str(ip) for ip in san.get_values_for_type(x509.IPAddress)}
    have_dns = set(san.get_values_for_type(x509.DNSName))
    return wanted.issubset(have) and set(_dns_names()).issubset(have_dns)


def _create(cert_path: Path, key_path: Path, ips: set, ca_cert, ca_key) -> None:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "OpenCue")])
    now = datetime.datetime.now(datetime.timezone.utc)
    names = [x509.DNSName(dns) for dns in _dns_names()] + [x509.IPAddress(ipaddress.ip_address(ip)) for ip in sorted(ips)]
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=VALID_DAYS))
        .add_extension(x509.SubjectAlternativeName(names), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=False, data_encipherment=False, key_agreement=False,
                                     key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)       # iOS verlangt "Serverauthentifizierung"
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    # Die Datei enthaelt auch die Stelle: so bekommt der Browser die ganze Kette
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM) + ca_cert.public_bytes(serialization.Encoding.PEM))
    logger.info("[HTTPS] neues Zertifikat fuer %s", ", ".join(sorted(ips)))


def ssl_context(addresses: Iterable[str]) -> Tuple[Optional[ssl.SSLContext], str]:
    """(Kontext, "") oder (None, Fehlertext). `addresses`: die Netzwerk-Adressen der Konsole."""
    try:
        import cryptography  # noqa: F401
    except ImportError:
        return None, "The package 'cryptography' is missing (pip install cryptography) - without it there is no https address."
    wanted = {"127.0.0.1"}
    for ip in addresses:
        try:
            ipaddress.ip_address(ip)
            wanted.add(ip)
        except ValueError:
            continue
    try:
        folder = _folder()
        cert_path, key_path = folder / "cert.pem", folder / "key.pem"
        ca_cert, ca_key = _load_ca()
        regenerate = True
        if cert_path.is_file() and key_path.is_file():
            from cryptography import x509
            try:
                regenerate = not _covers(x509.load_pem_x509_certificate(cert_path.read_bytes()), wanted, ca_cert)
            except Exception:                                # beschaedigt: neu erstellen
                regenerate = True
        if regenerate:
            _create(cert_path, key_path, wanted, ca_cert, ca_key)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(str(cert_path), str(key_path))
        return context, ""
    except Exception as exc:                                 # Datei-/Zertifikatsfehler: https bleibt aus, der Rest laeuft
        logger.warning("[HTTPS] nicht verfuegbar: %s", exc)
        return None, f"https not available: {exc}"
