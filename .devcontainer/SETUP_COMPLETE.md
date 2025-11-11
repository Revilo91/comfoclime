# ComfoClime Dev Container Setup — Schnellstart

## ✅ Setup erfolgreich abgeschlossen!

Home Assistant wurde erfolgreich installiert. Deine ComfoClime Integration ist bereits verlinkt und bereit.

## 🚀 Home Assistant starten

**Einfachste Methode:**
```bash
bash .devcontainer/start-ha.sh
```

**Oder manuell:**
```bash
hass -c /workspaces/comfoclime/.devcontainer/ha-config
```

## 🌐 Zugriff auf Home Assistant

Nach dem Start ist Home Assistant verfügbar unter:
- **URL:** http://localhost:8123
- Beim ersten Start musst du einen Admin-Benutzer erstellen

## 📝 Integration testen

1. Home Assistant starten (siehe oben)
2. Im Browser öffnen: http://localhost:8123
3. Admin-Account erstellen
4. Gehe zu **Einstellungen** → **Geräte & Dienste** → **+ Integration hinzufügen**
5. Suche nach "ComfoClime"
6. Gib die IP-Adresse deines ComfoClime-Geräts ein

**⚠️ Wichtig:** Dein ComfoClime-Gerät muss im gleichen Netzwerk erreichbar sein!

## 🔧 Entwicklung

### Code ändern
1. Bearbeite die Dateien in `custom_components/comfoclime/`
2. Stoppe Home Assistant (Ctrl+C im Terminal)
3. Starte Home Assistant neu mit dem Skript oben

Die Custom Component ist automatisch per Symlink nach `/workspaces/comfoclime/.devcontainer/ha-config/custom_components/comfoclime` verlinkt.

### Logs ansehen
Während Home Assistant läuft, siehst du Logs direkt im Terminal. Für Debug-Logging ist in der Konfiguration bereits aktiviert:

```yaml
logger:
  default: info
  logs:
    custom_components.comfoclime: debug
```

### Konfigurationsdateien
- **Config:** `.devcontainer/ha-config/configuration.yaml`
- **Custom Component:** `custom_components/comfoclime/`

## 📦 Was wurde installiert?

- ✅ Home Assistant Core (neueste Version)
- ✅ ComfoClime Custom Component (verlinkt)
- ✅ Alle Abhängigkeiten (requests, etc.)
- ✅ Debug-Logging aktiviert

## 🐛 Troubleshooting

### Port 8123 nicht erreichbar?
- Prüfe, ob Home Assistant läuft (Terminal-Ausgabe)
- In VS Code: Öffne den "PORTS"-Tab und prüfe Port-Weiterleitung
- Teste: `curl http://localhost:8123`

### ComfoClime-Gerät nicht gefunden?
- Stelle sicher, dass das Gerät im gleichen Netzwerk ist
- Teste die Erreichbarkeit: `curl http://DEINE_IP/api/dashboard`
- Bei Codespaces können Netzwerk-Beschränkungen gelten

### Integration wird nicht geladen?
1. Prüfe Logs im Terminal
2. Stelle sicher, dass alle Dateien in `custom_components/comfoclime/` vorhanden sind
3. Neustart: Ctrl+C und `bash .devcontainer/start-ha.sh`

## 📚 Weitere Infos

- **ComfoClime API Doku:** Siehe `ComfoClimeAPI.md`
- **Dev Container Doku:** Siehe `.devcontainer/README.md`
- **Home Assistant Doku:** https://developers.home-assistant.io/

## 🎉 Viel Erfolg beim Entwickeln!
