# Bad Word Beep — Greek + English

A local, experimental microphone censor for Windows and OBS, created by
[Intzevidis7](https://github.com/Intzevidis7).

The app uses offline Vosk speech recognition to detect configured words and
replace matched speech with a beep in a delayed microphone feed sent through
VB-CABLE to OBS.

Version 0.4.0 adds an optional AI audio keyword model. Vosk remains the main
Greek word-list recognizer; the v4 model works alongside it as a helper
detector for target speech patterns.

The installer includes your trained v4 checkpoint:

```text
models/keyword_v4/model.pt
```

When you enable **Enable AI audio keyword model** for the first time, the app
automatically downloads the required XLS-R encoder into:

```text
models/keyword_v4/pretrained/
```

The app runs on CPU. It does not require an AMD/NVIDIA GPU or a cloud
transcription account. Microphone audio is processed locally, and recognition
transcripts appear in the app log.

> Important: This is not a guaranteed profanity filter. It can miss words,
> beep innocent speech, or recognize a word after it has already played.
> Always test with a local OBS recording before streaming.

## How Vosk and AI work together

Bad Word Beep can run **Vosk and the AI audio keyword model at the same time**.
They analyze the same delayed microphone stream independently.

| System | What it does | When it triggers a beep |
| --- | --- | --- |
| Vosk | Converts speech to Greek text and matches entries in the active word lists | When a listed word is recognized |
| AI audio keyword model | Analyzes 2-second audio windows directly from sound | When a target reaches the configured confidence threshold |
| Censor engine | Delays microphone audio and inserts the beep | When either Vosk or the AI model detects a target |

Vosk is the primary detector because it provides precise, editable word-list
control. The AI model is a supplementary detector for cases where Vosk misses,
mishears, or does not transcribe a target expression correctly.

If both systems detect the same speech, the overlapping audio region is beeped
only once.

## Quick start

### What users need

- `BadWordBeep-Setup.exe` from this project's GitHub Release.
- [VB-CABLE](https://vb-audio.com/Cable/), installed separately.
- [OBS Studio](https://obsproject.com/download), if you want to use the app with OBS.
- Internet access for the first-time Vosk model download and several GB of free disk space.
- Internet access on the first AI-enabled run, so the app can download XLS-R.

End users do **not** need Python, Inno Setup, the source files, or the GitHub “Source code (zip)” archive.

### Windows SmartScreen warning

This installer is **not code-signed**. Windows may display:

> Windows protected your PC  
> Microsoft Defender SmartScreen prevented an unrecognized app from starting.  
> App: BadWordBeep-Setup.exe  
> Publisher: Unknown publisher

This means Windows cannot verify the publisher of the EXE and has not established reputation for this new download. The warning does not by itself prove that the file is malicious, but it is not a safety guarantee either.

Only continue if you intentionally downloaded `BadWordBeep-Setup.exe` from this project's official GitHub Release and trust the project. Verify the filename and download location. If anything looks unexpected, cancel the launch.

If you choose to continue, click **More info → Run anyway**. Do not disable SmartScreen for your entire computer.

### Vosk recognition modes

- **Greek only — fastest for Greek streams:** loads the Greek Vosk model and uses `bad_words_el.txt` plus `bad_words_greeklish.txt`.
- **English only — fastest for English streams:** loads the English Vosk model and uses `bad_words_en.txt`.
- **Greek + English — mixed speech, higher CPU use:** loads both recognizers and uses all three language lists.

For Greek-focused streams, use **Greek only** to avoid loading the English recognizer. Greek + English mode uses substantially more memory because it runs two offline recognizers.

The language lists are editable UTF-8 files next to the installed application:

```text
bad_words_el.txt
bad_words_en.txt
bad_words_greeklish.txt
```

Stop and restart censoring after editing a list.

## Enable AI audio detection

The AI audio keyword model is optional. When disabled, Bad Word Beep uses only
the selected Vosk recognizer(s).

To enable it:

1. Open Bad Word Beep.
2. Select **Enable AI audio keyword model (experimental)**.
3. Click **Start censor**.
4. On the first AI-enabled run, wait while XLS-R downloads automatically.

The detector analyzes a 2-second, 16 kHz mono audio window every 0.25 seconds.
If your microphone or CABLE device uses 44.1 kHz, the app automatically
resamples each 2-second window to 16 kHz before classification.

The current default AI confidence threshold is `0.65`. A detected target beeps
the most recent 0.45 seconds of audio. Repeated detections of the same label
are suppressed for 0.7 seconds.

AI audio detection requires `torch` and `transformers`. These are included in
the Windows build requirements; the GUI installer bundles the trained v4
checkpoint and downloads XLS-R on first AI use.

## Installation

1. Download `BadWordBeep-Setup.exe` from the GitHub Release assets.
2. Install [VB-CABLE](https://vb-audio.com/Cable/) using the vendor's Windows instructions. This installer does **not** install VB-CABLE. A reboot may be required.
3. Install [OBS Studio](https://obsproject.com/download) if needed.
4. Run `BadWordBeep-Setup.exe`. It installs the app for your Windows user and creates a Start-menu shortcut. A desktop shortcut is optional.
5. At the end of setup, select **Download Greek and English Vosk models**. Keep the console window open until it reports that both models are ready.
6. The model download requires internet and several GB of free space, including temporary extraction space. The Greek model download is roughly 1.1 GB and the English small model roughly 40 MB; extracted files require additional space. The model archives come from the [official Vosk model catalog](https://alphacephei.com/vosk/models).
7. If model setup is skipped or fails, run `BadWordBeep-Models.exe` from `%LOCALAPPDATA%\BadWordBeep` later. Censoring cannot start until the required models are installed.

## Configure the app

1. Open **Bad Word Beep** from the Start menu.
2. Select your microphone by its full device name.
3. Select **CABLE Input (VB-Audio Virtual Cable)** as **Playback output**.
4. Choose a device entry whose default sample rate matches the microphone and supports mono.
5. Enable **Enable AI audio keyword model** only if you want the optional AI helper detector.

## Configure OBS

**Only the microphone is delayed by this app.** It does not delay the entire OBS scene or automatically synchronize webcam video, game video, game sound, or other sources.

1. Add an **Audio Input Capture** source in OBS.
2. Select **CABLE Output (VB-Audio Virtual Cable)** as the device.
3. Mute or remove every raw microphone route, including OBS `Settings → Audio → Mic/Aux`, webcam microphones, scene sources with the original mic, and Sonar/Fifine/mixer routes that carry it.
4. Keep only the processed CABLE route active. Otherwise, uncensored audio can leak into the stream.

**Routing terminology:** The app sends audio to `CABLE Input`; OBS receives it from `CABLE Output`.

## Test before streaming

1. Start the app and click **Start censor**. Wait until its status says **Running**.
2. In OBS, click **Start Recording**, not **Start Streaming**.
3. Speak normal speech and test words from the lists active in your selected mode.
4. If AI audio detection is enabled, test target speech and listen for `BEEP [audio]` entries in the activity log.
5. Wait longer than the configured delay after the last word before stopping the recording.
6. Listen to the actual recording. Check voice, beeps, synchronization, background audio, false positives, and possible raw-microphone leaks.
7. Stop the app when finished. Closing its window also stops censoring.

The default microphone delay is six seconds. Changing it does not change an OBS delay or synchronize the scene.

## Controls and logs

| Item | Description |
| --- | --- |
| Delay, default 6 seconds | Holds only microphone audio while recognition runs. |
| Beep volume, default `0.04` | Try `0.02` for a quieter beep or `0` to silence matched words. |
| Open active word list | Opens the language-specific lists used by the selected mode. |
| Mute unanalyzed audio | Experimental. May create gaps and is not a fail-safe. |
| Enable AI audio keyword model | Optional helper detector that analyzes audio directly alongside Vosk. |
| `PARTIAL HEARD [el]` | Interim Vosk recognition that may change. |
| `HEARD [el]` | Final Vosk transcript after an utterance boundary. |
| `BEEP [el]` | Vosk matched a word in an active list. |
| `BEEP [audio]` | The AI audio keyword model detected a target above its threshold. |
| `TOO LATE [audio]` | The AI detection referred to audio that had already been played. |
| `AI audio recognition error` | The AI model or its audio-window processing failed. |
| `STATUS: lag el=...` | Vosk recognizer backlog. Persistent growth means the PC may not keep up. |

False positives are possible with both Vosk and AI audio detection. Review the
activity log and test with local recordings before streaming.

## Troubleshooting

### The app will not start and mentions `_internal\vosk`

This usually means an old broken build was installed. Rebuild with the corrected `build_windows.ps1`, confirm that `dist\BadWordBeep\_internal\vosk\libvosk.dll` exists, and install the newly generated setup EXE.

### Vosk models are missing

Run the installed `BadWordBeep-Models.exe` again. Each Vosk model directory should contain `am\final.mdl`.

### XLS-R downloads on first AI use

This is expected. The first time you enable **Enable AI audio keyword model**, the app downloads the XLS-R encoder into:

```text
models/keyword_v4/pretrained/
```

Leave the app and internet connection open until the download finishes.

### AI audio detection produces errors

Install or update `torch` and `transformers` in the environment used to run the
application. Confirm that `models/keyword_v4/model.pt` exists and that the
microphone/CABLE devices use matching default sample rates.

### OBS receives no audio

Confirm that the app uses the microphone by name, the app output is `CABLE Input`, OBS input is `CABLE Output`, and you waited for the configured delay.

### Voice does not match video or game audio

This app delays only the microphone. OBS Stream Delay will not repair the mismatch. Other video/audio sources need their own appropriate delays.

### An uncensored word is audible

Check that no raw microphone route reaches OBS. Inspect the app log for
`TOO LATE`, `PARTIAL`, recognizer backlog, or a mismatch between recognized text
and an entry in the active language-specific lists. If AI detection is enabled,
check for `BEEP [audio]` entries and adjust the threshold or model only after
additional testing.

### The beep is too loud or the wrong words beep

Lower the beep volume if needed. For primarily Greek streams, choose **Greek only**. False matches remain possible in every mode. Review the log, edit the active lists carefully, restart censoring, and test with a local recording.

## Build the Windows installer

These instructions are for the project owner or contributors with explicit permission. End users should download the release installer instead.

### Source files

```text
app.py
censor_engine.py
keyword_audio_detector.py
models_setup.py
bad_words.txt
bad_words_el.txt
bad_words_en.txt
bad_words_greeklish.txt
requirements-build.txt
installer.iss
build_windows.ps1
BUILD_WINDOWS.cmd
README.md
app.ico
LICENSE
THIRD_PARTY_NOTICES.md
licenses/
.gitignore
```

The build and installer configuration must package all language-specific word
lists, the application icon, `LICENSE`, `THIRD_PARTY_NOTICES.md`, and the
applicable third-party license files.

The current `build_windows.ps1` bundles `vosk/libvosk.dll`, includes
`keyword_audio_detector.py`, collects the required `torch` and `transformers`
runtime files, and bundles the trained v4 checkpoint at:

```text
dist/BadWordBeep/models/keyword_v4/model.pt
```

The large XLS-R encoder is not bundled; it downloads automatically on the first
AI-enabled run.

### Build steps

1. Install [Python for Windows](https://www.python.org/downloads/) and [Inno Setup](https://jrsoftware.org/isdl.php) on the Windows build machine.
2. Run `BUILD_WINDOWS.cmd`.
3. Wait for the final message confirming `release\BadWordBeep-Setup.exe`.
4. Check the result from PowerShell in the source folder:

```powershell
Test-Path ".\dist\BadWordBeep\_internal\vosk\libvosk.dll"
Test-Path ".\dist\BadWordBeep\models\keyword_v4\model.pt"
Test-Path ".\release\BadWordBeep-Setup.exe"
```

All three commands should return `True`.

PyInstaller builds Windows applications on Windows; it does not cross-compile. Test the newly generated installer, model download, audio routing, Vosk recognition, AI audio detection, and Greek recordings before publishing it.

## Release checklist

Before publishing `v0.4.0`:

- Merge `feature/audio-keyword-detector` into `main`.
- Confirm the README documents both Vosk and AI audio detection.
- Confirm `torch` and `transformers` are included in the build/runtime requirements.
- Confirm the installer bundles `models/keyword_v4/model.pt`.
- Confirm XLS-R downloads on the first AI-enabled run.
- Rebuild the Windows installer.
- Test a local recording with Vosk only.
- Test a local recording with Vosk and AI audio detection enabled.
- Confirm that no raw microphone route reaches OBS.
- Attach the verified `BadWordBeep-Setup.exe` to the GitHub Release.
- Do not commit the EXE or XLS-R cache to the source repository.

## Files

The installed application folder contains the executable, model setup tool,
editable word lists, and release documentation.

- `settings.json` stores the saved configuration.
- `bad_words_el.txt`, `bad_words_en.txt`, and `bad_words_greeklish.txt` contain language-specific matching entries.
- `models/` contains downloaded Vosk models and, after the first AI-enabled run, the XLS-R encoder cache.
- `models/keyword_v4/model.pt` is bundled with the installer.
- `LICENSE` describes the applicable application license terms.
- `THIRD_PARTY_NOTICES.md` and `licenses/` contain third-party acknowledgments and license information.

## Speech recognition and privacy

Bad Word Beep uses [Vosk](https://github.com/alphacep/vosk-api) for local,
offline speech recognition. The optional AI audio keyword model also processes
microphone audio locally.

Speech-recognition model files are not included in this source repository. The
installer can launch `BadWordBeep-Models.exe`, a separate model setup tool that
downloads Vosk models from the official model catalog.

Vosk is licensed under the Apache License, Version 2.0. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and
[`licenses/VOSK-LICENSE.txt`](licenses/VOSK-LICENSE.txt) for details.

Bad Word Beep processes microphone audio locally for speech recognition and
profanity detection. It does not intentionally upload microphone audio, stream
recordings, recognition transcripts, or user logs. OBS recordings may contain
private speech, so users should store and share recordings responsibly.

VB-CABLE and OBS have their own installation, licensing, and privacy requirements.

## Credits

Bad Word Beep was created by [Intzevidis7](https://github.com/Intzevidis7).

© 2026 Intzevidis7. All rights reserved.

## License and permitted use

Current releases are distributed under the custom terms in
[`LICENSE`](LICENSE), not the MIT License.

The custom license permits users to download and run official, unmodified
releases for personal and streaming use, including monetized streams.

It does not grant general permission to reuse the source code, publish modified
versions, redistribute the application, or sell copies. Additional permissions
require prior written authorization from Intzevidis7.

People wishing to contribute should contact Intzevidis7 before submitting code.
Source-code contributions require separately agreed contribution terms.

Third-party components remain subject to their own licenses. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and the applicable license
files in `licenses/`.
