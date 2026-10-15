# ============================================================
#
#   I N T Z E V I D I S 7
#
#   Bad Word Beep — local OBS microphone censor
#   Created by Intzevidis7
#   GitHub: https://github.com/Intzevidis7
#
#   "Every beep is a tiny piece of performance art."
#
# ============================================================
import json
import queue
import re
import sys
import threading
import webbrowser
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

import sounddevice as sd
from censor_engine import Censor

ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
MODELS = ROOT / 'models'
CONFIG = ROOT / 'settings.json'
GREEK_MODEL = MODELS / 'vosk-model-el-gr-0.7'
ENGLISH_MODEL = MODELS / 'vosk-model-small-en-us-0.15'

BG, CARD, TEXT, MUTED = '#f4f7fb', '#ffffff', '#172033', '#667085'
ACCENT, DANGER, GREEN = '#635bff', '#b42318', '#087443'
MODES = {
    'Greek only — fastest for Greek streams': 'el',
    'English only — fastest for English streams': 'en',
    'Greek + English — mixed speech, higher CPU use': 'both',
}

class GUI:
    def __init__(self, root):
        self.root = root
        root.title('Bad Word Beep')
        try:
            root.iconbitmap(str(ROOT / 'app.ico'))
        except tk.TclError:
            pass
        root.geometry('1000x800')
        root.minsize(820, 650)
        root.configure(bg=BG)
        self.events = queue.Queue()
        self.worker = self.censor = None
        self.inputs, self.outputs, self.saved = {}, {}, {}
        self.mic, self.output = tk.StringVar(), tk.StringVar()
        self.mode_label = tk.StringVar(value=list(MODES)[2])
        self.delay, self.volume = tk.StringVar(value='6'), tk.StringVar(value='0.04')
        self.fail_closed = tk.BooleanVar(value=False)
        self.status, self.status_detail = tk.StringVar(value='Stopped'), tk.StringVar(value='Ready to configure')
        self.build_ui()
        self.load_settings()
        self.refresh_devices()
        root.after(150, self.poll)
        root.protocol('WM_DELETE_WINDOW', self.close)

    def build_ui(self):
        style = ttk.Style(self.root)
        try: style.theme_use('clam')
        except tk.TclError: pass
        style.configure('.', font=('Segoe UI', 10), foreground=TEXT)
        style.configure('App.TFrame', background=BG)
        style.configure('Card.TLabelframe', background=CARD, bordercolor='#d9e1ec')
        style.configure('Card.TLabelframe.Label', background=CARD, foreground=TEXT, font=('Segoe UI', 10, 'bold'))
        style.configure('Title.TLabel', background=BG, foreground=TEXT, font=('Segoe UI', 27, 'bold'))
        style.configure('Subtitle.TLabel', background=BG, foreground=MUTED, font=('Segoe UI', 10))
        style.configure('Hint.TLabel', background=BG, foreground=DANGER, font=('Segoe UI', 9))
        style.configure('Muted.TLabel', background=CARD, foreground=MUTED, font=('Segoe UI', 9))
        style.configure('Primary.TButton', background=ACCENT, foreground='white', padding=(16, 9), font=('Segoe UI', 10, 'bold'))
        style.map('Primary.TButton', background=[('active', '#5148e5'), ('disabled', '#b7b4d9')])
        style.configure('TEntry', padding=6); style.configure('TCombobox', padding=5); style.configure('TCheckbutton', background=CARD)
        outer = ttk.Frame(self.root, padding=28, style='App.TFrame'); outer.pack(fill='both', expand=True)
        header = ttk.Frame(outer, style='App.TFrame'); header.pack(fill='x', pady=(0, 18))
        ttk.Label(header, text='Bad Word Beep', style='Title.TLabel').pack(anchor='w')
        ttk.Label(
            header,
            text='Local Greek + English microphone censor for OBS',
            style='Subtitle.TLabel',
        ).pack(anchor='w', pady=(2, 0))
        ttk.Style(self.root).configure(
            'AuthorLink.TLabel',
            background=BG,
            foreground=ACCENT,
            font=('Segoe UI', 9, 'underline'),
        )

        github_label = ttk.Label(
            header,
            text='Created by Intzevidis7',
            style='AuthorLink.TLabel',
            cursor='hand2',
        )
        github_label.pack(anchor='w', pady=(4, 0))
        github_label.bind(
            '<Button-1>',
            lambda event: webbrowser.open_new('https://github.com/Intzevidis7'),
        )
        ttk.Label(header, text='Experimental protection — always test a local recording before streaming.', style='Hint.TLabel').pack(anchor='w', pady=(8, 0))
        route = ttk.LabelFrame(outer, text='  1  Audio routing  ', padding=18, style='Card.TLabelframe'); route.pack(fill='x', pady=(0, 14)); route.columnconfigure(1, weight=1)
        ttk.Label(route, text='Microphone').grid(row=0, column=0, sticky='w', pady=6)
        self.mic_box = ttk.Combobox(route, textvariable=self.mic, state='readonly'); self.mic_box.grid(row=0, column=1, sticky='ew', padx=16, pady=6)
        ttk.Label(route, text='Playback output').grid(row=1, column=0, sticky='w', pady=6)
        self.out_box = ttk.Combobox(route, textvariable=self.output, state='readonly'); self.out_box.grid(row=1, column=1, sticky='ew', padx=16, pady=6)
        ttk.Button(route, text='Refresh devices', command=self.refresh_devices).grid(row=0, column=2, rowspan=2, padx=(6,0))
        ttk.Label(route, text='App → CABLE Input  •  OBS Audio Input Capture → CABLE Output  •  mute the raw microphone', style='Muted.TLabel').grid(row=2, column=0, columnspan=3, sticky='w', pady=(10,0))
        settings = ttk.LabelFrame(outer, text='  2  Recognition and censor settings  ', padding=18, style='Card.TLabelframe'); settings.pack(fill='x', pady=(0,14)); settings.columnconfigure(1, weight=1)
        ttk.Label(settings, text='Recognition mode').grid(row=0, column=0, sticky='w', pady=5)
        self.mode_box = ttk.Combobox(settings, textvariable=self.mode_label, values=list(MODES), state='readonly'); self.mode_box.grid(row=0, column=1, columnspan=5, sticky='ew', padx=(16,0), pady=5)
        ttk.Label(settings, text='Delay').grid(row=1, column=0, sticky='w', pady=(12,0)); ttk.Entry(settings, textvariable=self.delay, width=9).grid(row=1,column=1,sticky='w',padx=(16,6),pady=(12,0)); ttk.Label(settings,text='seconds',style='Muted.TLabel').grid(row=1,column=2,sticky='w',pady=(12,0))
        ttk.Label(settings, text='Beep volume').grid(row=1,column=3,sticky='w',padx=(26,0),pady=(12,0)); ttk.Entry(settings,textvariable=self.volume,width=9).grid(row=1,column=4,sticky='w',padx=(10,6),pady=(12,0)); ttk.Label(settings,text='0–0.3',style='Muted.TLabel').grid(row=1,column=5,sticky='w',pady=(12,0))
        ttk.Checkbutton(settings,text='Mute unanalyzed audio (experimental gaps)',variable=self.fail_closed).grid(row=2,column=0,columnspan=6,sticky='w',pady=(14,0))
        ttk.Label(settings,text='Greek + English loads two offline recognizers and may use 1.5 GB+ RAM. Greek-only or English-only mode can reduce resource use.',style='Muted.TLabel').grid(row=3,column=0,columnspan=6,sticky='w',pady=(10,0))
        actions = ttk.Frame(outer, style='App.TFrame'); actions.pack(fill='x', pady=(0,14))
        self.start_btn=ttk.Button(actions,text='Start censor',command=self.start,style='Primary.TButton'); self.start_btn.pack(side='left')
        self.stop_btn=ttk.Button(actions,text='Stop',command=self.stop,state='disabled'); self.stop_btn.pack(side='left',padx=10)
        ttk.Button(actions,text='Open active word list',command=self.open_words).pack(side='left')
        status=ttk.Frame(actions,style='App.TFrame'); status.pack(side='right')
        ttk.Label(status,textvariable=self.status,foreground=GREEN,font=('Segoe UI',11,'bold')).pack(anchor='e'); ttk.Label(status,textvariable=self.status_detail,style='Subtitle.TLabel').pack(anchor='e')
        h=ttk.Frame(outer,style='App.TFrame'); h.pack(fill='x'); ttk.Label(h,text='Activity log',font=('Segoe UI',11,'bold'),background=BG,foreground=TEXT).pack(side='left'); ttk.Label(h,text='  HEARD  •  BEEP  •  TOO LATE  •  lag',style='Subtitle.TLabel').pack(side='left')
        self.log=scrolledtext.ScrolledText(outer,state='disabled',wrap='word',height=14,bg='#101828',fg='#d0d5dd',insertbackground='white',relief='flat',borderwidth=0,padx=12,pady=10,font=('Consolas',9)); self.log.pack(fill='both',expand=True,pady=(7,0))
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⣠⣠⣶⣶⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣾⢷⣟⡿⠿⣷⣤⣄⠀⠀⠀⠀⠀⠀⠀
#           ⠀⢀⣾⡟⢛⣽⣶⠿⠷⣤⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡼⣿⠁⠈⣿⣿⠲⣿⢨⣿⠤⢤⠀⠀⠀⠀⠀
#           ⠀⠸⣏⡾⠉⣽⡀⣦⡀⠀⠈⠙⠶⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢸⠁⡟⠀⠀⠘⢿⠠⡏⣼⠃⠀⣸⡤⣤⠀⠀⠀
#           ⢀⣴⠿⣧⡄⠙⠁⢸⡇⠀⠀⠀⠀⠈⠻⢶⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡞⠀⢇⡀⠀⠀⠀⠀⢰⠏⠀⣰⠋⢠⡿⣶⡄⠀
#           ⠸⠟⢻⡇⠹⣦⣠⡿⠃⠀⠀⠀⠀⠀⣄⠀⠙⢷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⡴⠷⠚⠋⠀⠀⠀⡤⣾⡟⠀⠘⠁⢀⣿⣧⡟⢧⠀
#           ⠀⠀⠸⣇⡀⣸⡏⠀⠀⠀⠀⠀⠀⠀⠘⢷⢿⣦⣙⢷⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⡴⠚⠉⠀⠀⠀⠀⠀⠀⠀⠀⠛⢷⠀⠀⣴⣶⡿⠏⢡⣿⣷
#           ⠀⠀⠀⠈⠉⣹⠁⠀⡄⠀⡀⠀⡀⠀⠰⡈⠋⢿⢿⡷⠽⣦⠀⠀⠀⠀⠀⠀⠀⣠⠾⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠷⠤⡼⡁⣀⣴⣧⣀⡏
#           ⠀⠀⠀⠀⢀⡿⠀⢰⢻⡀⣷⣠⣷⣤⠀⠹⡄⠀⠀⠁⢠⣬⣷⠶⠒⠒⠒⣲⡟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠛⠻⣽⣷⣿⠹⣤
#           ⠀⠀⠀⠀⢸⡇⠀⠘⡎⣧⠛⣇⠹⣿⣀⣠⣤⠴⠚⠉⠀⠀⠀⣀⡤⠔⠈⠉⠙⠒⠲⢤⣤⣀⠀⠀⠀⠀⠀⠀⣸⠀⠀⠀⠀⢶⡄⠀⠀⠀⠉⣹⣷⠏
#           ⠀⠀⠀⠀⣿⡇⡀⠀⣷⣿⠀⡼⠚⠻⠀⠀⠀⠀⠀⠀⠀⠀⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠓⠶⢤⣀⠰⠚⣽⠄⠀⣠⣾⡥⠀⠀⠀⠘⡏⠁⠀
#           ⠀⠀⠀⠀⢿⡇⠉⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⠀⠀⠀⠈⠙⠆⣦⡀⠘⠋⠉⠀⠀⠀⠀⢰⠇⠀⠀
#           ⠀⠀⠀⠀⢸⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠳⠦⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠀⠀⠀⣼⣀⣀⣀⣀⣀⣠⣿⣄⠀⢀⣰⣌⣻⠆⣀⡏⠀⠀⠀
#           ⠀⠀⠀⠀⠀⢿⡔⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣦⣀⡀⠀⠀⠀⠀⠀⠀⢴⡟⠀⠀⢴⡇⠀⣀⣀⣠⠤⠤⣴⠟⠀⠀⢡⠽⠁⣠⡟⠁⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠘⣷⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⣻⣄⡀⠀⠀⠠⡶⣫⠀⢀⡤⠋⠀⣈⣭⡥⠤⠖⠋⠹⠦⣤⣤⣀⣠⡿⠋⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠘⢿⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠙⠚⠳⢤⣆⠉⠽⠋⠀⢀⣠⠴⠚⠉⠉⠀⠀⠀⠀⠀⠀⠉⢙⡿⠋⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠻⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠉⠻⣦⣤⠖⠋⠁⠀⠀⠀⠀⠀⠀⠀⢠⣄⣠⡴⣺⡇⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⢷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣀⠀⠀⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣨⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢻⣦⡀⠀⠀⢀⣀⣀⣠⡤⠉⠉⠉⠉⠀⠀⠀⢷⠀⠀⠀⠀⠀⠀⠀⠘⣻⡭⢥⣴⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠹⣿⡄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣼⡆⢀⡀⠀⠀⠀⠀⠀⠀⣴⡾⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢿⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣶⣟⣥⣳⣿⣷⣴⣖⣀⣐⣾⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿⣆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢛⣦⡽⣿⣻⣭⡽⠿⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠻⣷⡀⠀⠀⠀⠀⠀⠀⠀⣠⣶⠛⢛⣫⠟⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠛⠲⢶⡤⢤⣦⠤⠾⠋⠻⣟⣽⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡸⢀⡜⠁⠀⠀⠀⠀⠸⣾⡆⠀⠀⠀⠀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⣇⡿⠁⠀⠀⠀⠀⠀⠀⢻⣹⡀⢠⣴⡾⠛⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⡀⣀⣠⣿⢹⡀⠀⠀⠀⢀⣀⣀⣠⣤⣷⣙⡽⠋⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣿⣽⠯⠿⢷⣛⣫⡤⠬⢭⣷⡄⠀⢿⣯⠤⠶⠶⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
#           ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠿⠿⠛⠋⠉⠀⠀⠀⠀⠀⠀⠀⠀⠈⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
    def active_lists(self):
        mode=MODES[self.mode_label.get()]
        if mode=='el': return [ROOT/'bad_words_el.txt', ROOT/'bad_words_greeklish.txt']
        if mode=='en': return [ROOT/'bad_words_en.txt']
        return [ROOT/'bad_words_el.txt', ROOT/'bad_words_en.txt', ROOT/'bad_words_greeklish.txt']

    def append(self,text):
        self.log.configure(state='normal'); self.log.insert('end',str(text).rstrip()+'\n')
        if int(self.log.index('end-1c').split('.')[0])>1500: self.log.delete('1.0','301.0')
        self.log.see('end'); self.log.configure(state='disabled')

    def load_settings(self):
        try:
            self.saved=json.loads(CONFIG.read_text(encoding='utf-8'))
            for name,var in (('delay',self.delay),('volume',self.volume),('mode_label',self.mode_label)):
                if name in self.saved: var.set(str(self.saved[name]))
            if self.mode_label.get() not in MODES: self.mode_label.set(list(MODES)[2])
            self.fail_closed.set(bool(self.saved.get('fail_closed',False)))
        except (OSError,ValueError): pass

    def refresh_devices(self):
        old_mic=self.mic.get() or self.saved.get('mic',''); old_out=self.output.get() or self.saved.get('output','')
        try: devices,apis=sd.query_devices(),sd.query_hostapis()
        except Exception as exc: messagebox.showerror('Audio devices',str(exc)); return
        self.inputs,self.outputs={},{}
        for i,d in enumerate(devices):
            label=f"{i} | {d['name']} [{apis[d['hostapi']]['name']}] | {round(d['default_samplerate'])}Hz"
            if d['max_input_channels']: self.inputs[label]=i
            if d['max_output_channels']: self.outputs[label]=i
        self.mic_box['values'],self.out_box['values']=list(self.inputs),list(self.outputs)
        self.mic.set(old_mic if old_mic in self.inputs else next(iter(self.inputs),''))
        cable=next((v for v in self.outputs if re.search(r'\bCABLE Input\b',v,re.I)), '')
        self.output.set(old_out if old_out in self.outputs else cable or next(iter(self.outputs),''))

    def start(self):
        if self.worker and self.worker.is_alive(): return
        mode=MODES[self.mode_label.get()]
        needed=[]
        if mode in ('el','both'): needed.append(('Greek',GREEK_MODEL))
        if mode in ('en','both'): needed.append(('English',ENGLISH_MODEL))
        for name,path in needed:
            if not (path/'am'/'final.mdl').is_file(): messagebox.showerror(f'{name} model missing',f'Expected model at:\n{path}\n\nRun BadWordBeep-Models.exe first.'); return
        lists=self.active_lists(); missing=[p.name for p in lists if not p.is_file()]
        if missing: messagebox.showerror('Word list missing','Missing:\n'+'\n'.join(missing)); return
        try:
            inp,out=self.inputs[self.mic.get()],self.outputs[self.output.get()]; delay,volume=float(self.delay.get()),float(self.volume.get())
            if not (2<=delay<=120 and 0<=volume<=.3): raise ValueError('Delay must be 2–120 seconds, beep volume 0–0.3')
            rate=round(sd.query_devices(inp)['default_samplerate'])
            if rate!=round(sd.query_devices(out)['default_samplerate']): raise ValueError('Devices have different default sample rates; choose another entry')
            sd.check_input_settings(device=inp,channels=1,samplerate=rate); sd.check_output_settings(device=out,channels=1,samplerate=rate)
        except Exception as exc: messagebox.showerror('Check settings',str(exc)); return
        if 'cable input' not in self.output.get().lower() and not messagebox.askyesno('Check cable','You did not choose CABLE Input. Continue?'): return
        try: CONFIG.write_text(json.dumps({'mic':self.mic.get(),'output':self.output.get(),'delay':delay,'volume':volume,'mode_label':self.mode_label.get(),'fail_closed':self.fail_closed.get()},indent=2),encoding='utf-8')
        except OSError as exc: self.append(f'Could not save settings: {exc}')
        self.start_btn.configure(state='disabled'); self.stop_btn.configure(state='normal'); self.status.set('Starting…'); self.status_detail.set(f'Loading {self.mode_label.get().split(" — ")[0]} model(s)')
        def run():
            try:
                self.censor=Censor(inp,out,delay,volume,mode,GREEK_MODEL,ENGLISH_MODEL,lists,fail_closed=self.fail_closed.get(),events=lambda x:self.events.put(('log',x)))
                self.censor.run()
            except Exception as exc: self.events.put(('log',f'ERROR: {exc}'))
            finally: self.events.put(('done',None))
        self.worker=threading.Thread(target=run,daemon=True); self.worker.start()

    def poll(self):
        try:
            while True:
                kind,text=self.events.get_nowait()
                if kind=='log':
                    self.append(text)
                    if str(text).startswith('Running:'): self.status.set('Running'); self.status_detail.set('Microphone is being processed and delayed')
                elif kind=='done': self.censor=self.worker=None; self.status.set('Stopped'); self.status_detail.set('Ready to configure'); self.start_btn.configure(state='normal'); self.stop_btn.configure(state='disabled')
        except queue.Empty: pass
        self.root.after(150,self.poll)

    def stop(self):
        if self.censor: self.censor.stop()
        self.status.set('Stopping…'); self.status_detail.set('Releasing audio devices')

    def open_words(self):
        files=self.active_lists()
        if sys.platform=='win32':
            import os
            for path in files:
                if path.exists(): os.startfile(str(path))
        else: messagebox.showinfo('Active word lists','\n'.join(map(str,files)))

    def close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno('Stop censor?','Closing this window stops the censor. Close?'): return
            self.stop(); self.worker.join(timeout=5)
            if self.worker.is_alive(): messagebox.showwarning('Still stopping','Wait for the audio device to release, then close again.'); return
        self.root.destroy()

if __name__=='__main__':
    root=tk.Tk(); GUI(root); root.mainloop()
