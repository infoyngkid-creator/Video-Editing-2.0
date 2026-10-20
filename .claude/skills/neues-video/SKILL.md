---
name: neues-video
description: Neues Joe/PSGOTRICH-Footage aus Google Drive verarbeiten – Upload prüfen, Footage holen, Archiv-IDs, Transkript, Kontext.md, Schnittplan, Vorschauen und Entwürfe. Nutzen bei "neues Video", "neues Joe PS Video", "Drive Upload", "neues Event", "schneide …".
---

# Neues Video / Event verarbeiten

**Standardweg ohne Token** (Ordner `JOE X PSGOTRICH` ist per Link freigegeben):
1. **Finden** mit dem Google-Drive-Connector: `search_files` mit `parentId = '1gxp8zG5hgsyqUXvIrgD2KXqU7dCUrXn4'`
   (Wurzel) bzw. `01_EINGANG` → neuen Ordner finden, dann alle Dateien darin listen (Paginierung beachten!).
   Upload läuft noch, wenn die jüngste `createdTime` nur wenige Minuten alt ist → mit Vorhandenem anfangen.
2. Liste `work/ids.txt` schreiben, Zeilen `DRIVE_ID Dateiname`. Drehtag aus Aufnahme-Metadaten (`vedit.media.probe`).
3. **Holen + Ingest** im Hintergrund: `python3 -m vedit holen work/ids.txt <YYYY-MM-DD> <Name> --quelle "<Ordner>"`.
   Lädt parallel per Link, vergibt Archiv-IDs, Proxys, Transkript. Später erneut aufrufen holt nur Neues.
   (Mit `GDRIVE_*`-Secrets geht alternativ `python3 -m vedit neu "<Ordner>" …` über rclone.)
4. **Sichten**: `edits/<event>/transkript.txt` lesen. Für Bildinhalt Standbilder aus `work/<event>/proxy/<ID>.mp4`
   ziehen (`ffmpeg -ss <t> -i … -frames:v 1 x.jpg`) und ansehen – v. a. Shots ohne Sprache.
5. **Kontext.md** und **Schnittplan.txt** schreiben (Format + Regeln: CLAUDE.md). Setup→Payoff-Paare mit IDs + Zeiten.
6. **schnitt.json** bauen. Zeiten aus `transkript/<ID>.json`, vor dem ersten Wort ~0,15 s, nach der Pointe ≥ 0,4 s.
7. `python3 -m vedit vorschau <event>` → 2–3 Standbilder je Video prüfen (Ausschnitt `x`, Titel, Untertitel).
8. `python3 -m vedit render <event>`.
9. **Ausliefern**: fertige MP4s per `SendUserFile` direkt in die App schicken (User speichert/postet vom Handy).
   Kontext.md + Schnittplan.txt per Drive-Connector `create_file` (Text) nach `02_Entwürfe/` legen.
   Nur mit `GDRIVE_*`-Secrets: `python3 -m vedit hochladen <event>` lädt auch die Videos nach Drive.
10. `edits/<event>/` committen + pushen. Kurz antworten: Videos (Titel, Länge, Hook), offene Prüfhinweise.
