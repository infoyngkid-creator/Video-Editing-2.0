---
name: ai-larp
description: Echten Clip per Higgsfield (Connector) in eine KI-„Luxus-Version“ verwandeln (AI LARP – Lambo statt Astra, Anzug, Uhr, Villa) und als Shot ins Reel einbauen. Nutzen bei "AI LARP", "Higgsfield", "KI-Version", "mach daraus Lambo/Villa", "echt vs. KI".
---

# AI LARP mit Higgsfield

Idee: echter Clip (z. B. Joe im Astra) → Higgsfield macht dieselbe Szene in „rich“ → im Reel als Pointe
(Hook „ECHT“ → Schnitt → „KI“), oder als reiner Flex-Clip.

## Voraussetzung
- Higgsfield-Connector muss in dieser Session verbunden sein (Tools mit `higgsfield` im Namen; ggf. per ToolSearch laden).
  Fehlt er: User sagen → Claude-App → Einstellungen → Connectors → Custom Connector → `https://mcp.higgsfield.ai/mcp`.
  Mac/Claude Code: `claude mcp add --transport http --scope user higgsfield https://mcp.higgsfield.ai/mcp`
- Jede Generierung kostet Credits (auch Fehlversuche). **Credits-Regel unten ist Pflicht.**

## Credits-Regel (verbindlich)
1. Vor jeder Generierung Guthaben abfragen und dem User zeigen: Modell, Länge, geschätzte Credits.
2. Erst nach seinem **Ja** generieren – immer **ein** Clip pro Freigabe, keine Varianten-Serien.
3. Erst kurz (5 s) testen, erst bei gutem Ergebnis längere Version.
4. Verbrauchte Credits mit `--credits` beim Übernehmen eintragen (`vedit ki-liste` zeigt die Summe).

## Ablauf
1. Clip finden: `transkript.txt` / `python3 -m vedit archiv --lang`. Gut geeignet: Selfie im Auto, ruhige Kamera, ein Gesicht.
2. Vorlage schneiden: `python3 -m vedit ki-vorlage <event> <shot> <von> <bis>` → `work/<event>/ki/VORLAGE_….mp4` (SDR, ≤10 s).
3. Standbild ansehen, Prompt bauen (Englisch, konkret): was bleibt (Person, Pose, Kamera-Bewegung, Selfie-Perspektive),
   was sich ändert (z. B. „teal leather Lamborghini interior, black tuxedo, iced-out watch, Miami mansion driveway at golden hour“).
4. Mit dem Higgsfield-Connector generieren: Vorlage hochladen, bevorzugt Video-zu-Video / Motion Control
   (z. B. Kling Motion Control); sonst Standbild umgestalten (Bild-Edit) → Bild-zu-Video. Modell nach Credits wählen.
5. Ergebnis übernehmen: `python3 -m vedit ki-shot <event> <datei-oder-URL> --vorlage <shot> --prompt "…" --modell "…" --credits N`
   → neuer Shot `JP-YYMMDD-KI-NN` (mit Proxy). Lädt die URL in der Cloud nicht (Netz-Sperre): User bitten, das Video
   aus Higgsfield nach `03_Archiv/<event>/` zu legen, dann mit `--drive-id` übernehmen.
6. In `schnitt.json` wie jeden Shot nutzen. Typisch: echter Clip 1–3 s → harter Schnitt → KI-Shot, Kicker „ECHT“ / „KI“.
   Untertitel kommen aus dem echten Clip (KI-Shots haben kein Transkript).
7. `vorschau` → Standbilder prüfen (Gesicht erkennbar? Hände/Uhr ok? keine Logos/Text-Fehler) → `render` → Commit + Push.

## Regeln
- Nur Personen, die zugestimmt haben (Joe, PSGOTRICH, Paul); keine Gäste ohne OK, keine echten Promis.
- Keine echten Marken-Logos groß im Bild planen; im Prompt „no logos, no text“.
- Beim Posten auf Instagram/TikTok **„KI-generiert“-Label setzen** (Pflicht bei realistischen KI-Videos).
- Im `Schnittplan.txt` KI-Shots mit `[KI]` markieren.
