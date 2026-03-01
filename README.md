# N8N Voice Cloning — PDF to Speech

Convert PDF documents into spoken audio using voice cloning. This project pairs an [n8n](https://n8n.io) automation workflow with a FastAPI backend powered by [OpenVoice](https://github.com/myshell-ai/OpenVoice) to let you upload a PDF and a short voice sample and receive a WAV file spoken in that voice.

---

## Overview

```
Client / n8n Webhook
        │
        ▼
  n8n Workflow (N8N_VoiceCloning.json)
        │  normalizes binary keys
        │  writes temp files
        │  calls API via curl
        ▼
  FastAPI server (openvoice-api/)
        │  extracts text from PDF (pdfplumber → PyPDF2 fallback)
        │  clones voice with OpenVoice
        ▼
  WAV audio response
```

The n8n workflow handles request normalization and file staging; the Python API handles all heavy lifting (PDF parsing, voice embedding extraction, and speech synthesis).

---

## Repository Layout

```
N8N_VoiceCloning.json    # n8n workflow — import this into your n8n instance
openvoice-api/
  requirements.txt       # Python dependencies
  app/
    main.py              # FastAPI application & route handlers
    models.py            # Pydantic request/response models
    pdf_processor.py     # PDF text extraction and chunking
    voice_processor.py   # OpenVoice model loading and inference
  voices/                # Runtime directories (created automatically)
    uploads/             # Incoming voice samples
    outputs/             # Generated WAV files
  pdfs/                  # Temporary PDF storage (created automatically)
```

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.9 or later |
| PyTorch | compatible with your CUDA/CPU setup |
| n8n | 0.220 or later (self-hosted or cloud) |
| Git | any recent version |

> The API runs on CPU by default. A CUDA-capable GPU will significantly reduce synthesis time for longer documents.

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Waleed-Ahmad20/N8N_VoiceCloning.git
cd N8N_VoiceCloning
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install -r openvoice-api/requirements.txt
```

This also installs the `myshell-openvoice` package directly from GitHub.

### 4. Download OpenVoice checkpoints

Place the following files inside `openvoice-api/checkpoints/`:

| File | Description |
|---|---|
| `converter_v2.pth` | Tone-color converter weights |
| `base_en_v2.pth` | Base English TTS weights |
| `config_en_v2.json` | Model configuration |

Refer to the [OpenVoice releases page](https://github.com/myshell-ai/OpenVoice/releases) for the latest checkpoint downloads.

### 5. Start the API server

```bash
cd openvoice-api
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The server starts at `http://localhost:8000`. First startup takes 1–2 minutes while the models are loaded into memory.

---

## API Endpoints

### `GET /health`
Returns server status and the device (cpu/cuda) in use.

```json
{ "status": "healthy", "device": "cpu" }
```

---

### `POST /upload-voice`
Upload a named voice sample for repeated use.

| Field | Type | Description |
|---|---|---|
| `voice_name` | form string | Identifier for this voice |
| `file` | file | WAV or MP3 voice sample |

```bash
curl -X POST http://localhost:8000/upload-voice \
  -F "voice_name=alice" \
  -F "file=@sample.wav"
```

---

### `POST /pdf-to-speech`
Convert a PDF to speech using a previously uploaded voice.

| Field | Type | Default | Description |
|---|---|---|---|
| `voice_id` | form string | — | Name given during `/upload-voice` |
| `pdf_file` | file | — | PDF document to read |
| `speed` | form float | `1.0` | Playback speed multiplier |
| `max_chars` | form int | `5000` | Character limit for extracted text |

Returns a WAV audio file.

```bash
curl -X POST http://localhost:8000/pdf-to-speech \
  -F "voice_id=alice" \
  -F "pdf_file=@document.pdf" \
  --output output.wav
```

---

### `POST /simple-pdf-to-speech`
One-shot endpoint: upload both the PDF and the voice sample in a single request.

| Field | Type | Description |
|---|---|---|
| `pdf_file` | file | PDF document to read |
| `voice_file` | file | WAV voice sample for cloning |

Returns a WAV audio file.

```bash
curl -X POST http://localhost:8000/simple-pdf-to-speech \
  -F "pdf_file=@document.pdf" \
  -F "voice_file=@voice.wav" \
  --output output.wav
```

---

### `GET /voices`
List all voice names currently loaded in memory.

```json
{ "voices": ["alice", "bob"] }
```

---

### `DELETE /voice/{voice_id}`
Remove a voice from memory and delete its uploaded file.

```bash
curl -X DELETE http://localhost:8000/voice/alice
```

---

## n8n Workflow Setup

1. Open your n8n instance and navigate to **Workflows → Import from file**.
2. Select `N8N_VoiceCloning.json`.
3. Update the two **Write Binary File** nodes with temp paths suitable for your OS:
   - Default paths use `C:\temp\` — change to `/tmp/` on Linux/macOS.
4. Verify that the **Execute Command** nodes point to the correct API URL (default `http://127.0.0.1:8000`).
5. Activate the workflow.

### Calling the workflow

Send a `POST` request to the webhook URL with multipart form data:

```bash
curl -X POST http://<n8n-host>/webhook/simple-pdf-to-speech \
  -F "pdf_file=@document.pdf" \
  -F "voice_file=@voice.wav" \
  -F "language=EN" \
  -F "use_custom_voice=true" \
  --output result.wav
```

| Parameter | Description |
|---|---|
| `pdf_file` | PDF document |
| `voice_file` | WAV/MP3 voice sample (required when `use_custom_voice=true`) |
| `language` | Language code, e.g. `EN`, `ZH` |
| `use_custom_voice` | `true` to clone the provided voice; `false` to use the default voice |

---

## Configuration

The API server reads no environment variables by default. If you add integrations (e.g. OpenAI for text preprocessing) create a `.env` file in `openvoice-api/` and load it with `python-dotenv`.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: openvoice` | Package not installed | Re-run `pip install -r requirements.txt` |
| `FileNotFoundError: checkpoints/...` | Missing model files | Download checkpoints (see Installation step 4) |
| Silent or distorted audio | Voice sample too short | Use a 6–30 second clean recording |
| n8n `Write Binary File` error | Wrong temp path for your OS | Update node paths to `/tmp/` |
| Slow synthesis | Running on CPU | Use a GPU-enabled machine or reduce `max_chars` |

---

## License

This project uses [OpenVoice](https://github.com/myshell-ai/OpenVoice) which is released under the MIT License. See the upstream repository for full license details.
