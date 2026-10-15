# Bad Word Beep — Greek + English

A local, experimental microphone censor for Windows and OBS, created by
[Intzevidis7](https://github.com/Intzevidis7).

The app uses offline Vosk speech recognition to detect configured words and
replace matched speech with a beep in a delayed microphone feed sent through
VB-CABLE to OBS.

Version 0.3.0 provides three recognition modes: Greek only, English only,
and Greek + English. Only the recognizers required by the selected mode are
loaded. Editable language-specific word lists control targeted words and phrases.

The app runs on CPU. It does not require an AMD/NVIDIA GPU or a cloud
transcription account. Microphone audio is processed locally, and recognition
transcripts appear in the app log.

> Important: This is not a guaranteed profanity filter. It can miss words,
> beep innocent speech, or recognize a word after it has already played.
> Always test with a local OBS recording before streaming.

## Quick start

### What users need

- `BadWordBeep-Setup.exe` from this project's GitHub Release.
- [VB-CABLE](https://vb-audio.com/Cable/), installed separately.
- [OBS Studio](https://obsproject.com/download), if you want to use the app with OBS.
- Internet access for the first-time Vosk model download and several GB of free disk space.

End users do **not** need Python, Inno Setup, the source files, or the GitHub “Source code (zip)” archive.

### Windows SmartScreen warning

This first installer is **not code-signed**. Windows may display:

> Windows protected your PC  
> Microsoft Defender SmartScreen prevented an unrecognized app from starting.  
> App: BadWordBeep-Setup.exe  
> Publisher: Unknown publisher

This means Windows cannot verify the publisher of the EXE and has not established reputation for this new download. The warning does not by itself prove that the file is malicious, but it is not a safety guarantee either.

Only continue if you intentionally downloaded `BadWordBeep-Setup.exe` from this project's official GitHub Release and trust the project. Verify the filename and download location. If anything looks unexpected, cancel the launch.

If you choose to continue, click **More info → Run anyway**. Do not disable SmartScreen for your entire computer. Future unsigned builds may show the same warning. Code signing and Microsoft Store distribution are possible future improvements, but signing alone does not guarantee immediate removal of SmartScreen warnings.


### v0.3 recognition modes

Version 0.3 adds three recognition modes:

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

Stop and restart censoring after editing a list. The legacy `bad_words.txt` remains included for compatibility with older builds, but v0.3 uses the language-specific lists according to the selected mode.

### Installation

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
4. Choose a device entry whose default sample rate matches the microphone and supports mono. Device numbers can differ between PCs or change after driver updates.

## Configure OBS

**Only the microphone is delayed by this app.** It does not delay the entire OBS scene or automatically synchronize webcam video, game video, game sound, or other sources. OBS Stream Delay postpones the finished stream for viewers, but does **not** fix a mismatch between sources inside that stream. To synchronize the scene, the user must delay earlier video and other audio sources separately by the measured amount. This can require multiple settings or extra tools and may not be practical for every setup; check a local recording before going live.

1. Add an **Audio Input Capture** source in OBS.
2. Select **CABLE Output (VB-Audio Virtual Cable)** as the device.
3. Mute or remove every raw microphone route, including OBS `Settings → Audio → Mic/Aux`, webcam microphones, scene sources with the original mic, and Sonar/Fifine/mixer routes that carry it.
4. Keep only the processed CABLE route active. Otherwise, uncensored audio can leak into the stream.

**Routing terminology:** The app sends audio to `CABLE Input`; OBS receives it from `CABLE Output`.

## Test before streaming

1. Start the app and click **Start censor**. Wait until its status says **Running**.
2. In OBS, click **Start Recording**, not **Start Streaming**.
3. Speak normal speech and test words from the lists active in your selected mode:
   - Greek only: `bad_words_el.txt` and `bad_words_greeklish.txt`
   - English only: `bad_words_en.txt`
   - Greek + English: all three language-specific lists
4. Wait longer than the configured delay after the last word before stopping the recording.
5. Listen to the actual recording. Check voice, beeps, synchronization, background audio, and possible raw-microphone leaks.
6. Stop the app when finished. Closing its window also stops censoring.

The default microphone delay is six seconds. Changing it does not change an OBS delay or synchronize the scene. **Do not set OBS Stream Delay to six seconds expecting it to correct lip-sync**: that delays the already-combined output, leaving the microphone six seconds behind an undelayed picture. Align the other sources separately and verify the recording.

## Controls and logs

| Item | Description |
| --- | --- |
| Delay, default 6 seconds | Holds only microphone audio while recognition runs. It does not delay the scene or synchronize other sources. A longer delay is not a guarantee if processing falls behind. |
| Beep volume, default `0.04` | Try `0.02` for a quieter beep or `0` to silence matched words. |
| Open active word list | Opens the language-specific lists used by the selected mode. Use UTF-8 text files with one entry per line. Stop and restart censoring after editing. |
| Mute unanalyzed audio | Experimental. May create gaps and is not a fail-safe. |
| `PARTIAL HEARD [el/en]` | Interim recognition that may change. |
| `HEARD [el/en]` | Final transcript after an utterance boundary. |
| `BEEP [el/en]` | A word was marked for beeping at an estimated time. Duplicate lines may refer to overlapping model reports. |
| `PARTIAL` / `TOO LATE` | Some or all of the detected word played before it was marked. |
| `STATUS: lag el=... en=...` | Recognizer backlog. Persistent growth means the PC may not keep up. |

In single-language mode, only the selected recognizer processes microphone audio.
In Greek + English mode, both recognizers process the same input, which can
produce cross-language false matches. Results vary by PC, microphone, language,
pronunciation, and background noise.

A Greeklish word-list entry is a text-matching entry; it does not add a separate
Greeklish speech-recognition model.

The updated app also provides an **About / Credits** dialog with the developer
credit, GitHub link, third-party acknowledgments, and a reference to the release
license documents.

## Troubleshooting

### The app will not start and mentions `_internal\vosk`

This usually means an old broken build was installed. Rebuild with the corrected `build_windows.ps1`, confirm that `dist\BadWordBeep\_internal\vosk\libvosk.dll` exists, and install the newly generated setup EXE.

### Models are missing

Run the installed `BadWordBeep-Models.exe` again. Each model directory should contain `am\final.mdl`. If a model folder is incomplete, back it up or remove it before retrying.

### OBS receives no audio

Confirm that the app uses the microphone by name, the app output is `CABLE Input`, OBS input is `CABLE Output`, and you waited for the configured delay. Check the OBS mixer and the recorded file.

### Voice does not match video or game audio

This app delays only the microphone. OBS Stream Delay will not repair the mismatch. Other video/audio sources need their own appropriate delays; measure and verify them in a local recording. Some setups may need additional software or hardware to delay all sources reliably.

### An uncensored word is audible

Check that no raw microphone route reaches OBS. Inspect the app log for
`TOO LATE`, `PARTIAL`, recognizer backlog, or a mismatch between recognized text
and an entry in the active language-specific lists. Confirm that the selected
mode supports the spoken language. Restart censoring after editing a list.
The app cannot guarantee that every word will be censored.

### The beep is too loud or the wrong words beep

Lower the beep volume if needed. For primarily Greek or English streams,
choose the corresponding single-language mode to avoid unnecessary
cross-language recognition. False matches remain possible in every mode.
Review the log, edit the active lists carefully, restart censoring, and test
with a local recording.

## Build the Windows installer

These instructions are for the project owner or contributors with explicit permission. End users should download the release installer instead.

### Source files

```text
app.py
censor_engine.py
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
    VOSK-LICENSE.txt
    PYTHON-SOUNDDEVICE-LICENSE.txt
.gitignore
```

The build and installer configuration must package all language-specific word
lists, the application icon, `LICENSE`, `THIRD_PARTY_NOTICES.md`, and the
applicable third-party license files. Their presence in the source folder
alone does not confirm inclusion in the installer.

The current `build_windows.ps1` must bundle `vosk/libvosk.dll` into the GUI. The corrected builder discovers the installed Vosk package with `importlib.util.find_spec('vosk')`, passes `--add-binary "${voskDll}:vosk"` to PyInstaller, and refuses to package the installer unless `dist\BadWordBeep\_internal\vosk\libvosk.dll` exists.

### Build steps

1. Install [Python for Windows](https://www.python.org/downloads/) and [Inno Setup](https://jrsoftware.org/isdl.php) on the Windows build machine.
2. Confirm that the source folder contains the corrected `build_windows.ps1`.
3. Double-click `BUILD_WINDOWS.cmd` and wait for the final message confirming `release\BadWordBeep-Setup.exe`.
4. Check the result from PowerShell in the source folder:

```powershell
Test-Path ".\dist\BadWordBeep\_internal\vosk\libvosk.dll"
Test-Path ".\release\BadWordBeep-Setup.exe"
```

Both commands should return `True`.

If Inno Setup is installed at `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` but the builder cannot find it, use the corrected builder or compile the installer manually:

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" ".\installer.iss"
```

PyInstaller builds Windows applications on Windows; it does not cross-compile. Test the newly generated installer, model download, audio routing, and Greek/English recordings before publishing it.

`dist\BadWordBeep` is also a portable app folder. Keep the complete folder together; do not copy only `BadWordBeep.exe`. The `BadWordBeep-Models.exe` beside it downloads models for that portable folder.

Attach the verified `BadWordBeep-Setup.exe` as a GitHub Release asset. Do not commit the EXE or large Vosk model archives to the source repository.

## Files

The installed application folder contains the executable, model setup tool,
editable word lists, and release documentation.

- `settings.json` stores the saved configuration.
- `bad_words_el.txt`, `bad_words_en.txt`, and `bad_words_greeklish.txt`
  contain language-specific matching entries.
- `bad_words.txt` is retained for older-build compatibility; v0.3.0 uses the
  language-specific lists.
- `models/` contains downloaded speech-recognition models.
- `LICENSE` describes the applicable application license terms.
- `THIRD_PARTY_NOTICES.md` and `licenses/` contain third-party acknowledgments
  and license information.

Recognition transcripts appear in the application log. OBS recordings may
contain private speech; store and share recordings responsibly.

## Speech recognition and privacy

Bad Word Beep uses [Vosk](https://github.com/alphacep/vosk-api) for local,
offline speech recognition. Speech-recognition model files are not included in
this source repository; the installer can launch `BadWordBeep-Models.exe`, a separate model setup
tool that downloads Vosk models from the official model catalog.

Vosk is licensed under the Apache License, Version 2.0. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and
[`licenses/VOSK-LICENSE.txt`](licenses/VOSK-LICENSE.txt) for details.

Bad Word Beep processes microphone audio locally for speech recognition and
profanity detection. It does not intentionally upload microphone audio, stream
recordings, recognition transcripts, or user logs. OBS recordings may contain
private speech, so users should store and share recordings responsibly.

VB-CABLE and OBS have their own installation, licensing, and privacy
requirements. Consult their vendors before redistributing anything other than
this project’s own files.

## Credits

Bad Word Beep was created by [Intzevidis7](https://github.com/Intzevidis7).

© 2026 Intzevidis7. All rights reserved.

Developer and third-party acknowledgments are available in the updated
application's About / Credits dialog.

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

These terms do not revoke permissions already granted for material previously
distributed under the MIT License.

Third-party components remain subject to their own licenses. See
[`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and the applicable license
files in `licenses/`.
