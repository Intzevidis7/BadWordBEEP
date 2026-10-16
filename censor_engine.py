# ============================================================
#  Bad Word Beep — censor engine
#  Created by Intzevidis7
#  GitHub: https://github.com/Intzevidis7
#
#  "The beep is not censorship; it is dramatic timing."
# ============================================================
import json
import math
import queue
import threading
import time
import unicodedata
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.signal import resample_poly
from vosk import KaldiRecognizer, Model, SetLogLevel

ASR_RATE = 16000
AUDIO_WINDOW_SECONDS = 2.0
AUDIO_HOP_SECONDS = 0.25
AUDIO_BEEP_SECONDS = 0.8


def normalize(value):
    value = unicodedata.normalize('NFD', str(value).casefold())
    return ''.join(ch for ch in value if unicodedata.category(ch) != 'Mn' and ch.isalnum())


def load_words(paths):
    words = set()
    for path in paths:
        path = Path(path)
        for line in path.read_text(encoding='utf-8').splitlines():
            word = normalize(line.split('#', 1)[0].strip())
            if word:
                words.add(word)
    if not words:
        raise ValueError('The active word lists are empty')
    return words


class Censor:
    def __init__(self, input_id, output_id, delay, volume, mode, greek_path, english_path, word_paths, fail_closed=False, events=None, audio_model=False, audio_model_dir=None, audio_threshold=0.65):
        self.emit = events or (lambda line: None)
        self.input_id, self.output_id = int(input_id), int(output_id)
        self.delay_s, self.volume, self.fail_closed = float(delay), float(volume), bool(fail_closed)
        if not 2 <= self.delay_s <= 120 or not 0 <= self.volume <= .3:
            raise ValueError('Delay must be 2–120 seconds, volume 0–0.3')
        if mode not in ('el', 'en', 'both'):
            raise ValueError('Unknown recognition mode')
        self.words = load_words(word_paths)
        self.rate = round(sd.query_devices(self.input_id)['default_samplerate'])
        if self.rate != round(sd.query_devices(self.output_id)['default_samplerate']):
            raise ValueError('Mic and cable use different default sample rates')
        sd.check_input_settings(device=self.input_id, channels=1, samplerate=self.rate)
        sd.check_output_settings(device=self.output_id, channels=1, samplerate=self.rate)
        SetLogLevel(-1)
        self.models = {}
        if mode in ('el', 'both'):
            if not (Path(greek_path) / 'am' / 'final.mdl').is_file():
                raise FileNotFoundError(f'Greek model missing: {greek_path}')
            self.emit('Loading Greek model…')
            self.models['el'] = Model(str(greek_path))
        if mode in ('en', 'both'):
            if not (Path(english_path) / 'am' / 'final.mdl').is_file():
                raise FileNotFoundError(f'English model missing: {english_path}')
            self.emit('Loading English model…')
            self.models['en'] = Model(str(english_path))
        self.capacity = math.ceil((self.delay_s + 30) * self.rate)
        self.delay = round(self.delay_s * self.rate)
        self.audio = np.zeros(self.capacity, dtype=np.float32)
        self.marked = np.zeros(self.capacity, dtype=np.bool_)
        self.checked = {lang: np.full(self.capacity, -1, dtype=np.int64) for lang in self.models}
        self.lock = threading.Lock()
        self.incoming = queue.Queue(maxsize=100)
        self.stopping = threading.Event()
        self.state = {'written': 0, 'read': 0, 'dropped': 0, 'passed': 0, 'muted': 0, 'late': 0}
        for lang in self.models:
            self.state[lang + '_pos'] = 0
        self.feed = round(.1 * self.rate)
        self.audio_model = bool(audio_model)
        self.audio_model_dir = Path(audio_model_dir) if audio_model_dir else None
        self.audio_threshold = float(audio_threshold)
        self.audio_detector = None
        self.audio_last_accept = {}
        self.audio_window = round(AUDIO_WINDOW_SECONDS * self.rate)
        self.audio_hop = round(AUDIO_HOP_SECONDS * self.rate)
        if self.audio_model:
            self.load_audio_model()

    def load_audio_model(self):
        if not self.audio_model_dir or not (self.audio_model_dir / 'model.pt').is_file():
            raise FileNotFoundError('AI audio keyword model missing: models/keyword_v4/model.pt')
        self.emit('Loading AI audio keyword model…')
        from keyword_audio_detector import AudioKeywordDetector
        self.audio_detector = AudioKeywordDetector(
            self.audio_model_dir,
            threshold=self.audio_threshold,
        )
        threading.Thread(target=self.audio_scan, daemon=True).start()

    def audio_scan(self):
        try:
            while not self.stopping.is_set():
                with self.lock:
                    written = self.state['written']
                    if written < self.audio_window:
                        window = None
                    else:
                        positions = np.arange(written - self.audio_window, written) % self.capacity
                        window = self.audio[positions].copy()
                if window is None:
                    time.sleep(.05)
                    continue
                if self.rate != ASR_RATE:
                    divisor = math.gcd(self.rate, ASR_RATE)
                    window = resample_poly(
                        window,
                        ASR_RATE // divisor,
                        self.rate // divisor,
                    )
                if len(window) != 32000:
                    time.sleep(self.audio_hop / self.rate)
                    continue
                label, score = self.audio_detector.detect(window)
                if label:
                    with self.lock:
                        now = written / self.rate
                        last = self.audio_last_accept.get(label, -10.0)
                        if now - last >= 0.70:
                            self.audio_last_accept[label] = now
                            self.mark_audio(label, now)
                time.sleep(self.audio_hop / self.rate)
        except Exception as exc:
            self.emit(f'AI audio recognition error: {exc}')
            self.stop()

    def mark_audio(self, label, end_time):
        right = max(1, round(end_time * self.rate))
        left = max(0, right - round(AUDIO_BEEP_SECONDS * self.rate))
        with self.lock:
            played = self.state['read']
            if right <= played:
                self.state['late'] += 1
                self.emit(f'TOO LATE [audio]: {label}')
                return
            if left < played:
                left = played
            right = min(right, self.state['written'])
            if left >= right:
                return
            self.marked[np.arange(left, right) % self.capacity] = True
        self.emit(f'BEEP [audio]: {label}')

    def stop(self):
        self.stopping.set()

    def input_callback(self, indata, frames, timing, status):
        try:
            self.incoming.put_nowait(indata[:, 0].copy())
        except queue.Full:
            self.state['dropped'] += 1

    def capture(self):
        try:
            while not self.stopping.is_set():
                try:
                    block = self.incoming.get(timeout=.1)
                except queue.Empty:
                    continue
                with self.lock:
                    start = self.state['written']
                    ix = np.arange(start, start + len(block)) % self.capacity
                    self.audio[ix] = block
                    self.marked[ix] = False
                    for checked in self.checked.values():
                        checked[ix] = -1
                    self.state['written'] += len(block)
        except Exception as exc:
            self.emit(f'Capture error: {exc}')
            self.stop()

    def mark(self, lang, word, first, last):
        if normalize(word) not in self.words:
            return
        left = max(0, round((first - .12) * self.rate))
        right = max(left + 1, round((last + .16) * self.rate))
        with self.lock:
            played = self.state['read']
            if right <= played:
                self.state['late'] += 1
                self.emit(f'TOO LATE [{lang}]: {word}')
                return
            if left < played:
                self.state['late'] += 1
                self.emit(f'PARTIAL [{lang}]: {word}')
                left = played
            right = min(right, self.state['written'])
            if left >= right:
                return
            self.marked[np.arange(left, right) % self.capacity] = True
        self.emit(f'BEEP [{lang}]: {word}')

    def process_result(self, lang, payload, seen):
        for item in payload.get('result', []) or payload.get('partial_result', []):
            word = item.get('word', '')
            first, last = float(item.get('start', 0)), float(item.get('end', 0))
            key = (round(first, 2), round(last, 2), normalize(word))
            if word and (key not in seen or last > seen[key] + .04):
                seen[key] = last
                self.mark(lang, word, first, last)

    def recognize(self, lang, model):
        try:
            rec = KaldiRecognizer(model, ASR_RATE)
            rec.SetWords(True)
            rec.SetPartialWords(True)
            seen = {}
            while not self.stopping.is_set():
                with self.lock:
                    pos, written = self.state[lang + '_pos'], self.state['written']
                    if written - pos > self.capacity - self.rate:
                        self.emit(f'FATAL [{lang}]: recognizer fell beyond ring; stopping')
                        self.stop()
                        return
                    n = min(self.feed, written - pos)
                    chunk = self.audio[np.arange(pos, pos + n) % self.capacity].copy() if n >= self.feed else None
                if chunk is None:
                    time.sleep(.02)
                    continue
                pcm = np.clip(resample_poly(chunk, ASR_RATE, self.rate) * 32768, -32768, 32767).astype(np.int16).tobytes()
                accepted = rec.AcceptWaveform(pcm)
                self.process_result(lang, json.loads(rec.Result() if accepted else rec.PartialResult()), seen)
                if len(seen) > 100:
                    cutoff = pos / self.rate - 30
                    seen = {k: v for k, v in seen.items() if k[0] > cutoff}
                with self.lock:
                    ix = np.arange(pos, pos + n) % self.capacity
                    self.checked[lang][ix] = pos + n
                    self.state[lang + '_pos'] += n
        except Exception as exc:
            self.emit(f'Recognition error [{lang}]: {exc}')
            self.stop()

    def output_callback(self, outdata, frames, timing, status):
        outdata.fill(0)
        with self.lock:
            n = min(frames, max(0, self.state['written'] - self.delay - self.state['read']))
            if not n:
                return
            positions = np.arange(self.state['read'], self.state['read'] + n)
            ix = positions % self.capacity
            audio, beep = self.audio[ix].copy(), self.marked[ix].copy()
            pending = np.zeros(n, dtype=np.bool_)
            for checked in self.checked.values():
                pending |= checked[ix] <= positions
            if self.fail_closed:
                audio[pending] = 0
                self.state['muted'] += int(np.count_nonzero(pending))
            else:
                self.state['passed'] += int(np.count_nonzero(pending))
            if beep.any():
                tone = (self.volume * np.sin(2 * np.pi * 700 * positions / self.rate)).astype(np.float32)
                audio[beep] = tone[beep]
            outdata[:n, 0] = audio
            self.state['read'] += n

    def run(self):
        threading.Thread(target=self.capture, daemon=True).start()
        for lang, model in self.models.items():
            threading.Thread(target=self.recognize, args=(lang, model), daemon=True).start()
        self.emit(f"Running: mic #{self.input_id} → output #{self.output_id}; delay {self.delay_s:g}s; languages {', '.join(self.models)}; {'MUTE' if self.fail_closed else 'PASS'} unanalyzed audio")
        try:
            with sd.InputStream(device=self.input_id, channels=1, samplerate=self.rate, dtype='float32', callback=self.input_callback), sd.OutputStream(device=self.output_id, channels=1, samplerate=self.rate, dtype='float32', callback=self.output_callback):
                while not self.stopping.wait(3):
                    with self.lock:
                        written = self.state['written']
                        lag = {x: (written - self.state[x + '_pos']) / self.rate for x in self.models}
                        dropped, passed, muted, late = (self.state[k] for k in ('dropped', 'passed', 'muted', 'late'))
                        for k in ('dropped', 'passed', 'muted', 'late'):
                            self.state[k] = 0
                    lag_text = ' '.join(f'{x}={lag[x]:.1f}s' for x in lag)
                    self.emit(f'STATUS: lag {lag_text} dropped={dropped} late={late} unanalyzed passed={passed/self.rate:.1f}s muted={muted/self.rate:.1f}s')
        finally:
            self.stop()
            self.emit('Stopped')
