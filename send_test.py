#!/usr/bin/env python3
"""
Send the built email to your own inboxes for render testing (free, no ESP needed).

Uses Gmail's SMTP server with an App Password:
  1. Google account -> Security -> turn on 2-Step Verification.
  2. Google account -> Security -> App passwords -> create one (16 characters).
  3. Run:
       export SMTP_USER="you@gmail.com"
       export SMTP_APP_PASSWORD="abcd efgh ijkl mnop"
       python3 send_test.py you@gmail.com you@outlook.com you@icloud.com

Send to a Gmail, an Outlook.com/Hotmail and an iCloud address, then open each in
web + mobile app (and the Outlook desktop app if you have it) to cover the
clients in the brief.

The script refuses to send if images still point at a relative path, because
recipients would see broken images.
"""
import os
import pathlib
import smtplib
import sys
from email.message import EmailMessage

DIST = pathlib.Path(__file__).parent / "dist"
HTML_FILE = DIST / "rate-connect-onboarding.html"
TEXT_FILE = DIST / "rate-connect-onboarding.txt"
SUBJECT = "Get the most from Rate Connect"


def main():
    recipients = sys.argv[1:]
    if not recipients:
        sys.exit("Usage: python3 send_test.py recipient@example.com [more recipients...]")

    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_APP_PASSWORD")
    if not (user and password):
        sys.exit("Set SMTP_USER and SMTP_APP_PASSWORD first (see the top of this file).")

    html = HTML_FILE.read_text(encoding="utf-8")
    if 'src="../images/' in html or 'src="images/' in html:
        sys.exit("Images use a relative path. Rebuild first:\n"
                 "  python3 build.py --img-base https://cdn.jsdelivr.net/gh/<user>/<repo>@main/images/")

    msg = EmailMessage()
    msg["Subject"] = SUBJECT
    msg["From"] = f"trivago Business Studio (test) <{user}>"
    msg["To"] = ", ".join(recipients)
    msg.set_content(TEXT_FILE.read_text(encoding="utf-8"))   # plain-text part
    msg.add_alternative(html, subtype="html")                # HTML part

    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(user, password)
        s.send_message(msg)
    print(f"Sent to: {', '.join(recipients)}")


if __name__ == "__main__":
    main()
