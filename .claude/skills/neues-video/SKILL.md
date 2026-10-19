---
name: neues-video
description: Neues Joe/PSGOTRICH-Footage aus Google Drive verarbeiten – Upload prüfen, Footage holen, Archiv-IDs, Transkript, Kontext.md, Schnittplan, Vorschauen und Entwürfe nach Drive. Nutzen bei "neues Video", "neues Joe PS Video", "Drive Upload", "neues Event", "schneide …".
---

# Neues Video / Event verarbeiten

1. **Finden**: `python3 -m vedit status`. Den neuen Ordner identifizieren (lose in der Wurzel oder unter `01_EINGANG/`).
   Ist er unklar, kurz nachfragen. Drehtag aus den Aufnahme-Zeitstempeln ableiten (nicht Upload-Datum).
   Event-Name: kurz, sprechend (`Mercedes-GoKart`, `ClownStadt-Rummel`); "Samstag shit" ist kein guter Name → nach Sichtung umbenennen.
2. **Holen + Ingest** (im Hintergrund): `python3 -m vedit neu "<Ordner>" <YYYY-MM-DD> <Name>`.
   Meldet es einen laufenden Upload, mit dem Vorhandenen anfangen und später erneut aufrufen (bestehende IDs bleiben).
3. **Sichten**: `edits/<event>/transkript.txt` lesen. Für Bildinhalt Standbilder aus `work/<event>/proxy/<ID>.mp4` ziehen
   (`ffmpeg -ss <t> -i … -frames:v 1 x.jpg`) und ansehen – v. a. Shots ohne Sprache.
4. **Kontext.md** und **Schnittplan.txt** schreiben (Format + Regeln: CLAUDE.md). Setup→Payoff-Paare mit IDs + Zeiten.
5. **schnitt.json** aus dem Plan bauen. Zeiten aus den Wort-Zeitstempeln in `transkript/<ID>.json` nehmen,
   vor dem ersten Wort ~0,15 s, nach der Pointe ≥ 0,4 s Luft.
6. `python3 -m vedit vorschau <event>` → 2–3 Standbilder je Video prüfen (Ausschnitt `x`, Titel, Untertitel), korrigieren.
7. `python3 -m vedit render <event>` → `python3 -m vedit hochladen <event>`.
8. `edits/<event>/` committen + pushen.
9. Dem User kurz antworten: Liste der Videos (Titel, Länge, Hook in einem Satz), Drive-Ordner, offene Prüfhinweise.
