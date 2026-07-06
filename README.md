# 🔎 Fake News Checker

The application listens, through a browser, to audio from the computer’s microphone. It transcribes the detected speech and has an AI model (OpenAI) evaluate the truthfulness of the statements, assigning a **correctness score from 1 to 10** across several parameters that help assess how true the sentence is.

## Requirements

- Python 3.10 or higher  
- Google Chrome or Microsoft Edge (for speech recognition)  
- An OpenAI API key (https://platform.openai.com/api-keys)

## Installation

1. Open a terminal in this folder and install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Copy the `.env.example` file into `.env` and insert your API key:

   ```
   OPENAI_API_KEY=sk-...
   ```

## Usage

1. Start the server:

   ```
   python server.py
   ```

2. Open **http://127.0.0.1:5000** in Chrome or Edge.

3. Press the **space bar** (or the 🎙️ button) to start listening.  
   On first launch, the browser will ask for microphone permission.

4. Every complete sentence that is detected appears as a card containing:
   - the **score from 1 to 10** (green = reliable, orange = doubtful, red = false)
   - a short evaluation
   - the **reasons** why the score is low, based on factual reality

5. Check "**Use web search**" to verify statements with an online search: more accurate for recent facts, but slower.

6. Press **Space** again to stop listening.

## Note: listening to computer audio (not just the microphone)

Speech recognition uses the **microphone**. To analyze audio played by the computer (videos, streaming TV, etc.), you have two options:

- turn up the speaker volume so the microphone picks up the audio;
- or, on Windows, enable the "**Stereo Mix**" recording device in sound settings (Control Panel → Sound → Recording) and set it as the default microphone: the "microphone" will then capture system audio.

## How it works

- `server.py` — Flask server that receives sentences and calls the OpenAI API (default model: `gpt-4o`, configurable via `OPENAI_MODEL` in `.env`) with structured JSON output (score, evaluation, reasons). When web search is enabled, it uses the Responses API with the `web_search` tool.
- `static/index.html` — web interface: uses the browser’s Web Speech API to transcribe spoken Italian in real time and display results instantly.
