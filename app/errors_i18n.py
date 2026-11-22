# Copyright (C) 2026 Samuel Zenker
# SPDX-License-Identifier: GPL-3.0-or-later
"""
errors_i18n.py
Uebersetzungen fuer das Fehlerfenster (app/error_window.py) in die sechs Sprachen von OpenCue (en, de, fr, nl, it, es).
Das Fehlerfenster erscheint oft VOR dem Start der Oberflaeche und kann daher keine Sprachdateien der Oberflaeche laden; die Texte stehen deshalb hier,
ohne weitere Abhaengigkeiten. Die Sprache wird direkt aus der Einstellungsdatei (app_config.json, Schluessel "language") gelesen; ist sie nicht lesbar
(z. B. Datenordner unbenutzbar), gilt Englisch. Der Text, der mit "Copy details" in die Zwischenablage kommt, bleibt immer Englisch (Fehlerberichte).

Neuer Fehlercode mit Fenster: Eintrag in errors.CATALOG (Englisch) UND hier in CODES (alle fuenf anderen Sprachen) ergaenzen.
"""
from __future__ import annotations

import json
from typing import Dict, Optional, Tuple

LANGUAGES = ("en", "de", "fr", "nl", "it", "es")

# Knoepfe und feste Beschriftungen: Schluessel = englischer Text (so steht er im Code)
UI: Dict[str, Dict[str, str]] = {
    "Close": {"de": "Schließen", "fr": "Fermer", "nl": "Sluiten", "it": "Chiudi", "es": "Cerrar"},
    "Copy details": {"de": "Details kopieren", "fr": "Copier les détails", "nl": "Details kopiëren", "it": "Copia i dettagli", "es": "Copiar los detalles"},
    "Open log folder": {"de": "Log-Ordner öffnen", "fr": "Ouvrir le dossier des journaux", "nl": "Logmap openen", "it": "Apri la cartella dei log", "es": "Abrir la carpeta de registros"},
    "Open log file": {"de": "Log-Datei öffnen", "fr": "Ouvrir le fichier journal", "nl": "Logbestand openen", "it": "Apri il file di log", "es": "Abrir el archivo de registro"},
    "Open download page": {"de": "Download-Seite öffnen", "fr": "Ouvrir la page de téléchargement", "nl": "Downloadpagina openen", "it": "Apri la pagina di download", "es": "Abrir la página de descarga"},
    "Start anyway": {"de": "Trotzdem starten", "fr": "Démarrer quand même", "nl": "Toch starten", "it": "Avvia comunque", "es": "Iniciar de todos modos"},
    "ERROR CODE": {"de": "FEHLERCODE", "fr": "CODE D'ERREUR", "nl": "FOUTCODE", "it": "CODICE ERRORE", "es": "CÓDIGO DE ERROR"},
}

# Fehlercodes mit Fenster (1xxx, 2xxx): code -> sprache -> (Titel, Text). Platzhalter wie im englischen Katalog ({port}).
CODES: Dict[str, Dict[str, Tuple[str, str]]] = {
    "OC-1001": {
        "de": ("OpenCue läuft bereits", "Auf diesem Computer kann nur ein OpenCue gleichzeitig laufen. Ein geöffnetes Fenster wurde in den Vordergrund geholt. Falls Sie OpenCue gerade erst geschlossen haben, beendet es sich vielleicht noch: Warten Sie ein paar Sekunden und starten Sie es erneut."),
        "fr": ("OpenCue est déjà en cours d'exécution", "Une seule instance d'OpenCue peut fonctionner à la fois sur cet ordinateur. Une fenêtre ouverte a été amenée au premier plan. Si vous venez de fermer OpenCue, il est peut-être encore en train de se terminer : attendez quelques secondes et relancez-le."),
        "nl": ("OpenCue draait al", "Op deze computer kan maar één OpenCue tegelijk draaien. Een geopend venster is naar voren gehaald. Hebt u OpenCue net gesloten, dan is het misschien nog bezig met afsluiten: wacht een paar seconden en start het opnieuw."),
        "it": ("OpenCue è già in esecuzione", "Su questo computer può essere in esecuzione un solo OpenCue alla volta. Una finestra aperta è stata portata in primo piano. Se hai appena chiuso OpenCue, potrebbe essere ancora in chiusura: attendi qualche secondo e riavvialo."),
        "es": ("OpenCue ya se está ejecutando", "En este ordenador solo puede ejecutarse un OpenCue a la vez. Se ha traído al primer plano una ventana abierta. Si acabas de cerrar OpenCue, quizá aún se esté cerrando: espera unos segundos y vuelve a iniciarlo."),
    },
    "OC-1002": {
        "de": ("Netzwerk-Port {port} wird bereits verwendet",
               "OpenCue braucht diesen Port für seinen eingebauten Server, aber ein anderes Programm belegt ihn. Schließen Sie dieses Programm und starten Sie OpenCue erneut. "
               "Um einen anderen Port zu verwenden, ändern Sie \"server_port\" in der unten angezeigten Einstellungsdatei."),
        "fr": ("Le port réseau {port} est déjà utilisé",
               "OpenCue a besoin de ce port pour son serveur intégré, mais un autre programme l'utilise. Fermez ce programme et relancez OpenCue. "
               "Pour utiliser un autre port, modifiez \"server_port\" dans le fichier de paramètres indiqué ci-dessous."),
        "nl": ("Netwerkpoort {port} is al in gebruik",
               "OpenCue heeft deze poort nodig voor de ingebouwde server, maar een ander programma gebruikt hem. Sluit dat programma en start OpenCue opnieuw. "
               "Om een andere poort te gebruiken, wijzigt u \"server_port\" in het hieronder getoonde instellingenbestand."),
        "it": ("La porta di rete {port} è già in uso",
               "OpenCue ha bisogno di questa porta per il suo server integrato, ma un altro programma la sta usando. Chiudete quel programma e riavviate OpenCue. "
               "Per usare un'altra porta, modificate \"server_port\" nel file delle impostazioni indicato qui sotto."),
        "es": ("El puerto de red {port} ya está en uso",
               "OpenCue necesita este puerto para su servidor integrado, pero otro programa lo está usando. Cierre ese programa y vuelva a iniciar OpenCue. "
               "Para usar otro puerto, cambie \"server_port\" en el archivo de ajustes que se muestra abajo."),
    },
    "OC-1003": {
        "de": ("Microsoft Edge WebView2 Runtime nicht gefunden",
               "OpenCue braucht die kostenlose Microsoft Edge WebView2 Runtime, um sein Fenster anzuzeigen, aber sie wurde auf diesem Computer nicht gefunden. "
               "Sie können die Download-Seite öffnen oder trotzdem starten, falls Sie glauben, dass dies ein Irrtum ist."),
        "fr": ("Microsoft Edge WebView2 Runtime introuvable",
               "OpenCue a besoin du composant gratuit Microsoft Edge WebView2 Runtime pour afficher sa fenêtre, mais il n'a pas été trouvé sur cet ordinateur. "
               "Vous pouvez ouvrir la page de téléchargement, ou démarrer quand même si vous pensez qu'il s'agit d'une erreur."),
        "nl": ("Microsoft Edge WebView2 Runtime niet gevonden",
               "OpenCue heeft de gratis Microsoft Edge WebView2 Runtime nodig om zijn venster te tonen, maar die is op deze computer niet gevonden. "
               "U kunt de downloadpagina openen, of toch starten als u denkt dat dit een vergissing is."),
        "it": ("Microsoft Edge WebView2 Runtime non trovato",
               "OpenCue ha bisogno del componente gratuito Microsoft Edge WebView2 Runtime per mostrare la propria finestra, ma non è stato trovato su questo computer. "
               "Potete aprire la pagina di download, oppure avviare comunque se pensate che sia un errore."),
        "es": ("No se encontró Microsoft Edge WebView2 Runtime",
               "OpenCue necesita el componente gratuito Microsoft Edge WebView2 Runtime para mostrar su ventana, pero no se encontró en este ordenador. "
               "Puede abrir la página de descarga o iniciar de todos modos si cree que se trata de un error."),
    },
    "OC-1004": {
        "de": ("Der OpenCue-Datenordner kann nicht verwendet werden",
               "OpenCue konnte seinen Datenordner nicht anlegen oder beschreiben und kann daher keine Einstellungen, Shows oder Logs speichern. Prüfen Sie, ob der Ordner existiert, "
               "das Laufwerk nicht voll oder schreibgeschützt ist und Ihr Konto dort schreiben darf."),
        "fr": ("Le dossier de données d'OpenCue est inutilisable",
               "OpenCue n'a pas pu créer son dossier de données ni y écrire, et ne peut donc pas enregistrer de paramètres, de shows ni de journaux. Vérifiez que le dossier existe, "
               "que le lecteur n'est ni plein ni en lecture seule et que votre compte a le droit d'y écrire."),
        "nl": ("De gegevensmap van OpenCue kan niet worden gebruikt",
               "OpenCue kon zijn gegevensmap niet aanmaken of beschrijven en kan dus geen instellingen, shows of logs opslaan. Controleer of de map bestaat, "
               "of de schijf niet vol of alleen-lezen is en of uw account daar mag schrijven."),
        "it": ("La cartella dei dati di OpenCue non è utilizzabile",
               "OpenCue non è riuscito a creare la propria cartella dei dati o a scriverci, quindi non può salvare impostazioni, show o log. Controllate che la cartella esista, "
               "che l'unità non sia piena o in sola lettura e che il vostro account possa scriverci."),
        "es": ("No se puede usar la carpeta de datos de OpenCue",
               "OpenCue no pudo crear su carpeta de datos ni escribir en ella, por lo que no puede guardar ajustes, shows ni registros. Compruebe que la carpeta existe, "
               "que la unidad no está llena ni es de solo lectura y que su cuenta puede escribir allí."),
    },
    "OC-2001": {
        "de": ("OpenCue konnte nicht starten", "Ein unerwarteter Fehler hat OpenCue beim Start angehalten. Bitte kopieren Sie die Details und fügen Sie sie einem Fehlerbericht bei."),
        "fr": ("OpenCue n'a pas pu démarrer", "Une erreur inattendue a arrêté OpenCue pendant son démarrage. Veuillez copier les détails et les joindre à un rapport de bogue."),
        "nl": ("OpenCue kon niet starten", "Een onverwachte fout heeft OpenCue tijdens het starten gestopt. Kopieer de details en voeg ze toe aan een foutrapport."),
        "it": ("OpenCue non è riuscito ad avviarsi", "Un errore imprevisto ha fermato OpenCue durante l'avvio. Copiate i dettagli e includeteli in una segnalazione di errore."),
        "es": ("OpenCue no pudo iniciarse", "Un error inesperado detuvo OpenCue durante el inicio. Copie los detalles e inclúyalos en un informe de errores."),
    },
    "OC-2002": {
        "de": ("Eine Hintergrundaufgabe ist fehlgeschlagen",
               "OpenCue läuft weiter, aber im Hintergrund ist etwas schiefgegangen. Wenn sich etwas seltsam verhält, speichern Sie Ihre Show und starten Sie OpenCue neu. "
               "Bitte kopieren Sie die Details für einen Fehlerbericht."),
        "fr": ("Une tâche en arrière-plan a échoué",
               "OpenCue fonctionne toujours, mais quelque chose s'est mal passé en arrière-plan. Si quelque chose se comporte de façon étrange, enregistrez votre show et redémarrez OpenCue. "
               "Veuillez copier les détails pour un rapport de bogue."),
        "nl": ("Een achtergrondtaak is mislukt",
               "OpenCue draait nog, maar op de achtergrond is iets misgegaan. Als er iets vreemd gedrag vertoont, sla dan uw show op en start OpenCue opnieuw. "
               "Kopieer de details voor een foutrapport."),
        "it": ("Un'attività in background non è riuscita",
               "OpenCue è ancora in esecuzione, ma in background qualcosa è andato storto. Se qualcosa si comporta in modo strano, salvate lo show e riavviate OpenCue. "
               "Copiate i dettagli per una segnalazione di errore."),
        "es": ("Una tarea en segundo plano ha fallado",
               "OpenCue sigue en marcha, pero algo salió mal en segundo plano. Si algo se comporta de forma extraña, guarde su show y reinicie OpenCue. "
               "Copie los detalles para un informe de errores."),
    },
    "OC-2003": {
        "de": ("Der OpenCue-Server wurde angehalten",
               "Der eingebaute Server von OpenCue wurde unerwartet angehalten oder nicht gestartet, daher kann das Fenster nicht arbeiten. OpenCue wird geschlossen. "
               "Bitte kopieren Sie die Details und fügen Sie sie einem Fehlerbericht bei."),
        "fr": ("Le serveur d'OpenCue s'est arrêté",
               "Le serveur intégré d'OpenCue s'est arrêté de façon inattendue ou n'a pas démarré, la fenêtre ne peut donc pas fonctionner. OpenCue va se fermer. "
               "Veuillez copier les détails et les joindre à un rapport de bogue."),
        "nl": ("De OpenCue-server is gestopt",
               "De ingebouwde server van OpenCue is onverwacht gestopt of niet gestart, dus het venster kan niet werken. OpenCue wordt gesloten. "
               "Kopieer de details en voeg ze toe aan een foutrapport."),
        "it": ("Il server di OpenCue si è fermato",
               "Il server integrato di OpenCue si è fermato inaspettatamente o non è stato avviato, quindi la finestra non può funzionare. OpenCue verrà chiuso. "
               "Copiate i dettagli e includeteli in una segnalazione di errore."),
        "es": ("El servidor de OpenCue se ha detenido",
               "El servidor integrado de OpenCue se detuvo de forma inesperada o no se inició, por lo que la ventana no puede funcionar. OpenCue se cerrará. "
               "Copie los detalles e inclúyalos en un informe de errores."),
    },
    "OC-2004": {
        "de": ("OpenCue wurde unerwartet beendet",
               "Ein unerwarteter Fehler ist aufgetreten und OpenCue muss sich schließen. Nicht gespeicherte Änderungen können verloren gehen. "
               "Bitte kopieren Sie die Details und fügen Sie sie einem Fehlerbericht bei."),
        "fr": ("OpenCue s'est arrêté de façon inattendue",
               "Une erreur inattendue s'est produite et OpenCue doit se fermer. Les modifications non enregistrées peuvent être perdues. "
               "Veuillez copier les détails et les joindre à un rapport de bogue."),
        "nl": ("OpenCue is onverwacht gestopt",
               "Er is een onverwachte fout opgetreden en OpenCue moet sluiten. Niet-opgeslagen wijzigingen kunnen verloren gaan. "
               "Kopieer de details en voeg ze toe aan een foutrapport."),
        "it": ("OpenCue si è arrestato inaspettatamente",
               "Si è verificato un errore imprevisto e OpenCue deve chiudersi. Le modifiche non salvate possono andare perse. "
               "Copiate i dettagli e includeteli in una segnalazione di errore."),
        "es": ("OpenCue se detuvo inesperadamente",
               "Se produjo un error inesperado y OpenCue tiene que cerrarse. Los cambios sin guardar pueden perderse. "
               "Copie los detalles e inclúyalos en un informe de errores."),
    },
}


def current_language() -> str:
    """Sprache aus der Einstellungsdatei; Englisch, wenn sie nicht lesbar oder unbekannt ist. Darf nie eine Ausnahme werfen (laeuft im Fehlerfall)."""
    try:
        from app import paths as _paths
        with open(_paths.APP_CONFIG_PATH, "r", encoding="utf-8") as fh:
            lang = json.load(fh).get("language")
        return lang if lang in LANGUAGES else "en"
    except Exception:
        return "en"


def ui(text: str, lang: Optional[str] = None) -> str:
    """Beschriftung des Fensters in der Sprache (Englisch, wenn es keine Uebersetzung gibt)."""
    lang = lang or current_language()
    return UI.get(text, {}).get(lang, text)


def code_text(code: str, title: str, message: str, lang: Optional[str] = None) -> Tuple[str, str]:
    """Titel und Text fuer `code` in der Sprache; die englischen (title, message) gelten, wenn es keine Uebersetzung gibt."""
    lang = lang or current_language()
    return CODES.get(code, {}).get(lang, (title, message))
