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

## Einrichtung Drive (einmalig, komplett am Handy, ~10 Min)
Browser am Handy auf **Desktop-Ansicht** stellen, eingeloggt als **info.yngkid@gmail.com**.

**A) Eigener Google-Zugang (Google Cloud Console)** – console.cloud.google.com
1. Oben Projekt-Auswahl → **Neues Projekt** → Name `video-editing` → Erstellen.
2. Suche „Google Drive API“ → **Aktivieren**.
3. Menü → APIs & Dienste → **OAuth-Zustimmungsbildschirm** (bzw. „Google Auth Platform“) → Starten:
   App-Name `video-editing`, deine E-Mail, Zielgruppe **Extern** → Erstellen.
4. Dort unter **Zielgruppe** → **App veröffentlichen** → Status „In Produktion“.
   Wichtig: im Status „Test“ läuft der Zugang nach 7 Tagen ab.
5. **Clients** → Client erstellen → Typ **Webanwendung** →
   Autorisierte Weiterleitungs-URI: `https://developers.google.com/oauthplayground` → Erstellen.
   **Client-ID** und **Clientschlüssel** kopieren (z. B. in Notizen).

**B) Dauerhaften Schlüssel holen** – developers.google.com/oauthplayground
6. Zahnrad oben rechts → **Use your own OAuth credentials** anhaken → Client-ID + Schlüssel einfügen.
7. Links unten ins Feld „Input your own scopes“: `https://www.googleapis.com/auth/drive` → **Authorize APIs**.
8. Google-Login → Warnung „App nicht überprüft“ → Erweitert → *Weiter zu video-editing* → Zulassen.
9. **Exchange authorization code for tokens** → den **Refresh token** kopieren.

**C) In Claude eintragen** – claude.ai/code → Environment dieses Repos → **Bearbeiten** → Umgebungsvariablen
```
GDRIVE_CLIENT_ID=<Client-ID>
GDRIVE_CLIENT_SECRET=<Clientschlüssel>
GDRIVE_REFRESH_TOKEN=<Refresh token>
```
Optional: `ELEVENLABS_API_KEY=<Key>` (Transkript mit Sprecher-Erkennung, sonst Whisper ohne Sprecher).
Speichern → **neue Session** starten → `python3 -m vedit status` zeigt die Drive-Ordner = läuft.

Der Zugang bleibt, bis du ihn unter myaccount.google.com → Sicherheit → Drittanbieter-Zugriff widerrufst.
Werte nie ins Repo oder in den Chat schreiben – nur ins Environment.

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
