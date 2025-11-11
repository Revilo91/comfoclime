# Development Container (Codespace) für ComfoClime

Diese Konfiguration ermöglicht es dir, die ComfoClime Custom Component direkt in einem GitHub Codespace oder Visual Studio Code Dev Container zu entwickeln und zu testen.

## Schnellstart

### Mit GitHub Codespaces

1. Öffne dieses Repository auf GitHub
2. Klicke auf "Code" → "Codespaces" → "Create codespace on main"
3. Warte, bis der Container gebaut und gestartet wurde
4. Home Assistant wird automatisch gestartet und ist unter Port 8123 verfügbar

### Mit Visual Studio Code (lokal)

1. Installiere die "Dev Containers" Extension in VS Code
2. Öffne dieses Repository in VS Code
3. Klicke auf die Benachrichtigung "Reopen in Container" oder nutze `Ctrl+Shift+P` → "Dev Containers: Reopen in Container"
4. Warte, bis der Container gebaut und gestartet wurde

## Home Assistant öffnen

Nach dem Start des Containers:

1. Warte auf die Benachrichtigung, dass Port 8123 weitergeleitet wurde
2. Klicke auf "Open in Browser" oder öffne manuell: `http://localhost:8123`
3. Beim ersten Start musst du einen Benutzer für Home Assistant erstellen

## ComfoClime Integration hinzufügen

### Über die UI (empfohlen)

1. Öffne Home Assistant im Browser
2. Gehe zu "Einstellungen" → "Geräte & Dienste"
3. Klicke auf "+ Integration hinzufügen"
4. Suche nach "ComfoClime" oder "Zehnder ComfoClime"
5. Gib die IP-Adresse deines ComfoClime-Geräts ein
6. Die Integration wird automatisch konfiguriert

**Wichtig:** Dein ComfoClime-Gerät muss im gleichen Netzwerk erreichbar sein oder du musst Netzwerk-Port-Forwarding einrichten.

### Manuelle Konfiguration (optional)

Du kannst die Integration auch manuell in `.devcontainer/configuration.yaml` konfigurieren:

```yaml
comfoclime:
  host: "192.168.1.XXX"  # Ersetze mit deiner ComfoClime IP
```

## Entwicklung und Debugging

### Custom Component bearbeiten

Die Custom Component befindet sich unter:
```
/workspaces/comfoclime/custom_components/comfoclime/
```

Alle Änderungen an den Python-Dateien erfordern einen Neustart von Home Assistant:
1. Im Terminal: `container restart`
2. Oder über die Home Assistant UI: "Entwickler-Werkzeuge" → "Neustart"

### Logs anschauen

**Im Container Terminal:**
```bash
container logs
```

**In Home Assistant UI:**
- Gehe zu "Einstellungen" → "System" → "Protokolle"
- Oder nutze "Entwickler-Werkzeuge" → "Protokolle"

### Debug-Logging aktivieren

Debug-Logging ist bereits in `.devcontainer/configuration.yaml` aktiviert:
```yaml
logger:
  default: info
  logs:
    custom_components.comfoclime: debug
```

### Container-Befehle

Der Home Assistant Container bietet nützliche Befehle:

```bash
# Home Assistant starten
container start

# Home Assistant stoppen
container stop

# Home Assistant neu starten
container restart

# Logs anzeigen
container logs

# In Home Assistant Core Shell wechseln
container enter
```

## Fehlersuche

### Port 8123 ist nicht erreichbar

1. Stelle sicher, dass der Container vollständig gestartet ist
2. Überprüfe die Port-Weiterleitung in VS Code (PORTS-Tab)
3. Versuche `http://localhost:8123` direkt im Browser

### ComfoClime-Gerät nicht erreichbar

1. Stelle sicher, dass das Gerät im gleichen Netzwerk ist
2. Bei Codespaces: Möglicherweise musst du VPN oder Port-Forwarding einrichten
3. Teste die Erreichbarkeit: `curl http://DEINE_IP/api/dashboard`

### Integration wird nicht geladen

1. Überprüfe die Logs: `container logs`
2. Stelle sicher, dass alle Abhängigkeiten installiert sind
3. Neustart des Containers: `container restart`

### Änderungen werden nicht übernommen

1. Stelle sicher, dass du die richtigen Dateien bearbeitest (im `/workspaces/comfoclime/` Verzeichnis)
2. Führe einen Neustart durch: `container restart`
3. Leere den Cache: Lösche `.devcontainer/.cache/` falls vorhanden

## Dateistruktur

```
.devcontainer/
├── devcontainer.json      # Container-Konfiguration
├── configuration.yaml     # Home Assistant Konfiguration
├── automations.yaml       # Test-Automatisierungen
├── scripts.yaml           # Test-Scripts
├── scenes.yaml            # Test-Szenen
└── README.md             # Diese Datei
```

## Nützliche Links

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Custom Component Tutorial](https://developers.home-assistant.io/docs/creating_component_index)
- [ComfoClime API Documentation](../ComfoClimeAPI.md)
- [Dev Container Documentation](https://code.visualstudio.com/docs/devcontainers/containers)

## Tipps

1. **Schneller Development Cycle**: Nutze `container restart` statt den ganzen Container neu zu bauen
2. **Code-Qualität**: Der Container enthält bereits Python-Linting Tools
3. **Git**: Alle Git-Befehle funktionieren normal im Container
4. **Extensions**: Nützliche VS Code Extensions werden automatisch installiert

## Beitragen

Wenn du Verbesserungen an der Dev-Container-Konfiguration hast, erstelle gerne einen Pull Request!
