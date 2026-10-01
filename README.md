# Bad Word Beep — Greek + English

A **local, experimental** microphone censor for Windows and OBS. The desktop app runs two Vosk recognizers—Greek and English—against the same microphone input. Words listed in `bad_words.txt` are replaced with a beep in a delayed audio feed sent through VB-CABLE to OBS.

The app runs on CPU. It does not require an AMD/NVIDIA GPU, a cloud transcription account, or intentional audio uploads. Transcripts appear in the app log.

> **Important:** This is not a guaranteed profanity filter. It can miss words, beep innocent speech, or recognize a word after it has already played. Always test with a local OBS recording before streaming.

## Quick start

### What users need

- `BadWordBeep-Setup.exe` from this project's GitHub Release.
- [VB-CABLE](https://vb-audio.com/Cable/), installed separately.
- [OBS Studio](https://obsproject.com/download), if you want to use the app with OBS.
- Internet access and several GB of free disk space for the Vosk models.

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

1. Add an **Audio Input Capture** source in OBS.
2. Select **CABLE Output (VB-Audio Virtual Cable)** as the device.
3. Mute or remove every raw microphone route, including:
   - OBS `Settings → Audio → Mic/Aux`.
   - A webcam microphone.
   - Scene sources containing the original microphone.
   - Sonar, Fifine, mixers, or other applications carrying the original voice.
4. Keep only the processed CABLE route active. Otherwise, uncensored audio can leak into the stream.

**Routing terminology:** The app sends audio to `CABLE Input`; OBS receives it from `CABLE Output`.

## Test before streaming

1. Start the app and click **Start censor**. Wait until its status says **Running**.
2. In OBS, click **Start Recording**, not **Start Streaming**.
3. Speak normal speech and test Greek and English words from `bad_words.txt`.
4. Wait longer than the configured delay after the last word before stopping the recording.
5. Listen to the actual recording. Check voice, beeps, synchronization, background audio, and possible raw-microphone leaks.
6. Stop the app when finished. Closing its window also stops censoring.

The default delay is six seconds. OBS video, game audio, and other audio sources are not delayed automatically, so the microphone may be out of sync unless those sources are aligned separately.

## Controls and logs

| Item | Description |
| --- | --- |
| Delay, default 6 seconds | Holds microphone audio while recognition runs. A longer delay is not a guarantee if processing falls behind. |
| Beep volume, default `0.04` | Try `0.02` for a quieter beep or `0` to silence matched words. |
| Open word list | Opens `bad_words.txt` beside the installed EXE. Use one UTF-8 word or phrase per line. `#` starts a comment. Accents and case are ignored; add inflected and plural forms separately. Stop and restart censoring after changes. |
| Mute unanalyzed audio | Experimental. May create gaps and is not a fail-safe. |
| `PARTIAL HEARD [el/en]` | Interim recognition that may change. |
| `HEARD [el/en]` | Final transcript after an utterance boundary. |
| `BEEP [el/en]` | A word was marked for beeping at an estimated time. Duplicate lines may refer to overlapping model reports. |
| `PARTIAL` / `TOO LATE` | Some or all of the detected word played before it was marked. |
| `STATUS: lag el=... en=...` | Recognizer backlog. Persistent growth means the PC may not keep up. |

Both language recognizers process all microphone audio. They can falsely identify an English word during Greek speech or a Greek word during English speech. Results vary by PC, microphone, language, pronunciation, and background noise.

## Troubleshooting

### The app will not start and mentions `_internal\\vosk`

This usually means an old broken build was installed. Rebuild with the corrected `build_windows.ps1`, confirm that `dist\BadWordBeep\_internal\vosk\libvosk.dll` exists, and install the newly generated setup EXE.

### Models are missing

Run the installed `BadWordBeep-Models.exe` again. Each model directory should contain `am\final.mdl`. If a model folder is incomplete, back it up or remove it before retrying.

### OBS receives no audio

Confirm that the app uses the microphone by name, the app output is `CABLE Input`, OBS input is `CABLE Output`, and you waited for the configured delay. Check the OBS mixer and the recorded file.

### An uncensored word is audible

Check that no raw microphone route reaches OBS. Also inspect the app log for `TOO LATE`, `PARTIAL`, recognizer backlog, or a spelling mismatch in `bad_words.txt`. The app cannot guarantee that every word will be censored.

### The beep is too loud or the wrong words beep

Lower the beep volume. Both language models process all microphone audio, so false matches are possible. Edit the word list carefully and confirm changes with a recording.

## Build the Windows installer

These instructions are for contributors or the project owner. End users should download the release installer instead.

### Source files

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

## Privacy and files

After the models are installed, speech recognition runs locally on the PC. The app displays transcripts in its log, stores `settings.json` beside the installed app EXE, and keeps an editable `bad_words.txt` there. OBS recordings may contain private speech. This source does not intentionally upload microphone audio.

VB-CABLE and OBS have their own installation, licensing, and privacy requirements. Consult their vendors before redistributing anything other than this project's own files.

## License

No open-source license has currently been included. Unless a license is added, the project remains under the author's default copyright rights. Do not reuse, redistribute, or modify the source as though it were public-domain software.
