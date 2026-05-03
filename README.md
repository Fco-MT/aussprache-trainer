# Aussprache-Trainer - Einrichtung & Bedienung

Ein lokales Tool fuer Deutschlehrer mit Privacy-First-Ansatz:
Audiodateien bleiben auf deinem MacBook - an Google wird nur anonymisierter Text gesendet.

---

## Wie es funktioniert

1. faster-whisper large-v3-turbo (lokal, kostenlos): Transkribiert die Audiodatei mit Konfidenzwerten pro Segment
2. Wort-Abgleich (lokal): Vergleicht Transkription mit Zieltext, markiert unsichere Stellen farbig
3. Gemini 2.5 Flash (Google AI Free Tier): Analysiert nur den anonymisierten Text - kein Audio, keine biometrischen Daten

---

## Einmalige Einrichtung (ca. 10-15 Minuten)

### 1. Python prüfen
```
python3 --version
```
Python 3.9 oder neuer wird benoetigt.

### 2. Virtuelle Umgebung erstellen und aktivieren (wichtig auf macOS!)

macOS verhindert die systemweite Installation von Python-Paketen.
Die Loesung ist eine virtuelle Umgebung (venv):

```bash
# In den Projektordner wechseln (Pfad ggf. anpassen)
cd ~/Desktop/aussprache_tool

# Virtuelle Umgebung erstellen (einmalig)
python3 -m venv venv

# Virtuelle Umgebung aktivieren
source venv/bin/activate
```

Du erkennst die aktive venv daran, dass im Terminal vorne (venv) erscheint:
```
(venv) manfred@MacBook aussprache_tool %
```

### 3. Abhaengigkeiten installieren
```bash
pip install -r requirements.txt
```
Das laedt faster-whisper, Flask und die Google AI-Bibliothek (~1-2 GB, einmalig).
Die Installation dauert ca. 5-10 Minuten.

Hinweis: Beim ersten Start laedt faster-whisper das Modell large-v3-turbo
automatisch nach (~1,6 GB). Das passiert einmalig im Hintergrund und erscheint
als Meldung im Terminal.

### 4. Google API-Key eintragen (kostenlos)
- Geh auf https://aistudio.google.com/apikey
- Klick auf "Create API Key"
- Oeffne die Datei key.txt im Projektordner
- Ersetze den Platzhaltertext durch deinen Key:
  AIzaSy...
- Das Free Tier reicht fuer den Unterrichtsbetrieb vollstaendig aus
  (1.500 Anfragen/Tag kostenlos)

---

## Tool starten

Bei jedem Start im Terminal:
```bash
# 1. In den Projektordner wechseln
cd ~/Desktop/aussprache_tool

# 2. Virtuelle Umgebung aktivieren
source venv/bin/activate

# 3. Tool starten
python3 app.py
```

Dann im Browser oeffnen: http://127.0.0.1:5000

Bitte Chrome oder Edge verwenden - Firefox unterstuetzt einige Funktionen nicht.

Das Terminal-Fenster muss waehrend der Nutzung geoeffnet bleiben.
Zum Beenden: Strg+C im Terminal.

---

## Bedienung

### Eingabe

1. Name der/des Studierenden eingeben (optional, erscheint im Feedback-Dokument)
2. Feedback-Sprache waehlen: Deutsch / English / Traditionelles Chinesisch
3. Bekannte Ausspracheprobleme anklicken (optional):
   Vorab bekannte Schwaechen werden im Feedback gezielt und ergaenzend zur
   Transkriptionsanalyse behandelt - auch wenn Whisper den Fehler nicht erfasst hat.
   Verfuegbare Kategorien:
   - ei/ie-Verwechslung
   - Umlaute ae/oe/ue
   - ch-Laut (ach/ich)
   - r-Laut
   - Endkonsonanten (-t/-d/-st)
   - Wortbetonung
   - Zahlenaussprache
   - Diphthonge (au/eu/aeu)
4. Zieltext einfuegen (der Text, den die Studierenden vorlesen sollten)
5. Audiodatei per Drag & Drop oder Klick hochladen

### Analyse

6. "Aussprache analysieren" klicken
7. Warten (~20-40 Sek.): faster-whisper transkribiert lokal, Gemini analysiert

### Ergebnis

Transkription & Wort-Abgleich (oben auf der Seite):
- Gruen: korrekt erkannt
- Rot + Wellenlinie: falsch erkannt
- Grau + [eckige Klammern]: nicht erkannt
- Gelber Hintergrund: niedrige Erkennungssicherheit
- Hover ueber ein Wort zeigt: Zielwort | Erkanntes Wort | Konfidenz in %

Aussprache-Feedback (Berichtsbereich):
- Erkennungsrate mit Balken
- Zieltext (als Fliestext, alle Saetze in einem Absatz)
- Transkription & Wort-Abgleich (farbig, identisch mit der Ansicht oben)
- Gesamteindruck, Staerken, Problemtabelle, gezielte Tipps, Uebungsvorschlag

### PDF-Export

8. "Feedback drucken / als PDF" klicken.
   Der Button wartet automatisch, bis alle Schriften (inkl. Chinesisch)
   vollstaendig geladen sind, bevor der Druckdialog erscheint.
   Im Druckdialog: "Als PDF sichern" waehlen.

---

## Datenschutz

Was                          | Wo verarbeitet
-----------------------------|--------------------------------------------------
Audiodatei                   | Bleibt auf deinem MacBook, sofort nach Analyse geloescht
Transkription & Wort-Abgleich| Lokal berechnet, verlaesst das MacBook nicht
An Google gesendet           | Nur: Zieltext + Transkription + Fehlerliste (Text)
Biometrische Daten           | Keine - Google sieht ausschliesslich Text

---

## Kosten

Komponente                    | Kosten
------------------------------|------------------------------------------------
faster-whisper (Transkription)| Kostenlos, laeuft lokal
Gemini 2.5 Flash (Analyse)   | Free Tier: 1.500 Anfragen/Tag kostenlos
Bei Ueberschreitung Free Tier | ca. 0,002 EUR pro Analyse

Bei 30 Studierenden pro Tag ist das Tool vollstaendig im kostenlosen Bereich.

---

## Unterstuetzte Audioformate

MP3, WAV, M4A, OGG, FLAC, WebM, MP4, AAC - max. 50 MB

---

## Hinweise & Tipps

Erster Start dauert laenger:
Das Whisper-Modell wird beim allerersten Start heruntergeladen und einmalig
geladen (~30-60 Sek.). Alle folgenden Analysen sind schneller.

Kuerzere Aufnahmen = bessere Erkennung:
Getrennte Aufnahmen fuer Fragen und Antworten verbessern die Transkriptions-
qualitaet bei A1-Lernenden deutlich.

Grenzen der Spracherkennung:
Bei stark akzentiertem A1-Deutsch erkennt Whisper nicht immer alle Fehler.
Die "Bekannte Ausspracheprobleme"-Funktion ermoeglicht gezieltes Feedback
auch ohne direkte Whisper-Evidenz - sie ergaenzt die Transkriptionsanalyse,
ersetzt sie aber nicht.

PDF auf Chinesisch:
Die Schrift Noto Sans TC wird beim Drucken automatisch von Google Fonts geladen.
Eine Internetverbindung beim PDF-Export ist daher erforderlich.
