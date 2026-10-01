# Bad Word Beep — Greek + English

A **local, experimental** microphone censor for Windows and OBS. The desktop app runs two Vosk recognizers (Greek and English) against the same microphone input. Recognized words listed in `bad_words.txt` are replaced with a beep in a delayed audio feed sent through VB-CABLE to OBS. It runs on CPU; it does not use an AMD/NVIDIA GPU, require a cloud transcription account, or upload mic audio. Transcripts appear in the app's log.

> **Not a guaranteed profanity filter.** It can miss words, beep innocent speech, or identify a word after it has played. Your installed Windows version has been reported working by the project tester, but every new build and audio routing configuration should still be tested using an OBS recording before streaming.

## Install and run

If you just want to use the program, you need **`BadWordBeep-Setup.exe`** from this project's GitHub Release; you do *not* need Python or Inno Setup. Do not download only `app.py` or `BadWordBeep.exe` and expect a complete install.

1. Install [VB-CABLE](https://vb-audio.com/Cable/) using the vendor's Windows instructions, and [OBS Studio](https://obsproject.com/download), if you have not already. VB-CABLE is a separate Windows audio driver; this installer does **not** download or install it, and a reboot may be required.
2. Run `BadWordBeep-Setup.exe`. It installs the app for your Windows user and adds a Start menu shortcut; an optional desktop shortcut is offered. The installer is not code-signed by this project, so verify the release before running it.
3. At the end, select **Download Greek and English Vosk models**. A console window will download/extract both models into the app's `models` folder. Keep it open until it reports **both models ready**. This needs internet and several GB of free space (including temporary extraction space). The Greek model is roughly 1.1 GB and English small model roughly 40 MB. If you skip it or it fails, run `BadWordBeep-Models.exe` from `%LOCALAPPDATA%\BadWordBeep` later. The installer does not silently install the models; downloading is optional at setup and required before starting censoring. Model archives come from the [official Vosk model catalog](https://alphacephei.com/vosk/models).
4. Open **Bad Word Beep** from Start. Choose the microphone by its full name, then choose **CABLE Input (VB-Audio Virtual Cable)** as *Playback output*. Select a device entry whose default sample rate matches the selected mic and accepts mono. Device numbers differ between PCs and can change after driver changes.
5. In OBS, add **Audio Input Capture** with **CABLE Output (VB-Audio Virtual Cable)**. Mute/remove *every* raw microphone route (scene sources, **Settings → Audio → Mic/Aux**, webcams, Sonar/fifine mixers carrying the original voice), otherwise uncensored audio can leak into the stream. CABLE Input is the playback side the app sends to; CABLE Output is the recording side OBS receives.
6. Click **Start censor** and wait for **Running**. Click **Start Recording** in OBS—not Start Streaming. Speak normal speech and Greek/English words from `bad_words.txt`. Wait *longer than the configured delay* after the last word before stopping the recording. Listen to the actual file to check voice, beeps, leaks and synchronization. OBS video, game audio and RTMP phone audio are **not** delayed automatically; a six-second mic delay will put audio out of sync unless other sources are aligned appropriately.
7. Click **Stop** in the app when finished. Closing the window stops the censor. The app's `settings.json` remembers your settings and selected device descriptions.

## Controls and logs

| Item | What it does |
| --- | --- |
| Delay (default 6 seconds) | Holds mic audio to allow recognition; longer is not a guarantee if processing falls behind. |
| Beep volume (default `0.04`) | Try `0.02` for quieter beeps or `0` to silence matched words. |
| Open word list | Opens `bad_words.txt` next to the installed EXE. One word per line, UTF-8. `#` starts a comment. Accents/case are ignored; add inflected and plural forms separately. Stop and restart censoring after changes. |
| Mute unanalyzed audio | Experimental alternative to passing through unanalyzed audio. Can create gaps and cannot prevent errors or later revisions from either recognizer. Not a true fail-safe. |
| `PARTIAL HEARD [el/en]` | Interim guess from one language model; may change. |
| `HEARD [el/en]` | Final transcript after an utterance boundary. |
| `BEEP [el/en]` | Word marked for beeping at an estimated time. Duplicate lines can refer to overlapping model reports. Check the recording. |
| `PARTIAL` / `TOO LATE` | Some/all of the detected word already played before it was marked. |
| `STATUS: lag el=... en=...` | Recognizer backlog; persistent growth means the PC cannot keep up. `unanalyzed passed` means audio went to OBS before both models had processed it. `muted` shows gaps in experimental mute mode. |

Two simultaneous language recognizers can falsely detect an English word during Greek speech or vice versa. The Vosk publisher describes its Greek model as not extremely accurate. The sample recording previously tested in this project looked promising, but results vary. [Vosk model list](https://alphacephei.com/vosk/models)

## Build the Windows installer

For contributors: put the following **source files** together in a fresh Windows project folder:

```text
app.py
censor_engine.py
models_setup.py
bad_words.txt
requirements-build.txt
installer.iss
build_windows.ps1
BUILD_WINDOWS.cmd
README.md
.gitignore
```

The **current `build_windows.ps1` must bundle `vosk/libvosk.dll`** into the GUI. Do **not** use the earlier build script that omitted it (the installed app crashed before opening), nor the first hotfix that incorrectly searched `.venv\vosk`. The corrected builder discovers the installed Vosk package with `importlib.util.find_spec('vosk')`, passes `--add-binary "${voskDll}:vosk"` to PyInstaller, and refuses to package the installer unless `dist\BadWordBeep\_internal\vosk\libvosk.dll` exists. [PyInstaller usage](https://pyinstaller.org/en/stable/usage.html)

1. Install [Python for Windows](https://www.python.org/downloads/) and [Inno Setup](https://jrsoftware.org/isdl.php) **on the build machine**. The finished installer does not require them on an end-user machine. Check that your source folder contains the *corrected* builder named `build_windows.ps1`.
2. Double-click **`BUILD_WINDOWS.cmd`** and wait for the last line confirming `release\BadWordBeep-Setup.exe`. It creates/reuses `.venv`, installs `numpy`, `scipy`, `sounddevice`, `vosk`, `pyinstaller`, bundles a GUI EXE and a separate model-downloader EXE, validates Vosk's DLL path, and compiles the setup file using Inno Setup's `ISCC.exe`. PyInstaller does not cross-compile; build the Windows EXEs on Windows. [PyInstaller manual](https://pyinstaller.org/en/stable/index.html)
3. Check the result in PowerShell from the source folder:

```powershell
Test-Path ".\dist\BadWordBeep\_internal\vosk\libvosk.dll"
Test-Path ".\release\BadWordBeep-Setup.exe"
```

Both should return `True`. If `ISCC.exe` is installed at `C:\Program Files (x86)\Inno Setup 6\ISCC.exe` but the builder cannot find it, check you are using the corrected script. You can compile the finished portable folder without rerunning pip/PyInstaller using:

```powershell
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" ".\installer.iss"
```

4. Install the **new** setup EXE on your own Windows machine and test *the installed app*, model download, audio routing, Greek and English recording. Do not publish a build merely because compilation succeeded. `dist\BadWordBeep` is also a portable app folder: keep all files together, not only `BadWordBeep.exe`. The one-file `BadWordBeep-Models.exe` beside it downloads models for that folder.

GitHub source releases should contain the source files and README; attach the verified installer as a GitHub Release asset. **Do not put the EXE inside the Git repository**. The model ZIPs are also too large to commit; the model downloader fetches them on each installation. Only run build and install scripts from a source you trust.

## Troubleshooting

- **`FileNotFoundError ... _internal\vosk` at startup:** That is the *old broken build*. Rebuild with the corrected `build_windows.ps1`, confirm `libvosk.dll` exists at the path above, then run the newly generated setup EXE to update the installed app. Running an old installer again will not fix it.
- **App says models are missing:** Run installed `BadWordBeep-Models.exe` again, or extract both official models so each directory under `models` contains `am\final.mdl`. An existing incomplete model folder is not overwritten automatically; back it up/remove it before retrying.
- **No OBS audio:** Verify mic by name, select CABLE Input in the app and CABLE Output in OBS, wait for the delay, and check OBS mixer/recording tracks.
- **A raw word is audible:** Verify no other mic reaches OBS; check `TOO LATE`, `PARTIAL`, backlog and the recognized word spelling in `bad_words.txt`. The app cannot guarantee every word.
- **Builder says `Missing Vosk DLL: ...\.venv\vosk\libvosk.dll`:** This is the *outdated hotfix*, not a missing pip package. Replace `build_windows.ps1` with the corrected one; the package actually lives under `.venv\Lib\site-packages\vosk` on the tested Windows machine.
- **Builder cannot find Inno Setup:** Install the official compiler. A successful PyInstaller build alone yields the portable folder but *not* the new setup EXE. Rerun the corrected build or call `ISCC.exe` as shown above once the correct portable folder exists.
- **Beep too loud:** Lower beep volume. **Wrong words beeped:** both models process all mic audio, including speech in the other language; edit the list carefully and confirm results with a recording.

## Privacy and files

The app processes speech on the local PC after both Vosk models are installed. It displays transcripts in its log, writes `settings.json` beside the installed app EXE and stores editable `bad_words.txt` there. OBS recordings can contain private speech. The source code does not intentionally upload audio. VB-CABLE and OBS have their own installation/licensing requirements; consult their vendors before redistributing anything besides your own app.
