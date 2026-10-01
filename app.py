"""Local GUI entry point; build this file with PyInstaller for Windows."""
import json
import queue
import re
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

import sounddevice as sd
from censor_engine import Censor

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
MODELS = ROOT / 'models'
WORDS = ROOT / 'bad_words.txt'
CONFIG = ROOT / 'settings.json'


class GUI:
    def __init__(self, root):
        self.root = root
        root.title('Bad Word Beep — Greek + English')
        root.geometry('960x740')
        root.minsize(770, 580)
        self.events = queue.Queue()
        self.worker = None
        self.censor = None
        self.inputs = {}
        self.outputs = {}
        self.saved = {}
        self.mic = tk.StringVar()
        self.output = tk.StringVar()
        self.delay = tk.StringVar(value='6')
        self.volume = tk.StringVar(value='0.04')
        self.fail_closed = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value='Stopped')
        self.build_ui()
        self.load_settings()
        self.refresh_devices()
        root.after(150, self.poll)
        root.protocol('WM_DELETE_WINDOW', self.close)

    def build_ui(self):
        f = ttk.Frame(self.root, padding=16)
        f.pack(fill='both', expand=True)
        ttk.Label(f, text='Bad Word Beep', font=('Segoe UI', 21, 'bold')).pack(anchor='w')
        ttk.Label(f, text='Local Greek + English microphone censor for OBS • Vosk').pack(anchor='w')
        ttk.Label(f, text='Experimental. Some words may pass through or innocent speech may beep. Test a local recording.',
                  foreground='#aa311c').pack(anchor='w', pady=(5, 12))
        route = ttk.LabelFrame(f, text='Audio routing', padding=12)
        route.pack(fill='x')
        route.columnconfigure(1, weight=1)
        ttk.Label(route, text='Microphone').grid(row=0, column=0, sticky='w')
        self.mic_box = ttk.Combobox(route, textvariable=self.mic, state='readonly')
        self.mic_box.grid(row=0, column=1, sticky='ew', padx=10, pady=5)
        ttk.Label(route, text='Playback output').grid(row=1, column=0, sticky='w')
        self.out_box = ttk.Combobox(route, textvariable=self.output, state='readonly')
        self.out_box.grid(row=1, column=1, sticky='ew', padx=10, pady=5)
        ttk.Button(route, text='Refresh devices', command=self.refresh_devices).grid(row=0, column=2, rowspan=2)
        ttk.Label(route, text='Here: CABLE Input. In OBS: Audio Input Capture → CABLE Output; mute original microphone.').grid(
            row=2, column=0, columnspan=3, sticky='w', pady=6)
        opts = ttk.Frame(f)
        opts.pack(fill='x', pady=12)
        ttk.Label(opts, text='Delay (seconds)').pack(side='left')
        ttk.Entry(opts, textvariable=self.delay, width=8).pack(side='left', padx=(8, 22))
        ttk.Label(opts, text='Beep volume (0–0.3)').pack(side='left')
        ttk.Entry(opts, textvariable=self.volume, width=8).pack(side='left', padx=(8, 22))
        ttk.Checkbutton(opts, text='Mute unanalyzed audio (experimental gaps)', variable=self.fail_closed).pack(side='left')
        actions = ttk.Frame(f)
        actions.pack(fill='x', pady=(0, 12))
        self.start_btn = ttk.Button(actions, text='Start censor', command=self.start)
        self.start_btn.pack(side='left')
        self.stop_btn = ttk.Button(actions, text='Stop', command=self.stop, state='disabled')
        self.stop_btn.pack(side='left', padx=9)
        ttk.Button(actions, text='Open word list', command=self.open_words).pack(side='left')
        ttk.Label(actions, textvariable=self.status).pack(side='right')
        ttk.Label(f, text='Log (HEARD, BEEP, TOO LATE, lag and unanalyzed duration)').pack(anchor='w')
        self.log = scrolledtext.ScrolledText(f, state='disabled', wrap='word')
        self.log.pack(fill='both', expand=True, pady=(5, 0))

    def append(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', str(text).rstrip() + '\n')
        if int(self.log.index('end-1c').split('.')[0]) > 1500:
            self.log.delete('1.0', '301.0')
        self.log.see('end')
        self.log.configure(state='disabled')

    def load_settings(self):
        try:
            self.saved = json.loads(CONFIG.read_text(encoding='utf-8'))
            for name, var in (('delay', self.delay), ('volume', self.volume)):
                if name in self.saved:
                    var.set(str(self.saved[name]))
            self.fail_closed.set(bool(self.saved.get('fail_closed', False)))
        except (OSError, ValueError):
            pass

    def refresh_devices(self):
        prev_mic = self.mic.get() or self.saved.get('mic', '')
        prev_out = self.output.get() or self.saved.get('output', '')
        try:
            devices = sd.query_devices()
            apis = sd.query_hostapis()
        except Exception as exc:
            messagebox.showerror('Audio devices', str(exc))
            return
        self.inputs, self.outputs = {}, {}
        for i, d in enumerate(devices):
            label = f"{i} | {d['name']} [{apis[d['hostapi']]['name']}] | {round(d['default_samplerate'])}Hz"
            if d['max_input_channels']:
                self.inputs[label] = i
            if d['max_output_channels']:
                self.outputs[label] = i
        self.mic_box['values'] = list(self.inputs)
        self.out_box['values'] = list(self.outputs)
        self.mic.set(prev_mic if prev_mic in self.inputs else next(iter(self.inputs), ''))
        cable = next((v for v in self.outputs if re.search(r'\bCABLE Input\b', v, re.I)), '')
        self.output.set(prev_out if prev_out in self.outputs else cable or next(iter(self.outputs), ''))

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        for name, path in (('Greek', MODELS/'vosk-model-el-gr-0.7'),
                           ('English', MODELS/'vosk-model-small-en-us-0.15')):
            if not (path/'am'/'final.mdl').is_file():
                messagebox.showerror(f'{name} model missing',
                                     f'Expected model at:\n{path}\n\nUse the Setup EXE or README instructions.')
                return
        if not WORDS.is_file():
            messagebox.showerror('Word list missing', f'Expected {WORDS}')
            return
        try:
            inp, out = self.inputs[self.mic.get()], self.outputs[self.output.get()]
            delay, volume = float(self.delay.get()), float(self.volume.get())
            if not (2 <= delay <= 120 and 0 <= volume <= .3):
                raise ValueError('Delay must be 2–120 seconds, beep volume 0–0.3')
            rate = round(sd.query_devices(inp)['default_samplerate'])
            if rate != round(sd.query_devices(out)['default_samplerate']):
                raise ValueError('Devices have different default sample rates; choose another entry')
            sd.check_input_settings(device=inp, channels=1, samplerate=rate)
            sd.check_output_settings(device=out, channels=1, samplerate=rate)
        except Exception as exc:
            messagebox.showerror('Check settings', str(exc))
            return
        if 'cable input' not in self.output.get().lower():
            if not messagebox.askyesno('Check cable', 'You did not choose CABLE Input. Continue?'):
                return
        try:
            CONFIG.write_text(json.dumps({'mic': self.mic.get(), 'output': self.output.get(),
                                          'delay': delay, 'volume': volume,
                                          'fail_closed': self.fail_closed.get()}, indent=2), encoding='utf-8')
        except OSError as exc:
            self.append(f'Could not save settings: {exc}')
        self.start_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self.status.set('Loading models…')
        def run():
            try:
                self.censor = Censor(inp, out, delay, volume,
                                     MODELS/'vosk-model-el-gr-0.7',
                                     MODELS/'vosk-model-small-en-us-0.15', WORDS,
                                     fail_closed=self.fail_closed.get(),
                                     events=lambda text: self.events.put(('log', text)))
                self.censor.run()
            except Exception as exc:
                self.events.put(('log', f'ERROR: {exc}'))
            finally:
                self.events.put(('done', None))
        self.worker = threading.Thread(target=run, daemon=True)
        self.worker.start()

    def poll(self):
        try:
            while True:
                kind, text = self.events.get_nowait()
                if kind == 'log':
                    self.append(text)
                    if str(text).startswith('Running:'):
                        self.status.set('Running (delayed mic)')
                elif kind == 'done':
                    self.censor = None
                    self.worker = None
                    self.status.set('Stopped')
                    self.start_btn.configure(state='normal')
                    self.stop_btn.configure(state='disabled')
        except queue.Empty:
            pass
        self.root.after(150, self.poll)

    def stop(self):
        if self.censor:
            self.censor.stop()
            self.status.set('Stopping…')

    def open_words(self):
        if not WORDS.exists():
            messagebox.showerror('Missing word list', str(WORDS))
        elif sys.platform == 'win32':
            import os
            os.startfile(str(WORDS))
        else:
            messagebox.showinfo('Word list', str(WORDS))

    def close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno('Stop censor?', 'Closing this window stops the censor. Close?'):
                return
            self.stop()
            self.worker.join(timeout=5)
            if self.worker.is_alive():
                messagebox.showwarning('Still stopping', 'Wait for the audio device to release, then close again.')
                return
        self.root.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    GUI(root)
    root.mainloop()
