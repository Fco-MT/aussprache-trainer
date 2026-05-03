# Aussprache-Trainer (German Pronunciation Trainer)

A local feedback tool for German language teachers (DaF).
Upload a student's audio recording and receive detailed pronunciation analysis — **privacy-first: audio never leaves your machine.**

---

## How It Works

1. **faster-whisper large-v3-turbo** (local, free): Transcribes the audio file with per-segment confidence scores
2. **Word alignment** (local): Compares transcription against the target text, highlights uncertain words
3. **Gemini 2.5 Flash** (Google AI Free Tier): Analyses only the anonymised text — no audio, no biometric data sent to Google

---

## Requirements

- Python 3.9 or newer (tested with Python 3.13)
- A free Google AI Studio API key: https://aistudio.google.com/apikey
- Chrome or Edge browser

---

## Installation (one-time, ~10–15 minutes)

### 1. Download the project

Click **Code → Download ZIP** on this page, then unzip the folder.

### 2. Create a virtual environment (important on macOS)

Open a terminal, navigate to the project folder, and run:

```bash
cd path/to/aussprache_tool

# Create virtual environment
python3 -m venv venv

# Activate it (macOS/Linux)
source venv/bin/activate

# Activate it (Windows)
venv\Scripts\activate
```

You will see **(venv)** at the start of your terminal prompt when it is active.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

This downloads faster-whisper, Flask, and the Google AI library (~1–2 GB, one-time only).

> **Note:** On first launch, faster-whisper will automatically download the
> `large-v3-turbo` model (~1.6 GB). This happens once in the background.

### 4. Add your Google API key

- Go to https://aistudio.google.com/apikey and click **Create API Key**
- Open the file `key.txt` in the project folder
- Replace the placeholder text with your key:
  ```
  AIzaSy...
  ```
- The Free Tier is sufficient for classroom use (1,500 requests/day free)

---

## Starting the Tool

Run the following commands each time you want to use the tool:

```bash
# Navigate to the project folder
cd path/to/aussprache_tool

# Activate the virtual environment
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

# Start the server
python3 app.py
```

Then open **http://127.0.0.1:5000** in Chrome or Edge.

Keep the terminal window open while using the tool. To stop: press **Ctrl+C**.

---

## How to Use

### Input

1. Enter the **student's name** (optional — appears in the feedback document)
2. Select the **feedback language**: German / English / Traditional Chinese
3. Optionally tick **known pronunciation issues** for targeted feedback even when the speech recogniser misses them:
   - ei/ie confusion
   - Umlauts ä/ö/ü
   - ch-sound (ach vs. ich)
   - r-sound
   - Final consonants (-t/-d/-st)
   - Word stress
   - Number pronunciation
   - Diphthongs (au/eu/äu)
4. Paste the **target text** (the text the student was asked to read aloud)
5. **Upload the audio file** by drag & drop or click

### Analysis

6. Click **"Aussprache analysieren"** (Analyse Pronunciation)
7. Wait ~20–40 seconds: faster-whisper transcribes locally, then Gemini analyses

### Results

**Transcription & Word Alignment** (top section):
- 🟢 Green: correctly recognised
- 🔴 Red + wavy underline: incorrectly recognised
- ⚫ Grey + [brackets]: not recognised (missing)
- 🟡 Yellow background: low confidence score
- Hover over a word to see: target word | recognised word | confidence %

**Pronunciation Feedback** (report section):
- Recognition rate with progress bar
- Target text (as continuous prose)
- Transcription & word alignment (colour-coded)
- Overall impression, strengths, problem table, targeted tips, practice exercise

### PDF Export

Click **"Feedback drucken / als PDF"** (Print / Save as PDF).
The button waits until all fonts (including Chinese) are fully loaded before opening the print dialog.
In the print dialog, choose **"Save as PDF"**.

---

## Privacy

| Data | Where it is processed |
|------|-----------------------|
| Audio file | Stays on your computer; deleted immediately after analysis |
| Transcription & alignment | Computed locally; never leaves your machine |
| Sent to Google | Only: target text + transcription + error list (plain text) |
| Biometric data | None — Google sees text only |

---

## Cost

| Component | Cost |
|-----------|------|
| faster-whisper (transcription) | Free — runs locally |
| Gemini 2.5 Flash (analysis) | Free Tier: 1,500 requests/day at no cost |
| Beyond Free Tier | ~€0.002 per analysis |

For a class of 30 students per day, the tool runs entirely within the free tier.

---

## Supported Audio Formats

MP3, WAV, M4A, OGG, FLAC, WebM, MP4, AAC — max. 50 MB

---

## Tips

**First launch takes longer:** The Whisper model is downloaded and loaded on first use (~30–60 sec). All subsequent analyses are faster.

**Shorter recordings = better recognition:** Separate recordings for questions and answers improve transcription quality for A1 learners significantly.

**Limits of speech recognition:** Whisper may not catch all errors in heavily accented A1 German. The "known issues" checkboxes allow targeted feedback even without direct transcription evidence.

**PDF in Chinese:** The Noto Sans TC font is loaded from Google Fonts when printing. An internet connection is required for Chinese PDF export.

---

## Acknowledgements

Built with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and [Google Gemini](https://ai.google.dev/).
