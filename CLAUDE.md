# Video-Editing 2.0 – Joe x PSGOTRICH

Du schneidest Social-Content (Reels 9:16, YouTube 16:9) für **Joe** und **PSGOTRICH** aus iPhone-Footage.
Der User steuert meist **vom Handy** (Claude-App → Cloud-Session dieses Repos). Antworte deshalb kurz,
auf Deutsch, und liefere Ergebnisse als Drive-Links bzw. Dateinamen statt langer Logs.

## Wo liegt was
- **Drive** `Mein Mac/JOE X PSGOTRICH/` (alle Pfade unten relativ dazu, Remote `gdrive:`):
  - `01_EINGANG/` Rohmaterial je Event (z. B. `#4_Mercedes GoKart`). Neue Uploads landen manchmal auch lose in der Wurzel (z. B. `Samstag shit `) – beachte Leerzeichen am Ende.
  - `02_Entwürfe/<YYYY-MM-DD>_<Event>/` Exporte + `Kontext.md` + `Schnittplan.txt` (das schaut sich das Team an)
  - `04_Zum_Löschen/`, `05_Musik/` (Songs für Hard Edits)
- **Repo** `edits/<YYYY-MM-DD>_<Event>/` – versioniert, damit jede Session (Handy/Mac) weitermachen kann:
  `event.json`, `shots.json` (Archiv-IDs), `transkript/*.json`, `transkript.txt`, `Kontext.md`, `Schnittplan.txt`, `schnitt.json`
- **work/** – Medien (Originale, Proxys, Exporte). Nicht versioniert, in Cloud-Sessions flüchtig.

## Pipeline (`python3 -m vedit …`)
1. `status` – was liegt neu in Drive, läuft ein Upload noch?
2. `neu "<Drive-Ordner>" <Drehtag> <Name>` – lädt Footage, vergibt Archiv-IDs `JP-YYMMDD-NN`
   (nach Aufnahmezeit, stabil), baut 540p-Proxys + Audio, transkribiert (Scribe mit Sprechern, wenn
   `ELEVENLABS_API_KEY` gesetzt; sonst faster-whisper). Läuft der Upload noch: holt das Vorhandene, später erneut aufrufen.
3. **Du** liest `transkript.txt` (+ bei Bedarf Standbilder aus Proxys) und schreibst `Kontext.md`, `Schnittplan.txt`, `schnitt.json`.
4. `vorschau <event> [nr…]` – schnelle 540p-Renders aus Proxys zum Prüfen (Standbilder ansehen!).
5. `render <event> [nr…]` – final aus Originalen (lädt nur benötigte Shots), HDR→SDR, −14 LUFS.
6. `hochladen <event>` (oder `--vorschau`) → `02_Entwürfe/<event>/`.
7. Commit + Push der `edits/<event>/`-Dateien, damit der Stand auf jedem Gerät da ist.

## schnitt.json
```json
{"datum": "2026-10-18", "videos": [{
  "nr": "01", "typ": "Vlog", "fokus": "Joe", "titel": "Kein-Mechanic", "format": "9:16",
  "clips": [{"shot": "JP-261018-03", "von": 12.3, "bis": 18.9, "x": 0.5, "zoom": 1.0}],
  "texte": [{"text": "MISSION: RADIO-SICHERUNG 64", "von": 0, "bis": 2.5, "pos": "kicker"},
            {"text": "KEIN MECHANIC", "von": 0, "bis": 1.8, "pos": "oben"}],
  "untertitel": true,
  "musik": {"datei": "05_Musik/song.mp3", "start": 44.07, "pegel": -12}
}]}
```
- `typ`: Vlog | Sketch | HardEdit | Interview · `fokus`: Joe | PSGOTRICH | Beide · `format`: 9:16 | 16:9
- Clip-Optionen: `x`/`y` (Bildausschnitt 0–1, bei Querformat→9:16 wichtig: auf Gesichter setzen), `zoom`, `tempo`, `lautstaerke` (dB)
- `pos`: oben | kicker (gelbe Zeile darüber) | mitte | unten
- Mit `musik` entstehen automatisch `…_PREVIEW.mp4` (mit Song) und `…_OHNE-MUSIK.mp4` (Song in der App drunterlegen).
- Dateiname: `<datum>_<Fokus>_<Typ>_<Reel|YouTube>_<NN>_<Titel>.mp4`

## Schnitt-Regeln (aus bisherigen Events)
- **Setup → Payoff nie trennen.** Erst Setup, dann Pointe. Bei Reels darf die Pointe als Hook vorn stehen, dann muss das Setup direkt folgen.
- Reaktionen gehören zur Pointe (Lachen, Blick in die Kamera): mind. **0,4 s** nach dem letzten Wort stehen lassen.
- Antworten nie ohne Frage („Am Sack der Welt“ braucht „Wo sind wir heute?“).
- Hintergrund, ohne den keiner die Aktion versteht, als **Kicker-Zeile** einblenden (z. B. „MISSION: RADIO-SICHERUNG 64“).
- Running Gags als Zähler-Titel nutzen („ÖFFNUNGEN: 1 … ALLE“, „STIMMEN: 1“), Uhrzeit-Kicker für Zeitverlauf.
- Meta-/Insider-Gags nur im YouTube-Vlog oder mit Kicker als Erklärung.
- Dunkles B-Roll (Fußraum, Hände) = Material für Hard Edits/Tempo-Montagen, nicht für Sprach-Reels.
- Reels 9:16: 12–30 s, Hook in den ersten 1–2 s. YouTube-Vlog 16:9: Cold Open + Freeze, Intro-Titel, Kapitel.
- Hard Edits nur auf Anfrage. Song kommerziell → OHNE-MUSIK-Version posten, Song in der App drunter (Drop-Zeit angeben).
- **Raus**: Leute, die nicht gefilmt werden wollten; abwertende Kommentare über Gäste/Körper; Lars’ echter Name.
  Gäste nur mit Namen, wie sie sich selbst nennen. Politische Stellen markieren und entscheiden lassen.
- Untertitel immer (laute Umgebung), bei Englisch auf Tippfehler prüfen.

## Schnittplan.txt (Format des Teams)
Kopfzeile: Event – Datum – Quelle (Archiv-IDs). Dann je Video eine Zeile:
`NN | Typ | Format | Fokus | Mood | Hook: … → Payoff | Shots (IDs + Zeiten) | Caption-Vorschlag | Länge`
Danach **Prüfhinweise** (Einwilligungen, heikle Stellen, ungenutzte Shots, offene Entscheidungen).

## Kontext.md (pro Event)
Worum geht’s · Figuren · Setup → Payoff-Tabelle (mit IDs) · Running Gags · Bogen · Schnitt-Regeln für dieses Event.

## Arbeitsweise
- Lange Läufe (Download, Transkription, Render) im Hintergrund starten und dem User kurz Bescheid geben.
- Vor dem Final-Render Vorschau-Standbilder prüfen (Ausschnitt, Titel lesbar, nichts abgeschnitten).
- Nach jedem Schritt `edits/<event>/` committen und pushen.
