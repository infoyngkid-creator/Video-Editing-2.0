---
name: reel-bauen
description: Einzelnes Reel/Video eines bestehenden Events ändern oder neu bauen (andere Pointe, Titel, Ausschnitt, Musik, Hard Edit). Nutzen bei Feedback wie "Reel 03 kürzer", "anderer Hook", "mach eine Version mit Song", "Titel ändern".
---

# Reel ändern / ergänzen

1. Event finden: `ls edits/`. `schnitt.json`, `Schnittplan.txt`, `transkript.txt` lesen.
2. Footage fehlt in dieser Session (Cloud = frischer Container)? `python3 -m vedit vorschau` braucht Proxys →
   bei Bedarf `python3 -m vedit neu "<quelle aus event.json>" <datum> <name> --skip-check` (holt + überspringt Bekanntes).
   Für reines Final-Rendern reicht `render`: es lädt nur die benötigten Originale.
3. Änderung in `schnitt.json` umsetzen (neue Nummer für neue Videos, bestehende Nummer bei Überarbeitung),
   Zeile im `Schnittplan.txt` anpassen (v2-Abschnitt mit Datum, wie im Team üblich).
4. `vorschau <event> <nr>` → Standbilder prüfen → `render <event> <nr>` → `hochladen <event>`.
5. Commit + Push. Kurz melden, was sich geändert hat.

Musik: Song muss in `05_Musik/` liegen. `musik.start` = Sekunde im Song, an der das Reel beginnt
(Drop auf Schnitt legen: start = Drop-Zeit − Position des Schnitts im Reel).

KI-Avatar ("Gesicht/Person tauschen", "AI-Avatar"): `vedit avatar <event> <shot> <avatarbild> --von --bis --nur-bild`
→ Bild per SendUserFile zeigen → nach OK mit `--bild <pfad>` das Video (Kling, max. 30 s) erzeugen, im Hintergrund.
Braucht `FAL_KEY`. Avatar-Bild per Upload in den Chat oder aus Drive. Nur mit Einverständnis der Person im Shot.
