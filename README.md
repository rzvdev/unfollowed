# Unfollowed

Instagram automation bot built with Python.

**Unfollowed** manages the "Following" list of an Instagram account by acting like a real user:
- performs **unfollow** (and optionally **follow**) actions on targeted accounts
- moves the **mouse**, **clicks**, **scrolls**, and **types**
- detects buttons in the interface using **computer vision**, not via DOM / API

It does **not** use Playwright, Selenium, the Instagram API, or direct HTTP requests. Everything happens visually on screen.

---

## 📌 Table of Contents

1. [Goal](#-goal)  
2. [Features](#-features)  
3. [How It Works](#-how-it-works)  
4. [Architecture](#-architecture)  
5. [Requirements](#-requirements)  
6. [Setup](#-setup)  
7. [Run](#-run)  
8. [Safety / Anti-Flag Behavior](#-safety--anti-flag-behavior)  
9. [Limitations](#-limitations)  
10. [Disclaimer](#-disclaimer)  
11. [Status](#-status)

---

## ⚡ Goal

Typical use case: you have a list of accounts that don’t follow you back and you want to remove them from your Following list in a controlled, safe way — without clicking manually 200 times.

The app:
1. takes a list of target usernames (CSV)
2. finds those users in your Following list, directly in the Instagram UI
3. clicks `Following` → confirms `Unfollow`
4. enforces human-like pacing (delays, pauses, per-day limits)
5. logs every action

---

## ✨ Features

### Assisted Follow / Unfollow
- Processes users from a `.csv` file
- For each user: finds their username on screen, clicks `Following`, confirms `Unfollow`

### Real system interaction
- Moves the mouse to physical screen coordinates `(x, y)`
- Clicks (left/right), scrolls, types
- Simulates human keyboard input
- Does **not** read HTML, does **not** call internal Instagram functions

### Computer Vision
- Detects known UI elements (`Following`, `Unfollow`) with **template matching** (OpenCV)
- Works on live screenshots of the screen

### OCR (username verification)
- Reads the username text in each row of the Following popup using OCR
- Confirms it's the correct target before unfollowing
- Prevents unfollowing the wrong person

### Human-style rate limiting
- Randomized delays between actions (e.g. 10–30 seconds)
- Automatic breaks after N actions (e.g. 3-minute pause after 15 unfollows)
- Daily cap (e.g. 40 actions / day)
- Slight mouse jitter before clicking to look natural

### Logging
- Every action is saved under `logs/`
- Log format (CSV/JSON) includes:
  - processed username
  - timestamp
  - action (unfollow / skip)
  - result (ok / fail / rate limited)

### Dry Run Mode
- Test mode where the bot positions the mouse and identifies targets,
  but does **not** actually confirm the `Unfollow` click
- Useful for calibration and UI changes

---

## 🧠 How It Works

1. You open Instagram in a browser (Chrome/Edge), log in manually, open your own profile, and open the `Following` popup (the scrollable modal with accounts you follow).
2. Unfollowed loads a CSV file with target usernames (for example `not_following_back.csv`).
3. For each username:
   - Takes a screenshot of the visible part of the Following list
   - Runs OCR on each row to detect if that username is currently visible
   - Computes the position of the `Following` button in that same row (relative offset)
   - Moves the mouse there and clicks
   - Detects the confirmation popup (`Unfollow`) via template matching and confirms
   - Waits a randomized delay
4. After a certain number of actions, the bot automatically pauses for a few minutes
5. Continues until it finishes the batch or hits the daily limit

**Important:**  
The browser window must stay in the same position/size on screen.  
You should not touch the mouse or keyboard while it runs.

---

## 🏗 Architecture

Proposed project layout:

```text
unfollowed/
│
├─ core/
│   ├─ batch_runner.py        # Orchestrates CSV loop, pauses, limits, logging
│   ├─ unfollow_worker.py     # Executes the unfollow logic for a single username
│   └─ safety.py              # Handles limits, stops on rate-limit / block popups
│
├─ vision/
│   ├─ screen_capture.py      # Full / partial screenshots
│   ├─ template_matcher.py    # Finds UI elements (Following / Unfollow buttons)
│   ├─ ocr_reader.py          # OCR to extract usernames from the list
│   └─ locator.py             # Converts matches into precise click coordinates
│
├─ controller/
│   ├─ mouse_controller.py    # move_mouse_human_like(), click(), scroll()
│   ├─ keyboard_controller.py # type_text_human_like()
│   └─ timing.py              # random delays, pauses, jitter
│
├─ ui/
│   └─ app_ui.py              # Simple PyQt control panel: pick CSV, Start/Stop, live status
│
├─ config/
│   └─ config.yaml            # Runtime config (timing, limits, screen settings, etc.)
│
├─ data/
│   └─ not_following_back.csv # Input: target usernames to unfollow
│
├─ logs/
│   └─ session-2025-10-26.json  # Action history per session
│
└─ main.py                    # Application entry point
```

---

## 🔧 Requirements

**System:**
- Windows (tested with system-level mouse/keyboard interaction)
- Recommended resolution: `1920x1080` fullscreen browser window
- Instagram UI language: English (the bot expects `Following` / `Unfollow` labels)

**Runtime:**
- Python 3.10+

**Python dependencies:**
- `pyautogui` – mouse / keyboard / scroll control
- `opencv-python` – template matching for UI elements
- `pillow` – screenshots / image processing
- `pytesseract` + local Tesseract OCR – extracting usernames as text
- `pyyaml` – config loading
- `pandas` – CSV input + logging/reporting

---

## 🛠 Setup

1. Clone / download the project.

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install pyautogui opencv-python pillow pytesseract pyyaml pandas
   ```

4. Install Tesseract OCR on Windows (required for OCR).
   - After installing, if needed, configure the OCR path in code:
     ```python
     import pytesseract
     pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
     ```

5. Configure runtime behavior by editing `config/config.yaml`.

Example `config.yaml`:

```yaml
resolution: "1920x1080"

timing:
  delay_between_actions_seconds_min: 10
  delay_between_actions_seconds_max: 30
  pause_every_actions: 15
  pause_duration_seconds: 180   # 3 min
  daily_limit: 40

behavior:
  mode: "unfollow"              # other possible value: "follow"
  dry_run: true                 # if true, do not click final Unfollow

vision:
  template_match_threshold: 0.8
  ocr_enabled: true
```

---

## ▶️ Run

1. Open Chrome/Edge.
2. Log in to Instagram manually.
3. Go to your profile.
4. Open the `Following` list (the scrollable popup with accounts you follow).
5. Leave that popup in the foreground, fullscreen at 1920x1080.
6. Hands off the mouse from now on.

7. Run the bot:
   ```bash
   python main.py --input data/not_following_back.csv
   ```

8. While running, the bot will:
   - iterate through the usernames in the CSV
   - interact with the Instagram UI using mouse, scroll, and clicks
   - respect timing rules and cooldowns
   - write logs under `logs/`

9. The UI / console will show:
   - which username is being processed
   - how many actions were done today
   - whether the bot is paused (cooldown) or stopped due to rate limit

---

## 🧯 Safety / Anti-Flag Behavior

- **Human-like mouse movement**  
  The cursor does NOT teleport.  
  It moves along a smooth path and does a tiny "jitter adjust" (2–5px micro-movement) before clicking, like a human lining up the button.

- **Randomized timing**  
  Delays between actions are randomized (e.g. anywhere between 10s and 30s), not a fixed interval.

- **Automatic cooldowns**  
  After ~15 consecutive actions, the bot goes idle for a few minutes.

- **Daily limit**  
  The bot will not exceed a configured `daily_limit` (example: 40 unfollows / day).

- **Block detection**  
  If Instagram shows something like `Action blocked`, `Try again later`, or `You can't follow/unfollow right now`,  
  the bot attempts to detect that popup visually (template match) and immediately stops.

**Goal:** slow, human-style cleanup. Not spam.

---

## ⚠ Limitations

- You cannot use your PC normally while it runs.  
  The bot literally takes control of your mouse and keyboard.

- If you move the browser window, change zoom level, or change resolution, the click coordinates may become invalid.

- If Instagram changes its UI (button text, layout, theme), the visual templates used for detection may need to be updated.

- Instagram must be in English for accurate OCR / template matching.  
  If the UI says `Siguiendo` or `Urmărești` instead of `Following`, the bot won't recognize it.

- OCR is not 100% perfect. It can confuse similar characters (`l` vs `I`, `0` vs `O`).  
  The bot includes username verification logic, but edge cases still exist.

- The bot cannot run "in the background".  
  It needs focus and control of the main screen to behave like a human.

---

## 📜 Disclaimer

- This project is provided for personal / educational / assisted automation use only.
- Automated Follow/Unfollow behavior can violate Instagram’s Terms of Service. You are responsible for how you use this tool.
- The app does **not** use the private Instagram API, does **not** send custom HTTP requests, and does **not** inspect the DOM.  
  It behaves like a human: it looks at pixels and clicks.

This is **not** a growth/engagement/spam service.

---

## ✅ Status

- Current stage: design + technical plan for the Python implementation.
- Immediate goal: MVP with `dry_run: true` that can
  - detect the target username in the Following popup,
  - locate the matching `Following` button on that row,
  - calculate safe click coordinates,
  - and simulate the full action **without** confirming Unfollow yet.

Next step after MVP: enable live mode (`dry_run: false`) and persist per-session logs.
