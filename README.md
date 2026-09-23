# commutree-videobio

Renders a 1080x1920 (9:16) Hindi video biodata for CommuTree from a JSON row + photos.

## Files
- `vb2.py` — renderer. `python3 vb2.py profile.json`
- `header.png` — fixed branded header (1080x1920, top ~335px used)
- `music.wav` — original background track (free to use, no copyright claim)
- `profile.example.json` — field reference

## Working dir must contain
`profile.json`, `p1.jpg` (required), optional `p2.jpg` / `father.jpg` / `mother.jpg`,
`fonts/` (4 Noto fonts), `header.png`, `music.wav`.

## Fonts (downloaded at render time)
NotoSerifDevanagari-Bold, NotoSansDevanagari-SemiBold, NotoSerif-Bold, NotoSans-SemiBold
from https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/

## Requirements
ffmpeg, libraqm (Hindi shaping — mandatory), python3, pillow, qrcode

## JSON fields
id, type (वर/कन्या), name, show_name (bool), city, dob (dd/mm/yyyy), birth_time,
birthplace, height, manglik, education, work, income, father, father_work, mother,
gotra[4] (blanks dropped), privacy (clear|blur|hide), profile_url

## NEVER commit personal data
No filled profile.json, no member photos, no sheet links. Template only.
