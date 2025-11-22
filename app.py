# backend/app.py
import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import openai
from dotenv import load_dotenv

load_dotenv()

OPENAI_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in environment before running.")

openai.api_key = OPENAI_KEY

app = Flask(__name__)
CORS(app, origins="*")


# The prompt template you provided — we'll inject values into the %s placeholders.
PROMPT_TEMPLATE = """You are a master of professional, trustworthy HTML email template design for internal corporate communications. Your task is to generate a visually appealing, fully responsive HTML email template based on provided input parameters.

Requirements:
- Use only email-safe HTML with inline CSS compatible with all major email clients (Outlook, Gmail, etc.).
- Apply the primary color for call-to-action buttons and main accents.
- Use the secondary color for background sections, dividers, or secondary buttons.
- Use the accent color for highlights, icons, and emphasized text.
- Layout should use tables for maximum compatibility.
- Header structure (IMPORTANT):
  * If approved logos are provided: Use the logo AS the header (centered, no colored header band). The logo should be the first visual element, replacing any header band.
  * If no approved logos are provided: Use a colored header band with the email subject/title in the primary color.
- Structure the template with: header (logo OR header band), greeting, body paragraphs, a call-to-action button, contact metadata, closing statement, signature, and footer with company reminders.
- Design must be modern, professional, with clean typography, proper spacing, and layout.
- Ensure the email is mobile-responsive.
- Incorporate relevant placeholders as needed.
- Output only the complete, ready-to-use HTML code wrapped between <HTML_FRAGMENT> and </HTML_FRAGMENT>, with no extra tags, comments, or explanation.
- Logo usage (when provided):
  * Include exactly ONE <img> element as the header that uses one of the approved URLs verbatim. Never invent or modify URLs.
  * Center the logo horizontally with appropriate padding (20-30px top/bottom).
  * Give the image meaningful alt text and constrain width to <=200px with inline CSS (height:auto to maintain aspect ratio).
  * The logo should stand alone as the header - no colored background band behind it.
- Never reference external resources besides the approved logo URL and inline styles.

- The model must automatically adapt color style, visual theme, and texture according to the brand identity of the selected logo.

Write a professional internal corporate email template in HTML format.

Input parameters:
- Topic: %s
- Mail details: %s
- Primary color: %s
- Secondary color: %s
- Accent color: %s

Use the placeholders from the following list as applicable:
Username, LandingPageURL, Company_email, Department, Manager_name, Manager_email, HR_Manager, Current_month, Current_year, Next_year, Current_day, Next_day, Previous_year, Current_time, Estimated_time, Future_date.

Approved logos you may choose from (use at most one):
%s

Generate a well-structured, polished email template that fits the topic and mail details, using the specified colors for styling.

--------------------------------------------------------
LANDING PAGE GENERATION (ADD THIS OUTPUT AFTER EMAIL)
--------------------------------------------------------
Now generate a professional, branded phishing-simulation landing page.

Landing Page Requirements:
- Output wrapped strictly between <LANDING_PAGE> and </LANDING_PAGE>.
- Use only inline CSS, no external styles, scripts, or fonts.
- Use the same Primary, Secondary, and Accent colors.
- Do NOT use a logo on the landing page.
- Instead, use this header prominently at the top:

  Important Security Notice
  You are part of an internal Cyber Attack Simulation drive.

- Structure:
  1. Text-only header above (centered, bold, well-spaced)
  2. A “Verification in Progress” or “Checking your request” style panel (to mimic a real service)
  3. Reveal message: This was a controlled phishing simulation
  4. Training explanation and next steps
  5. CTA button linking to LandingPageURL with inline CSS
  6. Footer with IT/Support contact details
- The landing page must visually match the brand identity of the logo used in the email.
- No external resources besides the approved logo URL (used only in email).
"""

# We'll wrap the user's prompt by asking the model to return a strict JSON object so parsing is deterministic.
# We append a short instruction to return ONLY JSON with two fields:
#  - email_html: string (the content between <HTML_FRAGMENT>...</HTML_FRAGMENT>)
#  - landing_page_html: string (the content between <LANDING_PAGE>...</LANDING_PAGE>)
# This instruction is separate from PROMPT_TEMPLATE and does not modify the user's template content.
JSON_RETURN_INSTRUCTION = (
    "\n\nIMPORTANT (for the assistant): After generating the HTML outputs, "
    "return a JSON object and nothing else with two keys: "
    "\"email_html\" (the full email HTML including the <HTML_FRAGMENT> ... </HTML_FRAGMENT> wrappers) "
    "and \"landing_page_html\" (the full landing page HTML including the <LANDING_PAGE> ... </LANDING_PAGE> wrappers). "
    "Do not include any extra text, explanation, or metadata. Strings must be valid JSON strings."
)


@app.route("/generate-email", methods=["POST"])
def generate_email():
    """
    Expected JSON body:
    {
      "topic": "...",
      "mail_details": "...",
      "primary_color": "#hex",
      "secondary_color": "#hex",
      "accent_color": "#hex",
      "approved_logos": [ {"name":"...", "url":"..."} , ... ]   # optional
    }
    """
    payload = request.json or {}
    topic = payload.get("topic", "Security Notification")
    mail_details = payload.get("mail_details", "Please take action")
    primary_color = payload.get("primary_color", "#1a73e8")
    secondary_color = payload.get("secondary_color", "#f5f5f5")
    accent_color = payload.get("accent_color", "#d93025")
    approved_logos = payload.get("approved_logos", [])

    # Prepare the logos replacement: a JSON-style string inserted into the prompt
    # If approved_logos is a Python list, convert to JSON string representation.
    if isinstance(approved_logos, (list, dict)):
        logos_str = json.dumps(approved_logos)
    else:
        # assume user sent already formatted string
        logos_str = str(approved_logos)

    # Fill the prompt template (order must match the %s placeholders)
    final_prompt = PROMPT_TEMPLATE % (
        topic,
        mail_details,
        primary_color,
        secondary_color,
        accent_color,
        logos_str,
    )
    # Append the JSON return instruction
    final_prompt_with_json = final_prompt + JSON_RETURN_INSTRUCTION

    try:
        # Call OpenAI ChatCompletion (Chat API)
        # Using ChatCompletion with gpt-4; adjust model as needed for your account.
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that must follow the user's prompt precisely."},
                {"role": "user", "content": final_prompt_with_json},
            ],
            temperature=0.15,
            max_tokens=3000,
        )
    except openai.error.OpenAIError as e:
        return jsonify({"error": str(e)}), 500

    # Extract assistant text
    try:
        assistant_text = response.choices[0].message["content"]
    except Exception as e:
        return jsonify({"error": "Unexpected response format from OpenAI", "detail": str(e)}), 500

    # The assistant was instructed to return pure JSON with the two keys
    try:
        parsed = json.loads(assistant_text)
        email_html = parsed.get("email_html", "")
        landing_page_html = parsed.get("landing_page_html", "")
    except Exception:
        # If parsing fails, return the raw assistant_text for debugging
        return jsonify({
            "error": "Failed to parse JSON from model output. Raw output returned for inspection.",
            "raw_output": assistant_text
        }), 500

    return jsonify({
        "email_html": email_html,
        "landing_page_html": landing_page_html
    })


@app.route("/")
def index():
    return jsonify({"status": "ok", "msg": "Email template generator backend running"})


if __name__ == "__main__":
    import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

