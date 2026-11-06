"""Guard against committing credentials or network captures.

The device API sends the WLAN password in clear text (``PUT /wifi/update`` with
``{"ssid": ..., "psk": ...}``), so a packet capture of the manufacturer app contains it.
These tests fail if such a capture, or a literal credential, is tracked by git.
"""

import pathlib
import re
import subprocess

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

CAPTURE_SUFFIXES = {".pcap", ".pcapng", ".cap", ".har"}

# A JSON/YAML-style credential with a real-looking literal value. Placeholders such as
# "…", "<redacted>", "***" or "your-password" are too short or contain markers and pass.
CREDENTIAL_PATTERN = re.compile(
    r"""["']?(?:psk|password|passwd|wifi_password)["']?\s*[:=]\s*["']([^"'<>*…\s]{8,})["']""", re.IGNORECASE
)
INVENTED_SECRET = "correct-horse-battery"
PLACEHOLDER_HINTS = ("example", "your-", "redacted", "changeme", "placeholder", "dummy")


def find_credentials(text: str) -> list[str]:
    """Return the credential-looking values in ``text``, ignoring obvious placeholders."""
    return [
        match.group(1)
        for match in CREDENTIAL_PATTERN.finditer(text)
        if not any(hint in match.group(1).lower() for hint in PLACEHOLDER_HINTS)
    ]


def _tracked_files() -> list[pathlib.Path]:
    try:
        output = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
        ).stdout
    except OSError, subprocess.CalledProcessError:
        pytest.skip("not a git checkout")
    return [REPO_ROOT / name for name in output.decode().split("\0") if name]


class TestCredentialDetection:
    """The detector itself, with invented values."""

    # The samples are assembled from pieces so this file does not itself contain a
    # literal credential, which the repository-wide scan below would flag.
    @pytest.mark.parametrize(
        "text",
        [
            '{"ssid":"HomeNet","psk":"' + INVENTED_SECRET + '"}',
            "{'psk': '" + INVENTED_SECRET + "'}",
            'wifi_password = "' + INVENTED_SECRET + '"',
            'PSK: "' + INVENTED_SECRET.upper() + '"',
        ],
    )
    def test_literal_credentials_are_found(self, text):
        assert find_credentials(text), text

    @pytest.mark.parametrize(
        "text",
        [
            '{"ssid":"…","psk":"…"}',
            '{"psk":"<redacted>"}',
            '"psk": "********"',
            '"password": "your-password-here"',
            '"password": "short"',
            "psk = os.environ['PSK']",
            "def set_psk(psk: str) -> None:",
        ],
    )
    def test_placeholders_and_code_are_not_flagged(self, text):
        assert find_credentials(text) == [], text


class TestRepositoryIsClean:
    def test_no_capture_files_are_tracked(self):
        captures = [str(p.relative_to(REPO_ROOT)) for p in _tracked_files() if p.suffix.lower() in CAPTURE_SUFFIXES]

        assert captures == []

    def test_no_literal_credentials_in_tracked_files(self):
        leaks = {}
        for path in _tracked_files():
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError, OSError:
                continue  # binary file, e.g. images
            found = find_credentials(text)
            if found:
                # Report where, never the value itself, so a failure does not spread the secret.
                leaks[str(path.relative_to(REPO_ROOT))] = len(found)

        assert leaks == {}

    def test_gitignore_blocks_captures(self):
        patterns = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

        assert "*.pcap" in patterns
        assert "*.pcapng" in patterns
