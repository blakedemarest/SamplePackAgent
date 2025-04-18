# Sample Pack Agent

Sample Pack Agent is a Python application designed to automate the generation of sound effects (SFX) libraries based on natural language descriptions (briefs). It employs a **Perceive -> Plan -> Act -> Evaluate** loop, primarily driven by a local Large Language Model (**Gemma 3 via Ollama**), combined with AI audio generation (**ElevenLabs API**) and audio processing tools (`pydub`, `ffmpeg`).

The goal is to transform potentially complex requests (e.g., "400 horror film samples across foley, SFX, and tones") into structured generation jobs, producing diverse and usable audio assets automatically.

## Core Concepts & Architecture

The agent operates using the following conceptual framework and tools:

**1. Agent Loop (Perceive → Plan → Act → Evaluate)**

*   **Perceive:** Takes a free-form SFX brief from the user and loads the base configuration. Handles both single SFX requests and complex bulk library requests.
*   **Plan (Decomposition):** Uses **Gemma 3 (via Ollama)** to parse the brief.
    *   **Single Brief:** Extracts structured parameters (source, timbre, dynamics, duration, pitch, space, analogy, influence values).
    *   **Bulk Brief:** *[Planned]* Extracts overall specifications (total count, categories, counts per category, default parameters). Then, for each category, uses Gemma 3 again to generate a set of *distinct prompt templates*. These templates are expanded/mutated (potentially using Gemma 3 synonyms) to meet the required count per category, ensuring uniqueness.
*   **Act (Generation & Processing):**
    *   **Compose Prompt:** Fills a prompt template (f-string, future: Jinja2) using the decomposed parameters.
    *   **Generate Audio:** Calls the **ElevenLabs API** (`eleven_multisfx_v1` model recommended) to generate raw audio. For each core prompt (especially in bulk mode), it loops through configured `batch_influences` to create variations.
    *   **Post-Process:** Uses **`pydub` and `ffmpeg`** to normalize audio to a target LUFS, trim silence (optional), and calculate quality metrics (LUFS, Peak dBFS).
*   **Evaluate (Critique & Store):**
    *   **Store Metadata:** Appends detailed metadata (original brief, parameters, prompt used, metrics, file paths) for each successfully generated and processed SFX to a central YAML library (`prompt_library.yml`). Uses `mutagen` for tagging audio files (planned).
    *   **Critique Loop:** *[Planned]* Feeds the calculated audio metrics (e.g., loudness, peaks) back to **Gemma 3** to ask for suggestions on how to tweak the *original prompt* for improved results (e.g., reducing clipping, adjusting timbre), potentially triggering another Plan -> Act cycle.

**2. Key Tools & Libraries**

| Capability                 | Tool / Library                  |
| :------------------------- | :------------------------------ |
| Agent "Thinking" / Control | Ollama CLI → Gemma 3 (e.g., 12B) |
| Text→Audio Generation      | `elevenlabs` Python SDK         |
| Audio Post-Processing      | `pydub` + `ffmpeg`              |
| Loudness Measurement       | `pyloudnorm`                    |
| Metadata Tagging           | `mutagen` *(Planned)*           |
| Configuration / File I/O   | `ruamel.yaml`, `pathlib`, etc.  |
| CLI / Orchestration        | Python (`argparse`, `logging`)  |

*(TODO: Add link to architecture diagram image if hosted)*

## Features

*   **Natural Language Input:** Accepts single SFX briefs via CLI.
*   **LLM Decomposition:** Uses Gemma 3 / Ollama for structured parameter extraction from single briefs.
*   **Prompt Composition:** Creates text prompts from parameters.
*   **AI Audio Generation:** Integrates with ElevenLabs API.
*   **Variation Generation:** Creates multiple SFX variations based on `batch_influences`.
*   **Audio Post-Processing:** Normalizes to target LUFS, calculates metrics.
*   **Metadata Library:** Stores results in `prompt_library.yml`.
*   **Modular Design:** Code separated by function (config, decompose, compose, generate, process, library, run).
*   **Unit Tested:** Core components have pytest coverage.
*   **Configurable:** Key parameters (models, paths, LUFS, influences) managed via YAML.
*   **Planned:**
    *   **Bulk Library Generation:** Handling complex briefs requesting large counts across multiple categories (core design goal).
    *   **LLM Critique Loop:** Using Gemma 3 to analyze audio metrics and suggest prompt improvements.
    *   **Advanced Prompting:** Hierarchical template generation and mutation for uniqueness in bulk mode.
    *   **GUI / DAW Integration:** Making the agent accessible via UI or plugin.
    *   **Resource Management:** Batching/chunking for large jobs.
    *   **Audio Tagging:** Embedding metadata into audio files using `mutagen`.
    *   **Enhanced Error Handling:** Retries for API/Ollama calls.

## Example Use Cases (Target Capabilities)

The agent architecture is designed to eventually handle briefs like:

*   `"I am designing a horror film, I need a 400 sample library of foley, scary sound effects, and abstract tones. I also need some horror string motifs"`
*   `"hyperpop sample pack for terminally online y2k baddies"`
*   `"I want 200 different sounds that are extremely unique to each other"`

*(Note: The current implementation primarily handles single SFX briefs. Bulk generation requires implementing the hierarchical planning steps described in the architecture.)*

## Setup / Installation

**Prerequisites:**

*   **Python:** 3.8 or higher.
*   **Ollama:** Install Ollama ([https://ollama.com/](https://ollama.com/)) and ensure the Ollama server is running (`ollama serve` or desktop app).
*   **Gemma Model:** Pull the specific Gemma model specified in `configs/sfx_agent.yml` via Ollama (e.g., `ollama pull gemma3:12b`). **Verify the model name matches your config exactly.**
*   **ffmpeg:** Required by `pydub`. Install ffmpeg and ensure the `ffmpeg` executable is in your system's PATH ([https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)).
*   **ElevenLabs API Key:** Required for audio generation ([https://elevenlabs.io/](https://elevenlabs.io/)).

**Steps:**

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd SamplePackAgent
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    python -m venv venv
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set API Key:** Create a file named `.env` in the project root directory (`SamplePackAgent/.env`) and add your ElevenLabs API key:
    ```dotenv
    # .env
    ELEVEN_API_KEY="your_elevenlabs_api_key_here"
    ```
    *(Note: `.env` is included in `.gitignore`.)*

5.  **Configure:** Review and adjust settings in `configs/sfx_agent.yml`:
    *   `gemma.model`: **Must match** the Ollama model you have pulled (e.g., `gemma3:12b`).
    *   `output.folder`: Where processed SFX files will be saved (relative to the config file).
    *   `prompt.batch_influences`: List of influence values (0.0-1.0) for generating variations.
    *   `processing.target_lufs`: Target loudness for normalization.
    *   `library.path`: Path to the YAML results library (relative to the config file).
    *   `logging.level`: Logging verbosity (`DEBUG`, `INFO`, `WARNING`, etc.).

## Usage (Current Implementation)

Run the agent from the command line to generate SFX variations from a single brief:

**Basic Usage:**

```bash
python scripts/run_agent.py "Your sound effect brief description here"
```
*Example:*
```bash
python scripts/run_agent.py "sci-fi door slam with a long echo"
```

**Using a Specific Configuration File:**

```bash
python scripts/run_agent.py "brief text" -c path/to/your/custom_config.yml
```

**Interactive Mode (If no brief provided):**

```bash
python scripts/run_agent.py
Describe your SFX brief: a small metal object dropping onto a concrete floor
```

**Output:**

*   Processed audio files (one for each influence in `batch_influences`) saved in the configured output folder.
*   Metadata appended to the configured YAML library file.
*   Console logs showing the process and any errors.

*(Note: Handling of bulk library briefs requires further development of the planning stage.)*

## Configuration Details (`configs/sfx_agent.yml`)

*(This section remains largely the same as the previous README, detailing the specific keys)*
*   **`elevenlabs`**: `voice`, `model`.
*   **`gemma`**: `model` (for Ollama).
*   **`output`**: `folder`, `file_format`.
*   **`prompt`**: `default_duration`, `prompt_influence` (fallback), `batch_influences` (primary for variations).
*   **`processing`**: `target_lufs`.
*   **`library`**: `path`.
*   **`logging`**: `level`.

## Development

**Running Tests:**

```bash
pytest -v
```
Show print statements:
```bash
pytest -v -s
```

## License

MIT
```

This version integrates the core ideas from the provided context, sets expectations about current vs. planned features, and provides a more comprehensive overview for anyone (including an LLM) trying to understand the project's scope and design.