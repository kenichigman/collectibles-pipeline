"""Optional tier-2 classifier: a local LLM behind an Ollama-compatible
HTTP endpoint.

Off unless BOTH environment variables are set:

    PIPELINE_LLM_URL    e.g. http://localhost:11434   (no trailing slash)
    PIPELINE_LLM_MODEL  e.g. llama3.1:8b

Design rule inherited from the system this rebuilds: model output is
untrusted input. The response must be JSON naming one of the known
classes; anything else — unparseable, an unknown label, a timeout, a
refused connection — returns None and the caller keeps the rule-based
result. The tier is a second opinion, never a dependency.
"""

import json
import os
import urllib.request

TIMEOUT = 10


def llm_classify(title, issue, publisher, year, grade, classes):
    url = os.environ.get("PIPELINE_LLM_URL")
    model = os.environ.get("PIPELINE_LLM_MODEL")
    if not url or not model:
        return None
    prompt = (
        "Classify this comic book into exactly one of these classes: "
        + ", ".join(classes)
        + f".\nTitle: {title} #{issue}\nPublisher: {publisher or 'unknown'}"
        f"\nYear: {year or 'unknown'}\nGrade: {grade or 'ungraded'}"
        '\nAnswer with JSON only: {"class": "<one of the classes>"}'
    )
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": "json",
        }
    ).encode()
    req = urllib.request.Request(
        url.rstrip("/") + "/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = json.loads(resp.read())
        answer = json.loads(body["message"]["content"])
        cls = answer.get("class")
    except Exception:
        return None
    return cls if cls in classes else None
