# Video-Editing 2.0

Schnitt-Pipeline für **Joe x PSGOTRICH** – läuft in Claude-Code-Cloud-Sessions, also auch vom **Handy**
(Claude-App → Code → dieses Repo). Footage kommt aus Google Drive, Entwürfe gehen zurück nach
`JOE X PSGOTRICH/02_Entwürfe/`. Der Projektstand (Kontext, Schnittplan, Transkripte, Schnitt-Specs)
liegt versioniert in `edits/`, damit jede Session – Handy oder Mac – nahtlos weitermacht.

## Benutzung (Handy)
Neue Session in diesem Repo starten und z. B. schreiben:
- „Neues Joe PS Video, Upload liegt in *Samstag shit*“
- „Reel 02 vom Samstag: Hook kürzer, Titel *SCHADE.*“
- „Mach von Kiel eine Hard-Edit-Version mit dem Song aus 05_Musik“

Claude nutzt dafür die Skills `neues-video` und `reel-bauen` und die Regeln in `CLAUDE.md`.

## Einrichtung (einmalig, ~5 Minuten am Mac)
1. Drive-Token erzeugen (am Mac, mit dem Google-Konto, dem der Ordner gehört):
   ```bash
   brew install rclone
   rclone authorize "drive"
   ```
   Browser öffnet sich → anmelden → im Terminal erscheint ein JSON-Block `{"access_token": …}`.
2. In claude.ai/code → Cloud-Environment dieses Repos → **Bearbeiten** → Umgebungsvariablen/Secrets:
   - `GDRIVE_TOKEN` = der komplette JSON-Block
   - optional `ELEVENLABS_API_KEY` = Scribe-Transkription mit Sprecher-Erkennung (wie bisher lokal);
     ohne Key wird lokal mit Whisper transkribiert (ohne Sprecher-Tags)
3. Netzwerkzugriff des Environments muss Google-APIs, `downloads.rclone.org` und PyPI erlauben
   (Standard „Vollzugriff“ bzw. die Hosts freigeben).
4. Neue Session starten – der SessionStart-Hook (`scripts/setup.sh`) installiert rclone + faster-whisper und
   verbindet Drive automatisch.

## Lokal am Mac
```bash
brew install ffmpeg rclone && pip3 install faster-whisper
rclone config   # Remote "gdrive" vom Typ drive anlegen
python3 -m vedit status
```

## Befehle
| Befehl | Was passiert |
|---|---|
| `python3 -m vedit status` | Überblick Drive: Eingang, Entwürfe, neue/laufende Uploads |
| `python3 -m vedit neu "<Ordner>" <YYYY-MM-DD> <Name>` | Footage holen, Archiv-IDs, Proxys, Transkript |
| `python3 -m vedit vorschau <event> [nr…]` | schnelle 540p-Vorschau aus Proxys |
| `python3 -m vedit render <event> [nr…]` | finaler Export (1080×1920 / 1920×1080, HDR→SDR, −14 LUFS) |
| `python3 -m vedit hochladen <event> [--vorschau]` | Exporte + Kontext + Schnittplan nach `02_Entwürfe/<event>/` |

## Was gegenüber dem lokalen System optimiert ist
- **Ein ffmpeg-Durchlauf pro Video** (Schnitt, Reframing, Titel, Untertitel, Loudness) – keine Zwischen-Encodes.
- **Proxys + Vorschau-Renders**: Schnitt prüfen in Sekunden, Originale (4K/HDR) nur für den Final-Render und nur die benötigten Shots.
- **Stabile Archiv-IDs** `JP-YYMMDD-NN` nach Aufnahmezeit; Nachladen bei noch laufendem Upload ohne Umnummerieren.
- **Untertitel automatisch** aus Wort-Zeitstempeln auf die Schnitt-Timeline gemappt.
- **Deklarative Specs** (`schnitt.json`) statt `specs.py`/`build.py` pro Event – am Handy lesbar und von Claude leicht änderbar.
- **Projektstand in Git** statt nur auf dem Mac.
