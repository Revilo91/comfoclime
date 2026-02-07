#!/bin/bash
# Lokales Linting und Formatierung mit Ruff
# Ähnlich wie die GitHub Action .github/workflows/ruff.yml
#
# Verwendung:
#   ./scripts/lint.sh          # Nur prüfen
#   ./scripts/lint.sh --fix    # Automatisch beheben

set -e  # Bei Fehler abbrechen

# Farben für Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ins Projektverzeichnis wechseln
cd "$(dirname "$0")/.."

# Parameter prüfen
FIX_MODE=false
if [[ "$1" == "--fix" || "$1" == "-f" ]]; then
    FIX_MODE=true
fi

echo -e "${YELLOW}🔍 Ruff Lint & Format Check${NC}"
echo "================================"

# Prüfen ob ruff installiert ist
if ! command -v ruff &> /dev/null; then
    echo -e "${RED}❌ Ruff ist nicht installiert.${NC}"
    echo "Installiere mit: uv tool install ruff"
    exit 1
fi

echo -e "${YELLOW}📋 Ruff Version:${NC} $(ruff --version)"

if [[ "$FIX_MODE" == true ]]; then
    echo -e "${YELLOW}🔧 Modus: Auto-Fix${NC}"

    # Formatierung
    echo -e "\n${YELLOW}📐 Formatiere...${NC}"
    ruff format .
    echo -e "${GREEN}✅ Formatierung abgeschlossen${NC}"

    # Linting mit Fix
    echo -e "\n${YELLOW}🔧 Behebe Lint-Fehler...${NC}"
    ruff check --fix --unsafe-fixes . || true

    # Nochmal prüfen
    echo -e "\n${YELLOW}🔎 Prüfe verbleibende Fehler...${NC}"
    if ruff check .; then
        echo -e "${GREEN}✅ Alle Fehler behoben${NC}"
    else
        echo -e "${YELLOW}⚠️  Einige Fehler erfordern manuelle Korrektur${NC}"
    fi
else
    echo -e "${YELLOW}🔍 Modus: Nur prüfen${NC}"

    # Format Check
    echo -e "\n${YELLOW}📐 Format Check...${NC}"
    if ruff format --check .; then
        echo -e "${GREEN}✅ Formatierung OK${NC}"
    else
        echo -e "${RED}❌ Formatierungsfehler gefunden${NC}"
        echo -e "${YELLOW}Führe './scripts/lint.sh --fix' aus, um zu beheben${NC}"
        FORMAT_FAILED=1
    fi

    # Lint Check
    echo -e "\n${YELLOW}🔎 Lint Check...${NC}"
    if ruff check .; then
        echo -e "${GREEN}✅ Linting OK${NC}"
    else
        echo -e "${RED}❌ Linting-Fehler gefunden${NC}"
        echo -e "${YELLOW}Führe './scripts/lint.sh --fix' aus, um automatisch zu beheben${NC}"
        LINT_FAILED=1
    fi

    # Zusammenfassung
    echo -e "\n================================"
    if [[ -z "$FORMAT_FAILED" && -z "$LINT_FAILED" ]]; then
        echo -e "${GREEN}✅ Alle Checks bestanden!${NC}"
        exit 0
    else
        echo -e "${RED}❌ Einige Checks fehlgeschlagen${NC}"
        exit 1
    fi
fi
