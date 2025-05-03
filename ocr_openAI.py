# ocr_template_extractor_app.py – v6 (OpenAI ≥ 1.0 compatible)
# -------------------------------------------------------------------------
# Streamlit PO OCR extractor using OpenAI Python v1 interface (no regex)
# -------------------------------------------------------------------------

import os
import io
import json
import tempfile
from datetime import datetime
from typing import Dict, List, Any

import streamlit as st
from PIL import Image
import pdfplumber
import pytesseract

# ----------------------
# 🔑 API key configuration
# ----------------------
OPENAI_API_KEY = "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"  # ← put your key here or set $OPENAI_API_KEY

# Import the new OpenAI client (v1)
try:
    import openai
    client = openai.OpenAI(api_key=OPENAI_API_KEY or os.getenv("OPENAI_API_KEY"))
except ImportError:
    st.error("openai package is missing – run `pip install openai`.")
    st.stop()
except AttributeError:
    st.error("Detected an old openai‑python version. Upgrade: `pip install --upgrade openai`.")
    st.stop()

# --------------------
# JSON PO schema template
# --------------------
JSON_TEMPLATE: Dict[str, Any] = {
    "po_number": "",
    "po_date": "YYYY-MM-DD",
    "order_type": "",
    "status": "",
    "supplier_number": "",
    "ship_via": "",
    "fob": "",
    "confirm": "",
    "supplier": {
        "name": "",
        "address": {
            "line1": "",
            "line2": "",
            "city": "",
            "state": "",
            "postal_code": "",
            "country": ""
        },
        "phone": "",
        "fax": "",
        "email": ""
    },
    "ship_to": {
        "name": "",
        "address": {
            "line1": "",
            "line2": "",
            "city": "",
            "state": "",
            "postal_code": "",
            "country": ""
        }
    },
    "bill_to": {
        "name": "",
        "address": {
            "line1": "",
            "line2": "",
            "city": "",
            "state": "",
            "postal_code": "",
            "country": ""
        },
        "phone": "",
        "fax": "",
        "email": ""
    },
    "terms": "",
    "reference": "",
    "notes": "",
    "special_instructions": [""],
    "line_items": [
        {
            "line_number": 1,
            "item_number": "",
            "description": "",
            "uom": "",
            "supplier_part_number": "",
            "quantity": 0,
            "due_date": "YYYY-MM-DD",
            "unit_price": 0.0,
            "total_price": 0.0,
            "status": "",
            "requisitioner": "",
            "requisition_number": "",
            "work_order": ""
        }
    ],
    "page_total": 0.0,
    "po_total": 0.0,
    "buyer": {
        "name": "",
        "email": "",
        "phone": ""
    },
    "authorization": ""
}

# -------------------------------
# OCR helper (pdfplumber + pytesseract)
# -------------------------------

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text; OCR fallback for scanned pages."""
    text_list = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            txt = page.extract_text() or ""
            if not txt.strip():
                image = page.to_image(resolution=300).original
                txt = pytesseract.image_to_string(image)
            text_list.append(txt)
    return "\n".join(text_list)

# -------------------------------
# GPT‑based field extraction
# -------------------------------

def extract_fields_with_gpt(doc_text: str) -> Dict[str, Any]:
    """Send the entire document text to GPT and ask for PO JSON."""
    prompt = (
        "You are a precise data‑extraction engine. "
        "Read the purchase‑order text and output **only** valid JSON conforming to this schema.\n\n"
        f"```json\n{json.dumps(JSON_TEMPLATE, indent=2)}\n```\n\n"
        "Fill every field you can. Leave impossible or missing values as empty strings or zeros. "
        "Return the JSON and nothing else.\n\n"
        "--- BEGIN DOCUMENT ---\n" + doc_text + "\n--- END DOCUMENT ---"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        st.error(f"OpenAI extraction failed: {e}")
        return JSON_TEMPLATE

# --------------------
# Streamlit UI
# --------------------
st.set_page_config(page_title="PO OCR → JSON (GPT)", layout="wide")
st.title("📄 Purchase Order OCR → Structured JSON via GPT")

# Template download
st.sidebar.download_button(
    "⬇️ Download blank PO template",
    data=json.dumps(JSON_TEMPLATE, indent=2),
    file_name="po_template.json",
    mime="application/json"
)

# File uploader
files = st.file_uploader("Upload PDF POs", type=["pdf"], accept_multiple_files=True)

if files:
    results: List[Dict[str, Any]] = []
    for f in files:
        st.subheader(f"Processing **{f.name}** …")
        text = extract_text_from_pdf(f.read())
        with st.expander("🔍 OCR Text (debug)"):
            st.text(text[:5000] + ("…" if len(text) > 5000 else ""))

        data = extract_fields_with_gpt(text)
        results.append(data)
        st.json(data, expanded=False)

    # Download all PO JSONs
    st.sidebar.download_button(
        "⬇️ Download extracted JSON array",
        data=json.dumps(results, indent=2),
        file_name="po_extracted.json",
        mime="application/json"
    )
else:
    st.info("Upload one or more PDF files to begin.")

