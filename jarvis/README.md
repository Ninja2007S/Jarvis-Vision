# Jarvis — Phase 1: the core is alive

A private assistant that runs entirely on your own machine and answers from
your phone, anywhere, with no accounts, no API keys and no cost.

Phase 1 gets one thing working end to end: **text to your machine, model reply
back, streamed live, reachable from your phone over a private network.**
No voice yet, no camera yet. Those land on this same socket in Phases 2–5.

## What you need

- Python 3.10 or newer
- [Ollama](https://ollama.com) — free, runs the model locally
- A free [Tailscale](https://tailscale.com) account for phone access

## 1. Model

```bash
ollama pull qwen2.5:3b-instruct
```

About 2 GB, runs on a laptop without a GPU. If your machine has 16 GB of RAM
or a decent GPU, `ollama pull qwen2.5:7b-instruct` is noticeably sharper — put
whichever you pulled in `JARVIS_MODEL` in your `.env`.

## 2. Core

```bash
cd jarvis
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
python -m server.main
```

Open `http://localhost:8200`. Check `http://localhost:8200/healthz` if it
doesn't answer — it tells you whether the core, the model server, or the model
itself is the problem.

## 3. Your phone

Install Tailscale on both the machine and the phone, sign in to the same
account on each, then on the machine:

```bash
tailscale serve --bg 8200
```

`tailscale status` gives you the machine's name. On the phone, open
`https://<machine-name>.<your-tailnet>.ts.net` — Tailscale issues the HTTPS
certificate for free, which Phase 2 needs before iOS will hand over the
microphone.

Works from mobile data, from anywhere, without opening a single port. Add it
to your home screen and it opens like an app.

## Layout

```
server/config.py    settings, reads .env
server/llm.py       language core — streams from Ollama
server/session.py   conversation state and the persona
server/main.py      websocket bus, health, static client
client/             the console
```

The websocket protocol is in the docstring at the top of `server/main.py`.
Every later phase adds message types to it rather than a second server.

## Checks before Phase 2

- A reply streams in word by word rather than appearing all at once.
- Killing the core shows `reconnecting`, and restarting it recovers on its own.
- The phone reaches it over mobile data with wifi off.

---

# Phase 2: voice

Ears and a voice, on the same socket. Push-to-talk: hold the button, speak,
let go, hear it answer in your AirPods. Both pieces run on CPU — this
machine's Iris Xe has no CUDA, so Phase 2 never tries the GPU path.

## New pieces

- **Ears** — `faster-whisper`, the `small.en` model, int8-quantized. A
  five-second clip transcribes in well under a second on a 13th-gen i5.
- **Voice** — Piper, a free local TTS engine. Replies are split sentence by
  sentence as they stream in, so the first sentence starts speaking while
  the model is still writing the second.

## Setup

```bash
cd jarvis
source .venv/bin/activate
pip install -r requirements.txt
```

faster-whisper downloads its model automatically on first use — nothing to
do there. Piper needs one voice file, which is free but not bundled:

```bash
mkdir -p models
curl -L -o models/en_US-lessac-medium.onnx \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
curl -L -o models/en_US-lessac-medium.onnx.json \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

Browse [huggingface.co/rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices)
for other free voices and accents — swap the path in `.env`
(`JARVIS_TTS_MODEL`) to try one.

Restart the core:

```bash
python -m server.main
```

## Using it

Open the same Tailscale URL on your phone with AirPods connected. **Hold to
talk** while speaking, release when you're done. Text input still works —
useful when you're somewhere you can't talk out loud.

The button falls back to text-only automatically if the Piper voice file
isn't downloaded yet — you'll still get an answer, just not spoken aloud.

## iOS note

Safari only grants microphone access on HTTPS or `localhost`, which is
exactly what Tailscale's certificate gives you — this is why Phase 1 already
had you set that up.

## Layout additions

```
server/ears.py              speech-to-text — faster-whisper on CPU
server/voice.py             text-to-speech — Piper, streamed sentence by sentence
client/worklets/mic-capture.js   downsamples the mic to 16kHz PCM off the main thread
models/                     Piper voice files (not committed — see above)
```

## Checks before Phase 3

- Holding the talk button and speaking produces a transcript, then a spoken reply.
- Releasing early (a short clip) fails gracefully rather than hanging.
- A second sentence starts speaking with no audible gap after the first ends.
- Still works with wifi off, on mobile data, through Tailscale.

Phase 3 replaces holding a button with a wake word and voice-activity
detection, so it starts listening on its own and you can interrupt it while
it's mid-sentence.

---

# Hands: foundation

Gesture tracking, running directly against this PC's own webcam — a
separate local process from `server/`, on purpose. Losing the webcam should
never take down voice, and a phone reconnecting shouldn't interrupt a
mid-gesture drag. A later phase ("Fusion") gives them one shared sense of
state; for now they're independent so each is simple to get right.

This step recognizes gestures and shows you what it sees. It does not
touch your mouse, keyboard, or files yet — that's deliberate, so you can
verify the tracking is solid on your specific hands and lighting before
anything acts on it.

## Setup

```bash
pip install -r requirements.txt
python -m hands.app
```

A window opens showing your camera feed with hand skeletons drawn over it.
Press `q` to quit, `m` to flip mirroring if left/right feels backwards.

## The gesture vocabulary

| Gesture | Shape | Reserved for |
|---|---|---|
| `pinch` | thumb and index tip touching | click / select — the universal "confirm" |
| `point` | index out, rest curled | cursor movement |
| `open_palm` | all four fingers out | stop / release |
| `fist` | hand closed | grab / hold |
| `peace` | index + middle out | free for a future command |
| `thumbs_up` | thumb out, rest closed | confirm / yes |

These are geometric, not machine-learned — every threshold is one number in
`hands/gestures.py` (`PINCH_RATIO_THRESHOLD`, `EXTENDED_RATIO`). If a
gesture misfires consistently for your hand, that's the first place to
nudge, not a sign anything is broken.

---

# Hands: acting

Every gesture above now drives a real action, plus motion — swipe your
hand and it switches windows, hold a shape and move and it scrolls. This
is the biggest safety-relevant step so far: your hand is now moving your
actual mouse.

## Starts safe, on purpose

`python -m hands.app` opens **disarmed** — tracking, the overlay, and the
console log all run normally, but nothing touches your mouse or keyboard
until you press **`a`**. Watch the overlay tell you what it *would* do
first; arm it once you trust what you're seeing.

Once armed, dragging your physical mouse to any screen corner kills all
synthetic input instantly — that's pyautogui's built-in failsafe, and it's
on by default with no way to disable it from the gesture side. If a
gesture ever runs away with the cursor, that's your emergency stop.

## The full map

| Gesture / motion | Action |
|---|---|
| moving hand (any gesture except `fist`) | moves the cursor, smoothed |
| `pinch` start → end | mouse click; hold the pinch and move to drag |
| `fist` | clutch — freezes the cursor so you can reposition your hand, the way you'd lift a real mouse off the desk |
| `peace`, then move up/down | scroll — proportional to how far you move, either direction |
| `open_palm`, then swipe left/right | switch window (Alt+Tab / Cmd+Tab) |
| `open_palm`, then swipe up | task view / all-windows overview |
| `open_palm`, then swipe down | show desktop |
| `thumbs_up` | reserved — lands in the resizing and typing phases as "confirm" |

Window-management shortcuts are auto-detected by OS (`hands/actions.py`,
via `platform.system()`) — Windows and Linux get Alt+Tab, macOS gets
Cmd+Tab. Two things worth knowing about your platform:

- **macOS** needs Accessibility permission granted to your terminal (or
  Python) in System Settings before pyautogui can move anything.
- **Linux** needs an X11 session — Wayland blocks synthetic input on most
  desktop environments, and the "show desktop" shortcut varies by desktop
  environment, so check yours if `super+d` doesn't respond.

If the hand leaves frame mid-drag, the click releases automatically rather
than leaving the mouse button stuck down.

## Layout additions

```
hands/mouse.py      cursor smoothing
hands/motion.py      swipe detection from a short position history
hands/actions.py     the only file that touches the real mouse/keyboard
```

## Checks before Windows and apps

- Clicking and dragging feel deliberate, not laggy or overshooting the target.
- Scrolling direction matches the direction your hand actually moved.
- A left/right swipe reliably switches windows without misfiring during ordinary pointing.
- Pulling your hand out of frame mid-drag releases the click instead of leaving it stuck.

## What's next

1. **Windows and apps** — a gesture-to-app launcher (open a specific program per gesture), beyond just switching between what's already open.
2. **Gesture typing** — a floating on-screen keyboard, reusing this cursor mapping, pinch to strike a key.
3. **Picture resizing** — pinch distance drives on-screen zoom (works in most viewers via Ctrl+Scroll); a separate confirmed gesture batch-resizes files in a watched folder.

Each step reuses what came before rather than replacing it.

## Checks before Mouse

- Skeleton tracks smoothly at your desk distance and lighting, not just close to the camera.
- Each of the six gestures shows its correct name and holds it without flickering between two labels.
- Two hands in frame at once get tracked and labeled independently (left vs right).
