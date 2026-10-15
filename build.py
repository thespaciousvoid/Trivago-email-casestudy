#!/usr/bin/env python3
"""
Build the trivago Rate Connect onboarding email.

One source template (src/email.src.html) -> three outputs in dist/:

  rate-connect-onboarding.html            Static, sample data. Send from anywhere.
  rate-connect-onboarding.ampscript.html  Salesforce Marketing Cloud version (AMPscript).
  preview-multi-property.html             Static preview of the multi-property state.

Why a build step at all? The static and AMPscript files must stay identical apart
from the dynamic bits. Generating both from one source means a layout fix is made
once. The template only uses {{TOKENS}}; there is no templating engine.

Usage:
  python3 build.py                                   # images from ./images/ (local preview only)
  python3 build.py --img-base https://cdn.jsdelivr.net/gh/<user>/<repo>@main/images/

The --img-base must be a public absolute URL before the email is sent anywhere.
"""
import argparse
import pathlib
import re

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / "src" / "email.src.html"
DIST = ROOT / "dist"

# System font stack ~ SF Pro on Apple, Segoe UI on Windows, Roboto on Android.
# (Outlook desktop is forced to Segoe UI/Arial separately in the <head>.)
FONT = "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

BLUE = "#0088d9"

LINKS = {
    "URL_STUDIO": "https://studio.trivago.com/",
    "URL_CAMPAIGN": "https://studio.trivago.com/",       # TODO: deep link to the Rate Connect campaign page
    "URL_ADD_PROPERTY": "https://studio.trivago.com/",   # TODO: deep link to the add-property flow
    "URL_SUPPORT": "https://support.trivago.com/",
    "URL_LINKEDIN": "https://www.linkedin.com/company/trivago/",
}

SAMPLE_SINGLE = {"hotelier": "Anna", "properties": [("Hotel Sonnenhof", "15")]}
SAMPLE_MULTI = {
    "hotelier": "Anna",
    "properties": [("Alpenblick Apartments", "18"), ("Hotel Sonnenhof", "15"), ("Pension Am See", "12.5")],
}


# --------------------------------------------------------------------------- components

def number_badge(n: int) -> str:
    """Blue numbered circle. Outlook desktop has no border-radius, so it gets a VML oval."""
    return f"""                    <!--[if mso]>
                    <v:oval xmlns:v="urn:schemas-microsoft-com:vml" style="width:32px;height:32px;v-text-anchor:middle;" fillcolor="{BLUE}" stroke="f">
                      <v:textbox inset="0,0,0,0"><center style="font-family:'Segoe UI',Arial,sans-serif;font-size:14px;line-height:16px;font-weight:bold;color:#ffffff;">{n}</center></v:textbox>
                    </v:oval>
                    <![endif]-->
                    <!--[if !mso]><!-->
                    <table role="presentation" width="32" cellpadding="0" cellspacing="0" border="0" style="width:32px;">
                      <tr><td width="32" height="32" align="center" valign="middle" style="width:32px; height:32px; border-radius:16px; background-color:{BLUE}; font-family:{FONT}; font-size:14px; line-height:32px; font-weight:bold; color:#ffffff;">{n}</td></tr>
                    </table>
                    <!--<![endif]-->"""


def button(href: str, label: str, *, width: int, height: int, radius: int, bg: str, color: str,
           font_size: int, line_height: int, pad_y: int, pad_x: int, align: str = "center") -> str:
    """
    "Bulletproof" button.
    - Outlook desktop: VML roundrect (the only way to get rounded corners + a full clickable area).
    - Everyone else: a padded <a>, so the whole button is clickable, not just the text.
    Note: the VML width is fixed. Longer translated labels need a wider `width`.
    """
    arc = round(radius / height * 100)
    return f"""        <table role="presentation" cellpadding="0" cellspacing="0" border="0"{' align="center"' if align == 'center' else ''} style="margin:0 {'auto' if align == 'center' else '0 0 auto'};">
          <tr><td align="center" style="border-radius:{radius}px; background-color:{bg};">
            <!--[if mso]>
            <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{href}" style="height:{height}px;v-text-anchor:middle;width:{width}px;" arcsize="{arc}%" stroke="f" fillcolor="{bg}">
              <w:anchorlock/>
              <center style="color:{color};font-family:'Segoe UI',Arial,sans-serif;font-size:{font_size}px;font-weight:bold;">{label}</center>
            </v:roundrect>
            <![endif]-->
            <!--[if !mso]><!-->
            <a href="{href}" target="_blank" style="display:inline-block; background-color:{bg}; border-radius:{radius}px; color:{color}; font-family:{FONT}; font-size:{font_size}px; line-height:{line_height}px; font-weight:bold; text-decoration:none; white-space:nowrap; padding:{pad_y}px {pad_x}px; mso-hide:all;">{label}</a>
            <!--<![endif]-->
          </td></tr>
        </table>"""


P_GREY = "margin:4px 0 0 0; font-family:{f}; font-size:14px; line-height:20px; color:#4d4d4d; mso-line-height-rule:exactly;".format(f=FONT)


def rate_list_open() -> str:
    return (f'                    <p style="{P_GREY}">Current rates:</p>\n'
            '                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:8px;">\n')


def rate_row(name: str, rate: str) -> str:
    cell = f"padding:6px 0; border-bottom:1px solid #e8e8e8; font-family:{FONT}; font-size:14px; line-height:20px; mso-line-height-rule:exactly;"
    return (f'                      <tr><td style="{cell} color:#4d4d4d;">{name}</td>'
            f'<td align="right" style="{cell} color:#000000; font-weight:bold; white-space:nowrap; padding-left:12px;">{rate}</td></tr>\n')


def fmt_rate(r: str) -> str:
    return f"{float(r):g}%"


def static_rate_block(props) -> str:
    if len(props) == 1:
        return f'                    <p style="{P_GREY}">Current rate: {fmt_rate(props[0][1])}</p>'
    rows = "".join(rate_row(n, fmt_rate(r)) for n, r in props)
    return rate_list_open() + rows + "                    </table>"


# --------------------------------------------------------------------------- AMPscript

AMPSCRIPT_SETUP = r"""%%[
/* =========================================================================
   trivago Rate Connect onboarding — personalisation (AMPscript)
   -------------------------------------------------------------------------
   DATA MODEL (assumed; rename to match the real one):
   - Sendable DE / profile attribute  HotelierName
   - Data Extension  RC_Onboarding_Properties  (one row per property)
       SubscriberKey   Text
       PropertyName    Text
       CommissionRate  Decimal   e.g. 15.5 means 15.5 %
   - Fallback when a hotelier has no DE rows: profile attributes
       PropertyName, CommissionRate   (single-property sends)

   OUTPUT VARIABLES used in the HTML below:
     @hotelierName, @introSubject, @rateWord, @rateDisplay,
     @propertyCount, @rows, @shown, @more, URLs
   ========================================================================= */

VAR @hotelierName, @rows, @row, @propertyCount, @i, @shown, @maxShown, @more
VAR @propertyName, @commissionRate, @rateDisplay, @introSubject, @rateWord
VAR @pName, @pRate, @pRateDisplay
VAR @urlStudio, @urlCampaign, @urlAddProperty, @urlSupport, @urlLinkedIn

/* ---- Links: change them here only. Output via RedirectTo() so clicks are tracked. ---- */
SET @urlStudio      = "{URL_STUDIO}"
SET @urlCampaign    = "{URL_CAMPAIGN}"
SET @urlAddProperty = "{URL_ADD_PROPERTY}"
SET @urlSupport     = "{URL_SUPPORT}"
SET @urlLinkedIn    = "{URL_LINKEDIN}"

/* ---- Greeting: never render "Hello ," ---- */
SET @hotelierName = Trim(AttributeValue("HotelierName"))
IF Empty(@hotelierName) THEN
  SET @hotelierName = "there"
ENDIF

/* ---- Properties for this hotelier, alphabetical ---- */
SET @rows = LookupOrderedRows("RC_Onboarding_Properties", 0, "PropertyName ASC", "SubscriberKey", _subscriberkey)
SET @propertyCount = RowCount(@rows)

IF @propertyCount == 0 THEN
  /* No DE rows: fall back to profile attributes */
  SET @propertyName   = Trim(AttributeValue("PropertyName"))
  SET @commissionRate = AttributeValue("CommissionRate")
  IF Empty(@propertyName) THEN
    /* No property at all: skip this subscriber instead of sending "Now that  is live".
       The second argument (true) skips only this subscriber; the send continues. */
    RaiseError("Rate Connect onboarding: no property data for subscriber", true)
  ENDIF
  SET @propertyCount = 1
ELSEIF @propertyCount == 1 THEN
  SET @row            = Row(@rows, 1)
  SET @propertyName   = Field(@row, "PropertyName")
  SET @commissionRate = Field(@row, "CommissionRate")
ENDIF

IF @propertyCount == 1 THEN
  /* ---- Single property ---- */
  SET @introSubject = Concat(@propertyName, " is")
  SET @rateWord     = "rate"
  IF Empty(@commissionRate) THEN
    SET @rateDisplay = "not set yet"
  ELSE
    /* The percent sign is added here, not in the HTML: writing it straight after an
       inline output block would put three percent signs in a row and confuse the parser. */
    SET @rateDisplay = Concat(Format(@commissionRate, "#0.##", "Number"), "%")
  ENDIF
ELSE
  /* ---- Several properties: list up to @maxShown, then "+ N more" ---- */
  SET @introSubject = Concat("your ", @propertyCount, " properties are")
  SET @rateWord     = "rates"
  SET @maxShown     = 5
  IF @propertyCount > @maxShown THEN
    SET @shown = @maxShown
  ELSE
    SET @shown = @propertyCount
  ENDIF
  SET @more = Subtract(@propertyCount, @shown)
ENDIF
]%%"""


def amp_rate_block() -> str:
    single = f'                    <p style="{P_GREY}">Current rate: %%=v(@rateDisplay)=%%</p>'
    row = rate_row("%%=v(@pName)=%%", "%%=v(@pRateDisplay)=%%")
    return f"""%%[ IF @propertyCount == 1 THEN ]%%
{single}
%%[ ELSE ]%%
{rate_list_open()}%%[
  FOR @i = 1 TO @shown DO
    SET @row   = Row(@rows, @i)
    SET @pName = Field(@row, "PropertyName")
    SET @pRate = Field(@row, "CommissionRate")
    IF Empty(@pRate) THEN
      SET @pRateDisplay = "&ndash;"
    ELSE
      SET @pRateDisplay = Concat(Format(@pRate, "#0.##", "Number"), "%")
    ENDIF
]%%
{row}%%[ NEXT @i ]%%
                    </table>
%%[ IF @more > 0 THEN ]%%
                    <p style="{P_GREY} margin-top:8px;">+ %%=v(@more)=%% more in <a href="%%=RedirectTo(@urlStudio)=%%" target="_blank" style="color:{BLUE}; text-decoration:underline;">Business Studio</a></p>
%%[ ENDIF ]%%
%%[ ENDIF ]%%"""


# --------------------------------------------------------------------------- build

def render(tokens: dict) -> str:
    html = SRC.read_text(encoding="utf-8")
    for k, v in tokens.items():
        html = html.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{[A-Z0-9_]+\}\}", html)
    assert not left, f"Unreplaced tokens: {sorted(set(left))}"
    # Drop lines that became empty because a token rendered to nothing.
    html = re.sub(r"\n[ \t]*\n(?=[ \t]*\n)", "\n", html)
    return html


def common(img_base: str, links: dict) -> dict:
    t = {
        "FONT": FONT,
        "IMG": img_base,
        "NUM_1": number_badge(1),
        "NUM_2": number_badge(2),
        "NUM_3": number_badge(3),
    }
    t.update({k: v for k, v in links.items()})
    t["BUTTON_PRIMARY"] = button(links["URL_CAMPAIGN"], "View your campaign", width=227, height=52, radius=8,
                                 bg=BLUE, color="#ffffff", font_size=16, line_height=24, pad_y=14, pad_x=32)
    t["BUTTON_ADD"] = button(links["URL_ADD_PROPERTY"], "Add a property", width=124, height=36, radius=6,
                             bg="#ffffff", color="#000000", font_size=13, line_height=16, pad_y=10, pad_x=18,
                             align="right")
    return t


def build_static(img_base: str, sample: dict) -> str:
    props = sample["properties"]
    multi = len(props) > 1
    t = common(img_base, LINKS)
    t.update({
        "AMPSCRIPT_SETUP": "",
        "HOTELIER_NAME": sample["hotelier"],
        "INTRO_SUBJECT": f"your {len(props)} properties are" if multi else f"{props[0][0]} is",
        "RATE_WORD": "rates" if multi else "rate",
        "RATE_BLOCK": static_rate_block(props),
        # Multi-property hoteliers have already answered "Got more than one property?",
        # so the banner is cut (it contains comments itself, so it can't be commented out).
        "IF_SINGLE_START": "@@CUT_START@@" if multi else "",
        "IF_SINGLE_END": "@@CUT_END@@" if multi else "",
        # Static sends: point these at whatever the sending platform provides.
        "URL_PREFERENCES": "https://studio.trivago.com/",
        "URL_UNSUBSCRIBE": "https://studio.trivago.com/",
    })
    html = render(t)
    return re.sub(r"[ \t]*@@CUT_START@@.*?@@CUT_END@@\n?", "", html, flags=re.S)


def build_ampscript(img_base: str) -> str:
    amp_links = {
        "URL_STUDIO": "%%=RedirectTo(@urlStudio)=%%",
        "URL_CAMPAIGN": "%%=RedirectTo(@urlCampaign)=%%",
        "URL_ADD_PROPERTY": "%%=RedirectTo(@urlAddProperty)=%%",
        "URL_SUPPORT": "%%=RedirectTo(@urlSupport)=%%",
        "URL_LINKEDIN": "%%=RedirectTo(@urlLinkedIn)=%%",
    }
    setup = AMPSCRIPT_SETUP
    for k, v in LINKS.items():
        setup = setup.replace("{" + k + "}", v)
    t = common(img_base, amp_links)
    t.update({
        "AMPSCRIPT_SETUP": setup,
        "HOTELIER_NAME": "%%=v(@hotelierName)=%%",
        "INTRO_SUBJECT": "%%=v(@introSubject)=%%",
        "RATE_WORD": "%%=v(@rateWord)=%%",
        "RATE_BLOCK": amp_rate_block(),
        "IF_SINGLE_START": "%%[ IF @propertyCount == 1 THEN ]%%",
        "IF_SINGLE_END": "%%[ ENDIF ]%%",
        # Marketing Cloud system personalisation strings
        "URL_PREFERENCES": "%%subscription_center_url%%",
        "URL_UNSUBSCRIBE": "%%unsub_center_url%%",
    })
    return render(t)


def plain_text(sample: dict) -> str:
    """Plain-text alternative part. Spam filters score HTML-only mail worse, and some readers prefer it."""
    props = sample["properties"]
    multi = len(props) > 1
    subject = f"your {len(props)} properties are" if multi else f"{props[0][0]} is"
    if multi:
        rates = "Current rates:\n" + "\n".join(f"  - {n}: {fmt_rate(r)}" for n, r in props)
    else:
        rates = f"Current rate: {fmt_rate(props[0][1])}"
    banner = "" if multi else (
        "GOT MORE THAN ONE PROPERTY?\nAdd them to Rate Connect and reach more travellers across trivago.\n"
        f"Add a property: {LINKS['URL_ADD_PROPERTY']}\n\n")
    return f"""trivago Rate Connect

GET THE MOST FROM RATE CONNECT
Your campaign is live. Here is how to set yourself up for success.

Hello {sample['hotelier']},

Now that {subject} live on trivago, here are a few things to do now and keep in mind as your campaign grows.

1. Make your profile stand out:
List all your amenities, upload at least 30 high-quality photos, and add descriptions in the languages of your target markets. A complete profile attracts more travellers.

2. Keep an eye on your commission {'rates' if multi else 'rate'}:
{rates}
Your commission rate influences how visible your property is on trivago. You can adjust it any time in Business Studio to improve your results.

3. Watch your rate unavailability:
This shows how consistently trivago is receiving your website rates. The lower it is, the better your visibility. You will start seeing this data as your campaign runs.

View your campaign: {LINKS['URL_CAMPAIGN']}

{banner}Need a hand? Reach out to our Hotelier Support team: {LINKS['URL_SUPPORT']}
trivago Business Studio: {LINKS['URL_STUDIO']}
Follow us on LinkedIn: {LINKS['URL_LINKEDIN']}

--
You've received this email because your property is registered on trivago Business Studio.
trivago N.V., Kesselstrasse 5-7, 40221, Duesseldorf, Germany
Registration Office: Dutch Chamber of Commerce; Registration Number: 67222927
Copyright 2026 trivago | All rights reserved.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--img-base", default="../images/",
                    help="Absolute URL of the hosted images folder, ending in '/'. Default is a relative path for local preview.")
    args = ap.parse_args()
    base = args.img_base if args.img_base.endswith("/") else args.img_base + "/"

    DIST.mkdir(exist_ok=True)
    outputs = {
        "rate-connect-onboarding.html": build_static(base, SAMPLE_SINGLE),
        "rate-connect-onboarding.ampscript.html": build_ampscript(base),
        "preview-multi-property.html": build_static(base, SAMPLE_MULTI),
    }
    for name, html in outputs.items():
        (DIST / name).write_text(html, encoding="utf-8")
        kb = len(html.encode("utf-8")) / 1024
        # Gmail clips messages above ~102 KB and hides the rest behind "View entire message".
        warn = "  <-- over Gmail's 102 KB clipping limit!" if kb > 100 else ""
        print(f"dist/{name:42s} {kb:5.1f} KB{warn}")
    (DIST / "rate-connect-onboarding.txt").write_text(plain_text(SAMPLE_SINGLE), encoding="utf-8")
    print("dist/rate-connect-onboarding.txt                  (plain-text part)")
    if not base.startswith("http"):
        print("\nNOTE: images use a relative path. Rebuild with --img-base <public URL> before sending.")


if __name__ == "__main__":
    main()
