# Requirements Quality Lab

A runnable four-label requirements-review application with a transparent offline baseline, an optional LLM adapter, a local web UI, JSON/CSV exports, and evaluation metrics.

Python **3.11+**, standard library only. Created in November 2026 as a new portfolio implementation inspired by the requirements-classification work in my resume. This is not a reproduction or validation of the full LC LQ ontology or a historical model evaluation.

## Quick start

~~~bash
git clone https://github.com/abelberhanuu/requirements-quality-lab.git
cd requirements-quality-lab
python app.py serve
~~~

Open **http://127.0.0.1:8767**. Paste requirements, load a file, choose a review mode, filter findings, and download JSON or CSV.

## CLI

~~~bash
python app.py analyze --input examples/requirements.csv
python app.py analyze --input examples/requirements.csv --format csv --output review.csv
python app.py evaluate --input examples/requirements.csv
python -m unittest discover -s tests -v
~~~

Inputs: text (one statement per line), JSON (an array of id/text objects), or CSV with id/text columns. IDs are optional but must be unique when provided. Each batch permits 1–50 requirements of at most 3,000 characters each.

## Defect labels

| Label | Baseline signal |
| --- | --- |
| incomplete | Missing actor/modal/action, unfinished condition, or TBD/TODO marker |
| meaningless | Promotional phrases with no observable acceptance criterion |
| redundant | At least 95% token-set overlap with an earlier item, with matching number and negation sets |
| ambiguous | A small explicit list of unbounded quality terms |

The baseline flags candidates, not semantic truth. It can miss defects, overflag valid requirements, and mistake similar statements for duplicates. An unflagged statement still requires human review. Baseline rewrite text is guidance, not an automatically approved replacement.

## Optional LLM mode

Use an installed local model through Ollama's compatible endpoint, or another endpoint supporting JSON-mode chat completions.

~~~bash
# Linux/macOS; choose a model already installed in your model server
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_MODEL=YOUR_INSTALLED_MODEL
# For a provider requiring credentials, set LLM_API_KEY securely in the environment.
python app.py analyze --input examples/requirements.csv --mode llm
# Or restart the UI after setting the environment:
python app.py serve
~~~

PowerShell equivalents use $env:LLM_BASE_URL and $env:LLM_MODEL. Model installation and hosting are separate from this repository.

The adapter posts to the configured base URL plus /chat/completions, requests JSON mode, and validates IDs, labels, and review fields. It rejects provider redirects, credential-bearing URLs, and non-loopback plaintext HTTP. Requests time out after 30 seconds. There is no silent fallback to baseline.

LLM mode sends input text to the configured endpoint. Use synthetic or appropriately authorized requirements; credentials stay on the local Python server. Requirements are placed in a data message, but model output still requires human review.

Reference: [Ollama compatibility documentation](https://github.com/ollama/ollama/blob/main/docs/api/openai-compatibility.mdx).

## Evaluation and evidence

The included **16 examples are hand-authored illustrative fixtures**, not an independent benchmark. The evaluate command reports per-label and micro precision, recall, and F1 on the supplied expected_labels. Multiple expected labels are separated with a pipe in CSV or supplied as a list in JSON. Empty labels mean no listed defect.

Do not present toy-fixture scores as real-world model accuracy. Live model quality and availability have not been measured here. Tests cover the offline rules, file validation, duplicate safeguards, CSV escaping, metric calculations, HTTP review, and the LLM request/response protocol using a local mock endpoint.

## Architecture

reviewer.py contains parsing, baseline rules, provider integration, and evaluation. app.py provides CLI/API routing. web.py serves the loopback-only UI. static/ renders findings using text nodes, and tests/ supplies deterministic checks.

No model weights, API keys, actual client requirements, or historical evaluation results are included.
