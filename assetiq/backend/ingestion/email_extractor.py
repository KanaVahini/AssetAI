"""
Handles .eml (real email export) and .txt (pasted email thread, treated
as plain text since it has no structured headers to parse reliably).
"""

import email
from pathlib import Path

from schema import make_doc_shell, make_page


def _extract_eml_body(msg) -> str:
    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode(errors="ignore"))
    else:
        payload = msg.get_payload(decode=True)
        body_parts.append(payload.decode(errors="ignore") if payload else str(msg.get_payload()))
    return "\n".join(body_parts)


def process_email(path) -> dict:
    path = Path(path)
    doc = make_doc_shell(path, "email")
    raw = path.read_text(errors="ignore")

    if path.suffix.lower() == ".eml":
        msg = email.message_from_string(raw)
        text = _extract_eml_body(msg)
        doc["metadata"].update({
            "from": msg.get("From"),
            "to": msg.get("To"),
            "subject": msg.get("Subject"),
            "date": msg.get("Date"),
        })
        page_meta = {"source_type": "email", "extraction_method": "email_headers_and_body"}
    else:
        text = raw  # plain pasted thread, no reliable headers to parse
        page_meta = {"source_type": "email", "extraction_method": "plain_text"}

    doc["pages"] = [make_page(1, text, tables=[], ocr_confidence=None, extra_meta=page_meta)]
    return doc
