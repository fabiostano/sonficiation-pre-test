# Auditory biofeedback stimulus pre-test

An internal, fully within-subjects oTree experiment using the existing
`intro → stimulus_test → outro` app structure and oTree 6.0.15.

Each participant completes 40 comparisons: four base sounds × five acoustic
characteristics × two endpoints. Sound A is always the baseline; Sound B is the
comparison. Reference magnitude is always **100**. The experiment asks what mental
states sounds **represent**, separately from how annoying or pleasant they sound.
No audio synthesis, filtering, resampling, or modulation takes place in oTree.

## Audio files required

**The repository does not include the 44 MP3s.** Session creation is blocked with
a list of missing files until all have been supplied. No substitute audio is created.

Create these 11 files in **each** of `_static/stimuli/base_01/`,
`base_02/`, `base_03/`, and `base_04/`:

| Reference / characteristic | Filename(s) in each base folder |
| --- | --- |
| Baseline | `baseline.mp3` |
| Pitch | `pitch_low.mp3`, `pitch_high.mp3` |
| Roughness | `roughness_low.mp3`, `roughness_high.mp3` |
| Brightness | `brightness_low.mp3`, `brightness_high.mp3` |
| Noisiness | `noisiness_low.mp3`, `noisiness_high.mp3` |
| Pulse frequency | `pulse_frequency_low.mp3`, `pulse_frequency_high.mp3` |

That is four baseline files and 40 manipulated files. File paths are defined in
[`stimulus_test/manifest.json`](stimulus_test/manifest.json); change that manifest
if your files use different paths. Each base must share the same baseline across
its ten comparisons, with a distinct path for each manipulated endpoint.

Optional `actual_parameter_value`, `actual_parameter_unit`, and `stimulus_id`
metadata can be omitted or left `null`. Values are saved as metadata and never
used to generate participant responses or shown in the interface. Increment the
manifest `version` when changing stimuli or metadata.

Validate before collecting data:

```bash
source .venv/bin/activate
python -m stimulus_test.validate --prepare
```

Validation checks all 40 combinations, path safety, baseline consistency, and all
44 nonempty MP3 files. It does **not** verify decoding, duration, loudness, or the
acoustic manipulation. Check these yourself, including constant modulation depth
for pulse-frequency variants.

Preparation copies the original MP3 bytes to content-hashed filenames under
`_static/stimuli/prepared/`. These neutral playback URLs prevent filenames such as
`roughness_high.mp3` from disclosing conditions. They are exact copies, without
audio processing. Preparation also happens automatically at session creation.
Keep this generated folder available to the server and retain it for existing
sessions; it is ignored by Git and is regenerated from the source files as needed.
If deploying to a read-only filesystem, prepare the files before deployment.

## Procedure and persistence

1. **Introduction:** optional tester ID, listening setup, baseline volume check,
   instructions, and optional baseline-versus-itself practice. Practice responses
   are stored in `intro` and excluded from the 40 analysed comparisons.
2. **Each comparison, step 1:** mental activation, mental workload, and attentional
   focus on discrete −3…+3 sliders, followed by independent annoyance and
   pleasantness ratings on 1…7 scales. There are no preselected responses.
3. **Each comparison, step 2:** the acoustic characteristic is revealed after the
   first responses have been saved. An initially empty field accepts any positive,
   finite magnitude estimate, including decimals and 100. Estimates are not recoded
   or constrained by endpoint direction.
4. **Breaks:** optional, untimed pages after comparisons 10, 20, and 30.
5. **Outro:** optional general feedback, perceptual ambiguity, suitability feedback,
   and a thank-you page.

Every participant receives 20 randomly ordered two-trial blocks. Endpoints stay
adjacent. For **each characteristic**, two bases are high-first and two are
low-first, giving ten blocks of each order overall. The full schedule is generated
once at session creation and saved in `participant.trial_schedule`. Reloads and
reconnections do not regenerate it. Trial metadata, wording configuration, and
playback paths are snapshotted into the database.

The two assessment pages have separate forms; previous responses cannot be
overwritten by resubmitting the next stage. `assessments_saved` marks the first
stage; `trial_completed` becomes true only after a valid magnitude estimate.
The final questionnaire sets `outro.completed` when submitted.

Audio uses native HTML5 controls, with no autoplay or playback-speed controls.
With JavaScript enabled, Sound B unlocks after Sound A finishes. That UI state
persists across the two stages and resets for the next comparison. Playback is
not measured server-side or used as proof that a participant listened. Native
players and radio controls remain available if JavaScript is unavailable.
Known media errors are displayed and block submission while the error persists.

## Configuration

- [`settings.py`](settings.py): session name, demo participant count,
  `enable_practice`, and `break_every` (`0` disables breaks; otherwise use a positive
  even number so a break never splits a pair). Endpoint balancing is always enabled.
- [`stimulus_test/manifest.json`](stimulus_test/manifest.json): source MP3 paths,
  manifest version, optional physical parameter metadata, and internal IDs.
- [`stimulus_test/config.py`](stimulus_test/config.py): characteristic wording,
  accessible explanations, mental-state dimensions, scale labels, and feature
  defaults. Change `enabled` to disable a mental dimension. Add a dimension with a
  unique `mental_…` or `attentional_…` field name to create a separate model/export
  column; trial generation needs no changes. Model changes require a fresh
  development database. The initial 4 × 5 × 2 design and reference 100 are fixed.
- App HTML templates and `_static/global/pretest.css`: participant wording/layout.

Restart the server and create new sessions after changing configuration. Keep
configuration and model fields fixed while a session is active. Preserve the
prepared audio used by existing sessions even if replacing source MP3s.

## Launch

Tested with Python 3.13; the preparation utility requires Python 3.11 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m stimulus_test.validate --prepare
otree devserver
```

On Windows activate with `.venv\Scripts\activate`. Open <http://localhost:8000>
and choose **Auditory stimulus pre-test**. For shared testing, create a session in
the admin interface and distribute participant links.

The earlier two-stimulus scaffold's sessions are not compatible with this model.
Before running, stop any old server, export any data you need, and move its
`db.sqlite3` to a backup location. oTree creates a fresh database on startup.

For hosting, set `OTREE_ADMIN_PASSWORD`, `OTREE_SECRET_KEY`, and
`OTREE_AUTH_LEVEL=STUDY` in the environment. The default secret is for local
development only. This project does not automatically load `.env` files.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python tests/run_checks.py
```

This runs in an isolated temporary database without touching project session data.
It checks the design over 100 schedules; adjacency and balance; manifest errors;
missing files; first/intermediate/last comparisons; all 40 rounds with two bots in
each of two cases; mandatory responses; decimal and invalid numeric inputs;
configuration switches; stable reloads; separate stage persistence; duplicate
submissions; breaks; and trial-level exports.

**These automated checks mock audio preparation and template file-existence checks.
They create no audio files and do not test playback.** Once the real files are in
place, also run the standard oTree bots against the actual file preparation:

```bash
otree test stimulus_pretest 2 --export /tmp/auditory-pretest-bot-exports
```

An optional browser UI check is available in `tests/check_browser.py` if Playwright
and a desktop Chromium executable are already installed:

```bash
python tests/check_browser.py --executable '/path/to/chrome'
```

This checks the sliders, keyboard interaction, responsive layout, empty numerical
input, validation, and stage transitions. It also mocks audio paths and simulates
the reference-ended UI event; it does not play or decode audio. Before collection,
manually test real MP3 playback, volume, replays, and navigation in your target browsers.

## Export results

In oTree admin, open **Data**. Standard app/combined exports contain all model
fields. Choose the **custom export for `stimulus_test`** for one row per participant
per comparison, including session/participant codes, tester ID, the complete
condition/order metadata, source and prepared audio paths, manifest version/hash,
configuration snapshot, raw responses, and completion flags.

There are 40 rows per participant, including unfinished comparisons. Use
`trial_completed` to select complete trials; retained first-stage responses can
still be inspected for incomplete trials. Practice, listening setup, and final
questionnaire answers are in the separate `intro`/`outro` or combined export.
No analysis transformations or hypothesized sound-to-mental-state mappings are
applied during collection.
