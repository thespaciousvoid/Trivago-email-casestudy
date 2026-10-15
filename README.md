# trivago Rate Connect onboarding email

Responsive HTML email built from the `InternCaseStudy` Figma file.

| File | What it is |
|---|---|
| `dist/rate-connect-onboarding.html` | **The email.** Static, sample data (Anna / Hotel Sonnenhof / 15%). Works from any sending tool. |
| `dist/rate-connect-onboarding.ampscript.html` | Bonus: Marketing Cloud version. AMPscript fills name, property and commission rate, and switches between single- and multi-property content. |
| `dist/preview-multi-property.html` | Static preview of what a hotelier with 3 properties receives. |
| `dist/rate-connect-onboarding.txt` | Plain-text alternative part. |
| `images/` | Logos, icons and support avatar, exported from the Figma vectors at 3× (4× for the 15px icons). |
| `src/email.src.html` | The single source template all of the above is built from. |
| `build.py` | Builds `dist/` from the source (Python 3, no dependencies). |
| `send_test.py` | Sends the email to your own inboxes through Gmail SMTP for render testing. |
| `WRITEUP.md` | Approach, what broke, AI usage, next steps. |

## Images must be hosted before sending

Email clients only load images from public URLs. Easiest free option: push this folder
to a **public** GitHub repo and serve `images/` through the jsDelivr CDN:

```bash
python3 build.py --img-base https://cdn.jsdelivr.net/gh/<github-user>/<repo>@main/images/
```

Then commit the rebuilt `dist/` files. Open one image URL in a browser to check it loads.

## Editing

Change `src/email.src.html` (layout, copy) or `build.py` (links, buttons, AMPscript), then run
`python3 build.py`. Do not edit `dist/` by hand: it is overwritten on every build.

Each section in the source is labelled with its Figma frame name (`Hero/LightBlue`,
`Block/NumberedTips`, and so on).

## AMPscript data assumptions

- Profile attribute `HotelierName`
- Data Extension `RC_Onboarding_Properties`: `SubscriberKey`, `PropertyName`, `CommissionRate` (decimal, `15.5` = 15.5%)
- Fallback when a hotelier has no rows: profile attributes `PropertyName` and `CommissionRate`
- No property data at all: the subscriber is skipped (`RaiseError(..., true)`) instead of being sent a broken sentence

All link URLs are set in one block at the top of the AMPscript and in `LINKS` in `build.py`.
The campaign and add-property links are placeholders pointing at studio.trivago.com
until real deep links are known.
