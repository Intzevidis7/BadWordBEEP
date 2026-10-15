# Third-party notices

This project uses third-party software and models. Their licenses and
attribution requirements are summarized below.

## Vosk

This project uses [Vosk](https://github.com/alphacep/vosk-api), an offline
speech recognition toolkit developed by Alpha Cephei.

- Project: https://github.com/alphacep/vosk-api
- License: Apache License, Version 2.0
- License text: [`licenses/VOSK-LICENSE.txt`](licenses/VOSK-LICENSE.txt)

Vosk is used for local, offline speech recognition.

## Vosk models

Bad Word Beep uses the following downloadable Vosk models:

- `vosk-model-el-gr-0.7` — Greek model  
  Source: https://alphacephei.com/vosk/models  
  License: Apache License, Version 2.0

- `vosk-model-small-en-us-0.15` — English model  
  Source: https://alphacephei.com/vosk/models  
  License: Apache License, Version 2.0

The models are downloaded by the application’s model setup tool from the
official Alpha Cephei website. Users are responsible for complying with the
license terms applicable to the models they download and use.

Users are responsible for downloading models from the official source and for
complying with the applicable model license.

## Python dependencies

Python package dependencies and their versions are declared in the project
dependency file. Each dependency remains subject to its own license.

## Privacy

Bad Word Beep processes audio locally for speech recognition and profanity
detection. This repository does not collect, upload, or distribute user audio,
microphone recordings, stream recordings, or recognition transcripts.

## python-sounddevice

This project uses [python-sounddevice](https://github.com/spatialaudio/python-sounddevice)
for microphone input and audio playback.

- Project: https://github.com/spatialaudio/python-sounddevice
- License: MIT License
- License text: [`licenses/PYTHON-SOUNDDEVICE-LICENSE.txt`](licenses/PYTHON-SOUNDDEVICE-LICENSE.txt)

- ## Python and Tkinter

Bad Word Beep is developed with Python and uses Tkinter for its graphical
interface. Python and Tkinter are subject to the applicable Python Software
Foundation license terms included with the Python distribution used to build
the application.
