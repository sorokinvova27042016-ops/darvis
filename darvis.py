#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Darvis Beta Test v9.0
Исправлено: сказки, аудио, название окна.
"""

import os, sys, re, io, time, math, wave, queue, random, asyncio
import hashlib, tempfile, threading, subprocess, uuid, traceback
import webbrowser, urllib.parse, ctypes, base64
from datetime import datetime

MISSING = []
try:
    import speech_recognition as sr
except ImportError:
    MISSING.append("SpeechRecognition")
try:
    import sounddevice as sd
    import numpy as np
except ImportError:
    MISSING.append("sounddevice numpy")
try:
    import edge_tts
except ImportError:
    edge_tts = None
    MISSING.append("edge-tts")
try:
    from fuzzywuzzy import fuzz as _fz
except ImportError:
    try:
        from rapidfuzz import fuzz as _rf
        class _W:
            @staticmethod
            def partial_ratio(a, b):
                r = _rf.partial_ratio(a, b)
                return r if r > 1 else r * 100
        _fz = _W()
    except ImportError:
        _fz = None
        MISSING.append("fuzzywuzzy")

if MISSING:
    msg = "Не хватает библиотек:\n" + "\n".join("  ✗ " + m for m in MISSING)
    msg += "\n\nУстанови:\n  pip install edge-tts SpeechRecognition sounddevice numpy fuzzywuzzy"
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk(); r.withdraw()
        messagebox.showerror("Darvis", msg); r.destroy()
    except Exception:
        print(msg)
    sys.exit(1)

import tkinter as tk
from tkinter import ttk, messagebox

# ══════════════════════════════════════════════════════════════
#  АВАТАР
# ══════════════════════════════════════════════════════════════
AVATAR_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

def get_avatar_image(size=52):
    try:
        from PIL import Image, ImageTk
        data = base64.b64decode(AVATAR_B64)
        img = Image.open(io.BytesIO(data)).resize((size, size))
        return ImageTk.PhotoImage(img)
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════
#  КОНСТАНТЫ
# ══════════════════════════════════════════════════════════════

VOICES = {
    "Светлана (женский)":        "ru-RU-SvetlanaNeural",
    "Дмитрий (мужской)":         "ru-RU-DmitryNeural",
    "Andrew (US, естественный)": "en-US-AndrewNeural",
    "Emma (Multilingual)":        "en-US-EmmaMultilingualNeural",
    "Guy (US)":                   "en-US-GuyNeural",
    "Aria (US)":                  "en-US-AriaNeural",
    "Ryan (UK)":                  "en-GB-RyanNeural",
    "Sonia (UK)":                 "en-GB-SoniaNeural",
}

WAKE_WORDS = ["привет дарвис", "привет дервис", "эй дарвис", "дарвис", "darvis"]
WAKE_THRESHOLD = 75

SILENCE_AFTER_SPEECH = 1.0
MAX_DURATION = 8.0
START_THRESHOLD = 500
MIN_SPEECH_LEVEL = 100

APPS = {
    "кс2": "steam://rungameid/730", "cs2": "steam://rungameid/730",
    "кс го": "steam://rungameid/730",
    "дота": "steam://rungameid/570", "dota": "steam://rungameid/570",
    "стим": "steam://open/", "steam": "steam://open/",
    "дискорд": "https://discord.com/app",
    "телеграм": "https://web.telegram.org",
    "вк": "https://vk.com", "vk": "https://vk.com",
    "ютуб": "https://youtube.com", "youtube": "https://youtube.com",
    "твич": "https://twitch.tv",
    "браузер": "https://google.com", "гугл": "https://google.com",
    "яндекс": "https://yandex.ru",
    "блокнот": "notepad.exe", "калькулятор": "calc.exe",
    "проводник": "explorer.exe", "терминал": "cmd.exe",
    "паинт": "mspaint.exe", "диспетчер": "taskmgr.exe",
    "настройки": "ms-settings:",
    "ворд": "winword.exe", "эксель": "excel.exe",
    "notepad++": "notepad++.exe",
}

PROC_MAP = {
    "кс2": "cs2.exe", "cs2": "cs2.exe", "кс го": "cs2.exe",
    "дота": "dota2.exe", "dota": "dota2.exe",
    "стим": "steam.exe", "steam": "steam.exe",
    "дискорд": "Discord.exe",
    "телеграм": "Telegram.exe",
    "хром": "chrome.exe", "chrome": "chrome.exe",
    "фаерфокс": "firefox.exe", "firefox": "firefox.exe",
    "эдж": "msedge.exe", "edge": "msedge.exe",
    "опера": "opera.exe", "opera": "opera.exe",
    "блокнот": "notepad.exe", "калькулятор": "calc.exe",
    "паинт": "mspaint.exe",
    "ворд": "WINWORD.EXE", "эксель": "EXCEL.EXE",
    "зум": "Zoom.exe", "скайп": "Skype.exe",
    "спотифай": "Spotify.exe", "обс": "obs64.exe",
}

SITE_SEARCH = {
    "ютуб":    "https://www.youtube.com/results?search_query={}",
    "youtube": "https://www.youtube.com/results?search_query={}",
    "гугл":    "https://www.google.com/search?q={}",
    "google":  "https://www.google.com/search?q={}",
    "яндекс":  "https://yandex.ru/search/?text={}",
    "вк":      "https://vk.com/search?c[q]={}",
    "твич":    "https://www.twitch.tv/search?term={}",
}

RULES = {
    ("привет", "хай", "здравствуй", "салют"): ["Привет! Чем помочь?", "Здравствуй!"],
    ("как дела", "как ты"): ["Отлично! У тебя как?", "Всё хорошо."],
    ("кто ты", "как тебя зовут", "твоё имя"): ["Я Дарвис Beta Test."],
    ("что умеешь", "что можешь", "помощь", "help"): [
        "Умею: сказки, музыку, код Python и Java, открывать и закрывать "
        "приложения, искать в интернете, считать.",
    ],
    ("люблю тебя", "молодец"): ["Спасибо!"],
    ("пока", "до свидания"): ["Пока! До встречи."],
    ("спасибо", "благодарю"): ["Пожалуйста!"],
    ("смысл жизни",): ["42."],
    ("устал", "нет сил", "грустно"): ["Отдохни. Всё будет хорошо."],
    ("python", "питон"): ["Python — язык для веба, данных, ИИ и автоматизации."],
    ("c++",): ["C++ — мощный язык для систем и игр."],
    ("c#",): ["C# — язык от Microsoft: Windows, Unity, веб."],
    ("java", "джава"): ["Java — объектно-ориентированный, работает везде. Android, enterprise."],
    ("javascript", "js"): ["JavaScript — язык для веба и Node.js."],
}

MONTHS_RU = ["января","февраля","марта","апреля","мая","июня",
             "июля","августа","сентября","октября","ноября","декабря"]

RU_NUMS = {"ноль":0,"один":1,"одна":1,"два":2,"две":2,"три":3,"четыре":4,
           "пять":5,"шесть":6,"семь":7,"восемь":8,"девять":9,"десять":10,
           "двадцать":20,"тридцать":30,"сорок":40,"пятьдесят":50,"сто":100}

T = {"bg":"#0f1115","panel":"#161a22","panel2":"#1d222c","card":"#1a1f29",
     "text":"#e1e8f0","muted":"#697786","accent":"#2d96eb",
     "green":"#41cd7d","red":"#eb4b55","yellow":"#ebbe41","user":"#7dd3fc"}

# ══════════════════════════════════════════════════════════════
#  СКАЗКИ (расширенный набор)
# ══════════════════════════════════════════════════════════════

FAIRY_TALES = {
    "колобок": (
        "Жили-были старик со старухой. Испекла старуха колобок — румяный, круглый. "
        "Положила его на окошко остудить. А колобок спрыгнул с окна и покатился по дорожке. "
        "Катится колобок, а навстречу ему заяц: «Колобок, колобок, я тебя съем!» "
        "А колобок отвечает: «Не ешь меня, я тебе песенку спою: я колобок, колобок, "
        "по амбару метён, по сусекам скребён, на сметане мешён, в печку сажён, "
        "на окошке стужён. Я от дедушки ушёл, я от бабушки ушёл, от тебя, зайца, "
        "и подавно уйду!» И покатился дальше. Повстречал волка, медведя, а потом лисицу. "
        "Лиса была хитрая — попросила сесть ей на нос и ещё раз спеть. "
        "Колобок прыгнул лисе на нос, а лиса его — ам! И съела."
    ),
    "курочка ряба": (
        "Жили-были дед да баба. Была у них курочка Ряба. Снесла курочка яичко, "
        "да не простое, а золотое. Дед бил-бил — не разбил. Баба била-била — не разбила. "
        "Мышка бежала, хвостиком махнула — яичко упало и разбилось. "
        "Дед плачет, баба плачет, а курочка кудахчет: «Не плачь, дед, не плачь, баба. "
        "Я снесу вам яичко не золотое, а простое!»"
    ),
    "репка": (
        "Посадил дед репку. Выросла репка большая-пребольшая. "
        "Стал дед репку тянуть. Тянет-потянет — вытянуть не может. "
        "Позвал дед бабку. Бабка за дедку, дедка за репку — тянут-потянут, вытянуть не могут. "
        "Позвала бабка внучку. Внучка за бабку, бабка за дедку — тянут-потянут, вытянуть не могут. "
        "Позвала внучка Жучку. Жучка за внучку — тянут-потянут, вытянуть не могут. "
        "Позвала Жучка кошку. Кошка за Жучку — тянут-потянут, вытянуть не могут. "
        "Позвала кошка мышку. Мышка за кошку, кошка за Жучку, Жучка за внучку, "
        "внучка за бабку, бабка за дедку, дедка за репку — тянут-потянут, и вытянули репку!"
    ),
    "теремок": (
        "Стоит в поле теремок. Бежит мимо мышка-норушка. Увидела теремок, остановилась и спрашивает: "
        "«Терем-теремок! Кто в тереме живёт?» Никто не отзывается. "
        "Вошла мышка в теремок и стала в нём жить. Прискакала лягушка-квакушка, "
        "потом зайчик-побегайчик, лисичка-сестричка, волчок-серый бочок. "
        "Пришёл медведь косолапый и полез на теремок. Затрещал теремок, упал набок и развалился. "
        "Еле-еле успели звери выскочить. Стали они новый теремок строить — лучше прежнего."
    ),
    "три медведя": (
        "Одна девочка ушла из дома в лес и заблудилась. Вышла она на полянку, "
        "а там стоит избушка. В избушке жили три медведя. Девочка поела из каждой чашки, "
        "посидела на каждом стуле, полежала на каждой кровати. Заснула на самой маленькой. "
        "Пришли медведи и увидели её. Девочка проснулась, испугалась и убежала."
    ),
    "гуси-лебеди": (
        "Жили-были мужик да баба, и были у них дочка и маленький сыночек. "
        "Ушли родители на работу, а дочке наказали следить за братцем. "
        "Но девочка заигралась и не заметила, как гуси-лебеди унесли мальчика к Бабе-Яге. "
        "Побежала девочка искать братца. Помогли ей печка, яблонька и молочная речка. "
        "Нашла она братца у Бабы-Яги, схватила и побежала домой. Гуси-лебеди гнались, "
        "но не догнали. Вернулись дети домой, а тут и родители пришли."
    ),
}

# ══════════════════════════════════════════════════════════════
#  ШАБЛОНЫ КОДА
# ══════════════════════════════════════════════════════════════

CODE_TEMPLATES = {
    "python": {
        "hello": 'print("Привет, мир!")\nname = input("Как тебя зовут? ")\nprint(f"Привет, {name}!")',
        "calc": 'def calc(a, b, op):\n    if op == "+": return a + b\n    if op == "-": return a - b\n    if op == "*": return a * b\n    if op == "/": return a / b if b else "деление на 0"\n\nprint(calc(5, 3, "+"))',
        "list": 'nums = [1, 2, 3, 4, 5]\nsquares = [x*x for x in nums]\nprint(squares)',
        "class": 'class Player:\n    def __init__(self, name, hp):\n        self.name = name\n        self.hp = hp\n    def hit(self, dmg):\n        self.hp -= dmg\n        return self.hp\n\np = Player("Вова", 100)\np.hit(30)\nprint(p.hp)',
    },
    "java": {
        "hello": 'public class Main {\n    public static void main(String[] args) {\n        System.out.println("Привет, мир!");\n    }\n}',
        "calc": 'public class Calc {\n    public static int add(int a, int b) {\n        return a + b;\n    }\n    public static void main(String[] args) {\n        System.out.println(add(5, 3));\n    }\n}',
        "list": 'import java.util.*;\npublic class Main {\n    public static void main(String[] args) {\n        List<Integer> nums = Arrays.asList(1, 2, 3, 4, 5);\n        nums.forEach(n -> System.out.println(n * n));\n    }\n}',
        "class": 'public class Player {\n    private String name;\n    private int hp;\n    public Player(String name, int hp) {\n        this.name = name;\n        this.hp = hp;\n    }\n    public int hit(int dmg) {\n        hp -= dmg;\n        return hp;\n    }\n    public static void main(String[] args) {\n        Player p = new Player("Вова", 100);\n        System.out.println(p.hit(30));\n    }\n}',
    },
}

# ══════════════════════════════════════════════════════════════
#  MP3
# ══════════════════════════════════════════════════════════════

IS_WIN = sys.platform == "win32"
_winmm = ctypes.windll.winmm if IS_WIN else None

def play_mp3(path, timeout_sec=180):
    if not IS_WIN or not _winmm:
        try:
            if sys.platform == "darwin":
                subprocess.run(["afplay", path], timeout=timeout_sec)
            else:
                subprocess.run(["ffplay", "-nodisp", "-autoexit",
                                "-loglevel", "quiet", path], timeout=timeout_sec)
            return True
        except Exception:
            return False
    short = path
    try:
        buf = ctypes.create_unicode_buffer(260)
        if ctypes.windll.kernel32.GetShortPathNameW(path, buf, 260):
            short = buf.value or path
    except Exception:
        pass
    alias = "dv_" + uuid.uuid4().hex[:6]
    try:
        r = _winmm.mciSendStringW(f'open "{short}" type mpegvideo alias {alias}', None, 0, 0)
        if r != 0: return False
        _winmm.mciSendStringW(f"play {alias} wait", None, 0, 0)
        _winmm.mciSendStringW(f"close {alias}", None, 0, 0)
        return True
    except Exception:
        try: _winmm.mciSendStringW(f"close {alias}", None, 0, 0)
        except Exception: pass
        return False

# ══════════════════════════════════════════════════════════════
#  TTS
# ══════════════════════════════════════════════════════════════

PRELOAD_PHRASES = ["Слушаю.", "Не понял. Переформулируй?", "Не нашёл такое приложение."]

class NeuralTTS:
    def __init__(self):
        self.q = queue.Queue()
        self.running = True
        self.voice = "ru-RU-SvetlanaNeural"
        self.rate = "+0%"
        self.volume = "+0%"
        self.tmp_dir = tempfile.gettempdir()
        self.cache_dir = os.path.join(self.tmp_dir, "darvis_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.enabled = True
        self._speaking_lock = threading.Lock()
        self._speaking = False
        self.last_engine = ""
        self._loop = None
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        threading.Thread(target=self._preload, daemon=True).start()

    def _get_loop(self):
        if self._loop is None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        return self._loop

    def _cache_path(self, text):
        h = hashlib.md5((text + "|" + self.voice).encode("utf-8")).hexdigest()
        return os.path.join(self.cache_dir, h + ".mp3")

    def _preload(self):
        time.sleep(1)
        for phrase in PRELOAD_PHRASES:
            if not self.running: return
            p = self._cache_path(phrase)
            if os.path.isfile(p) and os.path.getsize(p) > 100: continue
            try: self._synth_to_file(phrase, p)
            except Exception: pass

    def _synth_to_file(self, text, out_path):
        if edge_tts is None: return False
        loop = self._get_loop()
        async def job():
            comm = edge_tts.Communicate(text, self.voice, rate=self.rate, volume=self.volume)
            await comm.save(out_path)
        try:
            loop.run_until_complete(asyncio.wait_for(job(), timeout=60))
            return True
        except Exception as e:
            print(f"synth: {e}"); return False

    def _set_speaking(self, v):
        with self._speaking_lock: self._speaking = v

    def is_speaking(self):
        with self._speaking_lock: return self._speaking

    def _worker(self):
        while self.running:
            try:
                text = self.q.get(timeout=0.3)
                if text is None: continue
                if not self.enabled: continue
                self._set_speaking(True)
                try: self._speak(str(text).strip())
                finally: self._set_speaking(False)
            except queue.Empty: continue
            except Exception as e:
                print(f"TTS: {e}"); self._set_speaking(False)

    def _speak(self, text):
        if not text: return
        cached = self._cache_path(text)
        if os.path.isfile(cached) and os.path.getsize(cached) > 100:
            self.last_engine = "Edge(cache)"; play_mp3(cached, 180); return
        fname = os.path.join(self.tmp_dir, f"dv_{uuid.uuid4().hex}.mp3")
        if self._synth_to_file(text, fname) and os.path.getsize(fname) > 100:
            try:
                import shutil; shutil.copyfile(fname, cached)
            except Exception: pass
            self.last_engine = "Edge"; play_mp3(fname, 180)
            try: os.remove(fname)
            except Exception: pass
            return
        try: os.remove(fname)
        except Exception: pass
        self._speak_sapi(text); self.last_engine = "SAPI"

    def _speak_sapi(self, text):
        try:
            safe = text.replace("'", "''").replace('"', '\\"')
            ps = ('Add-Type -AssemblyName System.Speech;'
                  '$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;'
                  f"$s.Speak('{safe}')")
            flags = subprocess.CREATE_NO_WINDOW if IS_WIN else 0
            subprocess.run(["powershell", "-Command", ps],
                           capture_output=True, timeout=180, creationflags=flags)
        except Exception: pass

    def say(self, text):
        if not self.enabled: return
        try: self.q.put_nowait(str(text))
        except Exception: pass

    def set_voice(self, v):
        self.voice = v
        threading.Thread(target=self._preload, daemon=True).start()
    def set_rate(self, r): self.rate = r
    def set_volume(self, v): self.volume = v
    def stop(self):
        self.running = False
        try: self.q.put_nowait(None)
        except Exception: pass
        if self._loop:
            try: self._loop.close()
            except Exception: pass

# ══════════════════════════════════════════════════════════════
#  ХЕЛПЕРЫ
# ══════════════════════════════════════════════════════════════

def safe_open(path):
    try: os.startfile(path); return True
    except Exception:
        try:
            subprocess.Popen(["cmd", "/c", "start", "", path], shell=False); return True
        except Exception: return False

def find_app(name):
    n = name.lower().strip()
    if not n: return None
    for junk in ["пожалуйста", "мне", "быстро", "давай", "ну", "игру",
                 "приложение", "программу", "сайт"]:
        n = n.replace(junk, " ").strip()
    if not n: return None
    best, best_score = None, 0
    for key, path in APPS.items():
        s = _fz.partial_ratio(key, n)
        if s > best_score: best_score = s; best = (key, path)
    if best and best_score >= 70: return best
    return None

def open_app(name):
    found = find_app(name)
    if not found: return None
    key, path = found
    if path.startswith(("http://", "https://", "steam://", "ms-settings:")):
        return f"Открываю {key}." if safe_open(path) else f"Не смог открыть {key}."
    if path.endswith(".exe"):
        if os.path.isfile(path):
            try: subprocess.Popen([path]); return f"Открываю {key}."
            except Exception as e: return f"Ошибка: {e}"
        try: subprocess.Popen([path]); return f"Открываю {key}."
        except FileNotFoundError:
            try: subprocess.Popen([path], shell=True); return f"Открываю {key}."
            except Exception as e: return f"Не нашёл {key}: {e}"
    return f"Открываю {key}." if safe_open(path) else None

def find_proc(name):
    n = name.lower().strip()
    if not n: return None
    for junk in ["пожалуйста", "мне", "быстро", "давай", "ну", "игру", "приложение"]:
        n = n.replace(junk, " ").strip()
    if not n: return None
    best, best_score = None, 0
    for key, proc in PROC_MAP.items():
        s = _fz.partial_ratio(key, n)
        if s > best_score: best_score = s; best = (key, proc)
    if best and best_score >= 70: return best
    return None

def close_app(name):
    found = find_proc(name)
    if not found: return None
    key, proc = found
    try:
        flags = subprocess.CREATE_NO_WINDOW if IS_WIN else 0
        r = subprocess.run(["taskkill", "/F", "/IM", proc],
                           capture_output=True, text=True, shell=True,
                           timeout=10, creationflags=flags)
        if r.returncode == 0: return f"Закрываю {key}."
        return f"{key} не запущено."
    except Exception as e:
        return f"Ошибка закрытия {key}: {e}"

# ─── Признаки команд ───

def is_open_cmd(t): return any(w in t for w in ["открой", "запусти", "включи", "open", "start"])
def is_close_cmd(t): return any(w in t for w in ["закрой", "закрыть", "выключи", "убей", "прибей", "заверши"])
def is_search_cmd(t): return any(w in t for w in ["найди", "поищи", "покажи", "загугли", "погугли", "в поиск", "искать"])

# ─── СКАЗКИ (сильные триггеры — проверяем ДО поиска) ───

TALE_STRONG_TRIGGERS = [
    "расскажи сказку", "прочитай сказку", "почитай сказку", "прочти сказку",
    "расскажи мне сказку", "прочитай мне сказку",
    "найди сказку", "найди мне сказку", "хочу сказку", "включи сказку",
    "расскажи историю", "расскажи мне историю", "прочитай историю",
    "сказка про", "сказку про", "историю про",
    "расскажи про колобка", "расскажи про репку", "расскажи про теремок",
    "расскажи про курочку", "расскажи про трёх медведей", "расскажи про гусей",
]

def is_tale_cmd(t):
    """Проверяет, что фраза — про сказку."""
    tl = t.lower()
    # Прямые триггеры
    if any(w in tl for w in TALE_STRONG_TRIGGERS):
        return True
    # Комбо: "сказка" + глагол
    if "сказк" in tl and any(w in tl for w in
        ["расскажи", "прочитай", "почитай", "прочти", "найди", "включи", "хочу"]):
        return True
    # "истори" + глагол
    if "истори" in tl and any(w in tl for w in
        ["расскажи", "прочитай", "почитай", "прочти"]):
        return True
    return False

def find_tale(t):
    """Найти сказку по имени внутри фразы. Возвращает (name, text) или (None, None)."""
    tl = t.lower()
    best_name, best_score = None, 0
    for name in FAIRY_TALES.keys():
        s = _fz.partial_ratio(name, tl)
        if s > best_score:
            best_score = s; best_name = name
    # порог понижен — «колобок», «колобка» дают высокое совпадение
    if best_name and best_score >= 60:
        return best_name, FAIRY_TALES[best_name]
    return None, None

def tell_tale(t):
    """Возвращает текст сказки для озвучки."""
    name, text = find_tale(t)
    if not text:
        # Если сказка не указана — берём колобок (самая известная)
        name = "колобок"
        text = FAIRY_TALES[name]
    return f"Сказка «{name.capitalize()}». {text}"

# ─── МУЗЫКА ───

AUDIO_TRIGGERS = [
    "включи музыку", "включи песню", "включи аудио", "включи трек",
    "поставь музыку", "поставь песню", "поставь аудио",
    "открой музыку", "открой аудио", "открой песню",
    "найди музыку", "найди песню", "найди аудио",
    "воспроизведи", "запусти музыку", "запусти песню",
]

def is_audio_cmd(t):
    tl = t.lower()
    if any(w in tl for w in AUDIO_TRIGGERS): return True
    if "музык" in tl and any(w in tl for w in ["включи", "поставь", "найди", "открой", "запусти", "воспроизведи"]):
        return True
    if "песн" in tl and any(w in tl for w in ["включи", "поставь", "найди", "открой", "запусти", "воспроизведи"]):
        return True
    if "аудио" in tl and any(w in tl for w in ["включи", "поставь", "найди", "открой", "запусти", "воспроизведи"]):
        return True
    if "трек" in tl and any(w in tl for w in ["включи", "поставь", "найди", "открой", "запусти", "воспроизведи"]):
        return True
    return False

def extract_audio_query(t):
    s = t.lower().strip()
    for trigger in AUDIO_TRIGGERS:
        s = s.replace(trigger, " ")
    for junk in ["музыку", "музыка", "музыки", "песню", "песня", "песни",
                 "аудио", "трек", "пожалуйста", "мне", "давай",
                 "включи", "поставь", "найди", "открой", "запусти",
                 "воспроизведи", "на ютубе", "в ютубе", "на youtube",
                 "и", "про"]:
        s = re.sub(rf"\b{junk}\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip().strip("?.,!;:")
    return s if s else None

def play_audio(query):
    """Открывает YouTube с поиском — первый результат можно кликнуть."""
    if not query:
        try:
            webbrowser.open("https://www.youtube.com/")
            return "Открываю YouTube."
        except Exception as e:
            return f"Не смог: {e}"
    q = urllib.parse.quote(query)
    url = f"https://www.youtube.com/results?search_query={q}"
    try:
        webbrowser.open(url)
        return f"Открываю YouTube и ищу: {query}"
    except Exception as e:
        return f"Не смог открыть: {e}"

# ─── КОД ───

CODE_TRIGGERS = ["напиши код", "покажи код", "напиши программу",
                 "покажи программу", "пример кода", "пример на",
                 "напиши пример", "код на", "напиши на", "покажи на"]

def is_code_cmd(t): return any(w in t for w in CODE_TRIGGERS)

def detect_language(t):
    tl = t.lower()
    if "python" in tl or "питон" in tl or "пайтон" in tl: return "python"
    if "java" in tl or "джава" in tl: return "java"
    return None

def detect_code_type(t):
    tl = t.lower()
    if any(w in tl for w in ["калькулятор", "калькулят", "calc", "сложение"]): return "calc"
    if any(w in tl for w in ["список", "массив", "list"]): return "list"
    if any(w in tl for w in ["класс", "class", "объект"]): return "class"
    return "hello"

def generate_code(t):
    lang = detect_language(t) or "python"
    typ = detect_code_type(t)
    return lang, CODE_TEMPLATES[lang][typ]

# ─── ОБЩИЕ ───

def split_targets(s):
    s = s.strip()
    for junk in ["пожалуйста", "мне", "давай", "быстро", "ну"]:
        s = s.replace(junk, " ")
    s = s.strip()
    parts = re.split(r"\s+и\s+|,\s*|\s*\+\s*", s)
    return [p.strip() for p in parts if p.strip()]

def extract_search_query(t):
    patterns = [
        r"(?:найди|поищи|покажи|загугли|погугли|искать)\s+(?:в\s+поиск[еу]?\s+)?(.+?)(?:\s+на\s+\w+)?$",
        r"в\s+поиск[еу]?\s+(.+?)(?:\s+на\s+\w+)?$",
    ]
    for p in patterns:
        m = re.search(p, t)
        if m:
            q = m.group(1).strip().strip("?.!,")
            for site in SITE_SEARCH.keys():
                q = q.replace(site, "").strip()
            if q: return q
    return None

def extract_site(t):
    tl = t.lower()
    best, best_score = None, 0
    for key, tmpl in SITE_SEARCH.items():
        s = _fz.partial_ratio(key, tl)
        if s > best_score: best_score = s; best = (key, tmpl)
    if best and best_score >= 70: return best
    return None

def do_search_on_site(site_key, url_tmpl, query):
    q = urllib.parse.quote(query)
    try:
        webbrowser.open(url_tmpl.format(q))
        return f"Открываю {site_key}, ищу {query}."
    except Exception as e:
        return f"Ошибка: {e}"

def do_web_search(query, mode="web"):
    q = urllib.parse.quote(query)
    if mode == "images":
        webbrowser.open(f"https://yandex.ru/images/search?text={q}")
        return f"Ищу картинки: {query}"
    webbrowser.open(f"https://www.google.com/search?q={q}")
    return f"Ищу в интернете: {query}"

def words_to_num(s):
    for k, v in RU_NUMS.items():
        s = re.sub(rf"\b{k}\b", str(v), s)
    return s

def try_math(text):
    s = text.lower()
    s = words_to_num(s)
    s = s.replace("плюс", "+").replace("минус", "-")
    s = s.replace("умножить на", "*").replace("умножить", "*")
    s = s.replace("разделить на", "/").replace("разделить", "/")
    s = s.replace("в квадрате", "**2").replace("в кубе", "**3")
    s = re.sub(r"(сколько будет|посчитай|вычисли|реши|равно|=|\?)", " ", s)
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*([\+\-\*/]|\*\*)\s*(-?\d+(?:\.\d+)?)", s)
    if m:
        try:
            a = float(m.group(1)); op = m.group(2); b = float(m.group(3))
            if op == "+": r = a + b
            elif op == "-": r = a - b
            elif op == "*": r = a * b
            elif op == "/":
                if b == 0: return "На ноль делить нельзя."
                r = a / b
            elif op == "**": r = a ** b
            else: return None
            if r == int(r): r = int(r)
            return f"{a:g} {op} {b:g} = {r}"
        except Exception: return None
    m = re.search(r"корень (?:из )?(\d+(?:\.\d+)?)", s)
    if m:
        x = float(m.group(1))
        if x < 0: return "Корень из отрицательного не существует."
        return f"Корень из {m.group(1)} = {round(math.sqrt(x), 4)}"
    m = re.search(r"(\d+)\s*факториал", s) or re.search(r"факториал\s+(\d+)", s)
    if m:
        n = int(m.group(1))
        if n > 170: return "Слишком большое число."
        return f"{n}! = {math.factorial(n)}"
    return None

def get_time():
    n = datetime.now(); return f"Сейчас {n.hour} часов {n.minute} минут"
def get_date():
    n = datetime.now(); return f"Сегодня {n.day} {MONTHS_RU[n.month-1]} {n.year} года"
def get_weekday():
    d = ["понедельник","вторник","среда","четверг","пятница","суббота","воскресенье"]
    return f"Сегодня {d[datetime.now().weekday()]}"
def is_wake_word(t):
    t = t.lower().strip()
    for w in WAKE_WORDS:
        if _fz.partial_ratio(w, t) >= WAKE_THRESHOLD: return True
    return False

# ══════════════════════════════════════════════════════════════
#  МОЗГ
# ══════════════════════════════════════════════════════════════

class Brain:
    def __init__(self):
        self.mem = {"name": None, "age": None, "city": None}

    def respond(self, text):
        t = text.lower().strip()
        m = re.search(r"меня зовут\s+([а-яёa-z]+)", t)
        if m:
            name = m.group(1).capitalize(); self.mem["name"] = name
            return f"Приятно познакомиться, {name}!"
        m = re.search(r"мне\s+(\d+)", t)
        if m:
            self.mem["age"] = m.group(1); return f"Запомнил: тебе {m.group(1)}."
        m = re.search(r"(?:я из|живу в)\s+([а-яёa-z]+)", t)
        if m:
            city = m.group(1).capitalize(); self.mem["city"] = city
            return f"Круто, {city}!"
        if "время" in t or "час" in t: return get_time()
        if "число" in t or "дата" in t: return get_date()
        if "день недели" in t: return get_weekday()
        mr = try_math(t)
        if mr: return mr
        if "монет" in t: return "Орёл или решка. " + random.choice(["Орёл.", "Решка."])
        if "кубик" in t or "кость" in t: return f"Выпало {random.randint(1, 6)}"
        m = re.search(r"(простое ли|является ли простым)\s+(\d+)", t)
        if m:
            n = int(m.group(2))
            if n < 2: return f"{n} не простое."
            for i in range(2, int(n ** 0.5) + 1):
                if n % i == 0: return f"{n} не простое, делится на {i}."
            return f"{n} — простое."
        if "как меня зовут" in t:
            if self.mem["name"]: return f"Тебя зовут {self.mem['name']}."
            return "Ты не говорил, как тебя зовут."
        for kws, answers in RULES.items():
            for kw in kws:
                if kw in t: return random.choice(answers)
        return random.choice(["Не понял. Переформулируй?",
                              "Скажи что умеешь — расскажу."])

# ══════════════════════════════════════════════════════════════
#  ОБРАБОТКА КОМАНДЫ (порядок важен!)
# ══════════════════════════════════════════════════════════════

def process_command(t, brain):
    """
    Возвращает (ответ, код_или_None).
    Порядок проверок:
      1. КОД
      2. СКАЗКИ (до поиска!)
      3. МУЗЫКА
      4. ПОИСК
      5. ЗАКРЫТИЕ
      6. ОТКРЫТИЕ
      7. Вопросы мозга
    """
    tl = t.lower().strip()

    # ─── 1. КОД ───
    if is_code_cmd(tl):
        lang, code = generate_code(tl)
        resp = "Вот пример кода на Python." if lang == "python" else "Вот пример кода на Java."
        return resp, code

    # ─── 2. СКАЗКИ (ДО поиска, чтобы "найди мне сказку" не ушло в Google) ───
    if is_tale_cmd(tl):
        tale = tell_tale(tl)
        return tale, None

    # ─── 3. МУЗЫКА ───
    if is_audio_cmd(tl):
        query = extract_audio_query(tl)
        return play_audio(query), None

    # ─── 4. ПОИСК ───
    if is_search_cmd(tl):
        query = extract_search_query(tl)
        site = extract_site(tl)
        if query and site:
            site_key, tmpl = site
            return do_search_on_site(site_key, tmpl, query), None
        if query:
            mode = "images" if any(w in tl for w in
                ["картинк", "фото", "изображени", "image", "пикч"]) else "web"
            return do_web_search(query, mode), None

    # ─── 5. ЗАКРЫТИЕ ───
    if is_close_cmd(tl):
        targets = ""
        for w in ["закрой", "закрыть", "выключи", "убей", "прибей", "заверши"]:
            if w in tl:
                targets = tl.split(w, 1)[1].strip()
                break
        items = split_targets(targets)
        if not items: return "Что закрыть?", None
        results = []
        for item in items:
            r = close_app(item)
            results.append(r if r else f"{item} — не нашёл.")
        return " ".join(results), None

    # ─── 6. ОТКРЫТИЕ ───
    if is_open_cmd(tl):
        targets = tl
        for w in ["открой", "запусти", "включи", "open", "start"]:
            if w in tl:
                targets = tl.split(w, 1)[1].strip()
                break
        if is_search_cmd(targets):
            query = extract_search_query(targets)
            site = extract_site(targets)
            if site and query:
                site_key, tmpl = site
                return do_search_on_site(site_key, tmpl, query), None
            if query:
                return do_web_search(query, "web"), None
        items = split_targets(targets)
        if not items: return "Что открыть?", None
        results = []
        for item in items:
            r = open_app(item)
            results.append(r if r else f"{item} — не нашёл.")
        return " ".join(results), None

    if tl.startswith("что такое "):
        q = tl[10:].strip().strip("?")
        return do_web_search(q, "web"), None

    return brain.respond(tl), None

# ══════════════════════════════════════════════════════════════
#  ЗАПИСЬ
# ══════════════════════════════════════════════════════════════

SAMPLE_RATE = 16000

def record_audio_sd(duration=MAX_DURATION, silence_sec=SILENCE_AFTER_SPEECH,
                     stop_flag=None, tts_check=None, device=None):
    try:
        if tts_check is not None:
            wait_until = time.time() + 120
            while tts_check() and time.time() < wait_until:
                if stop_flag is not None and not stop_flag(): return None
                time.sleep(0.05)
        frames = []
        chunk = 1024
        max_chunks = int(SAMPLE_RATE * duration / chunk)
        silence_limit = int(SAMPLE_RATE * silence_sec / chunk)
        silent_chunks = 0; started = False
        def callback(indata, nframes, t, status):
            frames.append(indata.copy())
        kwargs = dict(samplerate=SAMPLE_RATE, channels=1, dtype='int16',
                      blocksize=chunk, callback=callback)
        if device is not None: kwargs["device"] = device
        with sd.InputStream(**kwargs):
            for _ in range(max_chunks):
                if stop_flag is not None and not stop_flag(): break
                time.sleep(chunk / SAMPLE_RATE)
                if frames:
                    last = frames[-1]
                    level = int(np.abs(last).mean())
                    if level > START_THRESHOLD:
                        started = True; silent_chunks = 0
                    else:
                        silent_chunks += 1
                        if started and silent_chunks > silence_limit: break
        if not frames: return None
        data = np.concatenate(frames, axis=0)
        if int(np.abs(data).mean()) < MIN_SPEECH_LEVEL: return None
        wav = io.BytesIO()
        with wave.open(wav, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
            wf.writeframes(data.tobytes())
        wav.seek(0); return wav.read()
    except Exception as e:
        print(f"record: {e}"); return None

# ══════════════════════════════════════════════════════════════
#  GUI
# ══════════════════════════════════════════════════════════════

class DarvisApp:
    def __init__(self, root):
        self.root = root
        root.title("Darvis Beta Test")
        root.configure(bg=T["bg"])
        root.geometry("960x820")
        root.minsize(750, 640)

        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.6

        self.tts = NeuralTTS()
        self.brain = Brain()

        self.mic_idx = None
        self.listening = False
        self.active = False
        self.thread = None
        self.out_q = queue.Queue()
        self.first_calibration_done = False

        self._build_ui()
        self._load_mics()
        self._poll_queue()
        self._log_system("Darvis Beta Test v9.0 запущен.")
        self._log_system("Сказки: «расскажи сказку про колобка».")
        self._log_system("Музыка: «включи музыку перемен».")
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        head = tk.Frame(self.root, bg=T["bg"], height=72)
        head.pack(fill="x"); head.pack_propagate(False)
        logo = tk.Frame(head, bg=T["bg"]); logo.pack(side="left", padx=(20, 0), pady=10)

        self.avatar_img = get_avatar_image(52)
        if self.avatar_img:
            tk.Label(logo, image=self.avatar_img, bg=T["bg"], bd=0).pack(side="left")
        else:
            av = tk.Canvas(logo, width=52, height=52, bg=T["bg"], highlightthickness=0)
            av.pack(side="left")
            self.av_bg = av.create_oval(2, 2, 50, 50, fill=T["accent"], outline="")
            av.create_text(26, 26, text="D", fill="#fff", font=("Segoe UI", 22, "bold"))
            self.av_canvas = av

        info = tk.Frame(logo, bg=T["bg"]); info.pack(side="left", padx=12)
        tk.Label(info, text="Darvis Beta Test", bg=T["bg"], fg=T["text"],
                 font=("Segoe UI Semibold", 18), anchor="w").pack(anchor="w")
        self.status_small = tk.Label(info, text="● ожидание", bg=T["bg"], fg=T["muted"],
                                       font=("Segoe UI", 9), anchor="w")
        self.status_small.pack(anchor="w")

        right = tk.Frame(head, bg=T["bg"]); right.pack(side="right", padx=20)
        self.status_big = tk.Label(right, text="● ГОТОВ", bg=T["bg"], fg=T["green"],
                                     font=("Segoe UI Semibold", 12))
        self.status_big.pack(pady=(20, 0))
        tk.Frame(self.root, bg=T["panel2"], height=1).pack(fill="x")

        panel = tk.Frame(self.root, bg=T["bg"]); panel.pack(fill="x", padx=20, pady=(10, 6))

        mrow = tk.Frame(panel, bg=T["panel"]); mrow.pack(fill="x", pady=(0, 6))
        tk.Label(mrow, text="  🎤 Микрофон:", bg=T["panel"], fg=T["muted"],
                 font=("Segoe UI", 10)).pack(side="left", padx=(8, 4), pady=8)
        self.mic_cb = ttk.Combobox(mrow, state="readonly", font=("Segoe UI", 10), width=50)
        self.mic_cb.pack(side="left", padx=6, pady=8, fill="x", expand=True)
        self.mic_cb.bind("<<ComboboxSelected>>", self._on_mic_selected)
        tk.Button(mrow, text="↻", command=self._load_mics, bg=T["panel2"], fg=T["text"],
                  relief="flat", bd=0, font=("Segoe UI", 10), padx=8, pady=4,
                  cursor="hand2").pack(side="left", padx=(0, 8))

        vrow = tk.Frame(panel, bg=T["panel"]); vrow.pack(fill="x", pady=(0, 6))
        tk.Label(vrow, text="  🔊 Голос:", bg=T["panel"], fg=T["muted"],
                 font=("Segoe UI", 10)).pack(side="left", padx=(8, 4), pady=8)
        self.voice_cb = ttk.Combobox(vrow, state="readonly", font=("Segoe UI", 10), width=30)
        self.voice_cb["values"] = list(VOICES.keys())
        self.voice_cb.current(0)
        self.voice_cb.pack(side="left", padx=6, pady=8)
        self.voice_cb.bind("<<ComboboxSelected>>", self._on_voice_selected)
        self.voice_on_var = tk.BooleanVar(value=True)
        tk.Checkbutton(vrow, text="Озвучивать", variable=self.voice_on_var,
                       command=self._on_voice_toggle,
                       bg=T["panel"], fg=T["text"], selectcolor=T["accent"],
                       activebackground=T["panel"],
                       font=("Segoe UI", 10)).pack(side="left", padx=10)

        brow = tk.Frame(panel, bg=T["bg"]); brow.pack(fill="x", pady=(0, 6))
        self.start_btn = tk.Button(brow, text="▶  НАЧАТЬ", command=self._toggle_listen,
                                    bg=T["green"], fg="#fff", relief="flat", bd=0,
                                    font=("Segoe UI", 11, "bold"), padx=24, pady=10,
                                    cursor="hand2")
        self.start_btn.pack(side="left", padx=(0, 8))
        tk.Button(brow, text="🧪 Тест голоса", command=self._test_voice,
                  bg=T["panel2"], fg=T["text"], relief="flat", bd=0,
                  font=("Segoe UI", 10), padx=14, pady=10,
                  cursor="hand2").pack(side="left", padx=8)
        tk.Button(brow, text="🧹 Очистить", command=self._clear_chat,
                  bg=T["panel2"], fg=T["text"], relief="flat", bd=0,
                  font=("Segoe UI", 10), padx=14, pady=10,
                  cursor="hand2").pack(side="left", padx=8)
        tk.Button(brow, text="❓ Что умею", command=self._show_help,
                  bg=T["panel2"], fg=T["text"], relief="flat", bd=0,
                  font=("Segoe UI", 10), padx=14, pady=10,
                  cursor="hand2").pack(side="right", padx=8)

        chat_wrap = tk.Frame(self.root, bg=T["bg"])
        chat_wrap.pack(fill="both", expand=True, padx=20, pady=(4, 14))
        tk.Label(chat_wrap, text="💬 Диалог", bg=T["bg"], fg=T["accent"],
                 font=("Segoe UI Semibold", 11)).pack(anchor="w", pady=(0, 4))
        chat_box = tk.Frame(chat_wrap, bg=T["panel"]); chat_box.pack(fill="both", expand=True)
        self.chat = tk.Text(chat_box, bg="#05070a", fg=T["text"],
                            font=("Segoe UI", 10), bd=0, padx=12, pady=10,
                            wrap="word", cursor="arrow",
                            highlightthickness=0, state="disabled")
        vs = tk.Scrollbar(chat_box, orient="vertical", command=self.chat.yview,
                          bg=T["panel"], troughcolor="#05070a", bd=0)
        self.chat.configure(yscrollcommand=vs.set)
        self.chat.pack(side="left", fill="both", expand=True); vs.pack(side="right", fill="y")
        self.chat.tag_config("user_name", foreground=T["user"], font=("Segoe UI Semibold", 10))
        self.chat.tag_config("ai_name", foreground=T["accent"], font=("Segoe UI Semibold", 10))
        self.chat.tag_config("sys_name", foreground=T["muted"], font=("Segoe UI Semibold", 9))
        self.chat.tag_config("user_msg", foreground=T["text"], font=("Segoe UI", 10))
        self.chat.tag_config("ai_msg", foreground=T["text"], font=("Segoe UI", 10))
        self.chat.tag_config("sys_msg", foreground=T["muted"], font=("Segoe UI", 9))
        self.chat.tag_config("code_block", foreground="#7dd3fc", background="#0a1220",
                             font=("Consolas", 9))

        bar = tk.Frame(self.root, bg=T["panel"], height=24)
        bar.pack(fill="x", side="bottom"); bar.pack_propagate(False)
        tk.Label(bar, text="  Darvis Beta Test v9.0",
                 bg=T["panel"], fg=T["muted"], font=("Segoe UI", 9)).pack(side="left", padx=10)
        self.engine_lbl = tk.Label(bar, text="", bg=T["panel"], fg=T["green"],
                                     font=("Segoe UI", 9))
        self.engine_lbl.pack(side="left", padx=10)
        self.mem_lbl = tk.Label(bar, text="", bg=T["panel"], fg=T["muted"],
                                 font=("Segoe UI", 9))
        self.mem_lbl.pack(side="right", padx=10)

    def _update_engine_lbl(self):
        eng = self.tts.last_engine
        if eng:
            try:
                color = T["green"] if "Edge" in eng else T["yellow"]
                self.engine_lbl.config(text=f"  Голос: {eng}", fg=color)
            except Exception: pass

    def _on_voice_selected(self, e=None):
        try:
            name = self.voice_cb.get()
            self.tts.set_voice(VOICES.get(name, "ru-RU-SvetlanaNeural"))
            self._log_system(f"Голос: {name}")
        except Exception as ex: self._log_system(f"Ошибка: {ex}")

    def _on_voice_toggle(self):
        self.tts.enabled = self.voice_on_var.get()
        self._log_system(f"Озвучивание {'включено' if self.tts.enabled else 'выключено'}")

    def _on_close(self):
        self.listening = False
        try: self.tts.stop()
        except Exception: pass
        try: self.root.destroy()
        except Exception: pass

    def _load_mics(self):
        if not hasattr(self, "chat"): return
        try:
            devices = sd.query_devices()
            inputs = [(i, d["name"]) for i, d in enumerate(devices)
                      if d["max_input_channels"] > 0]
            items = ["[авто] Микрофон по умолчанию"]
            for idx, name in inputs: items.append(f"[{idx}] {name}")
            self.mic_cb["values"] = items
            self.mic_cb.current(0); self.mic_idx = None
            self._log_system(f"Микрофонов: {len(inputs)} (+авто)")
        except Exception as e: self._log_system(f"Ошибка поиска: {e}")

    def _on_mic_selected(self, e=None):
        try:
            i = self.mic_cb.current()
            if i <= 0: self.mic_idx = None
            else:
                m = re.match(r"\[(\d+)\]", self.mic_cb.get())
                self.mic_idx = int(m.group(1)) if m else None
            self._log_system(f"Микрофон: {self.mic_cb.get()}")
        except Exception as ex: self._log_system(f"Ошибка: {ex}")

    def _append(self, who, text, tag_name, msg_tag):
        if not hasattr(self, "chat"): return
        try:
            self.chat.configure(state="normal")
            if who: self.chat.insert("end", f"{who} ", tag_name)
            self.chat.insert("end", f"{text}\n", msg_tag)
            self.chat.see("end"); self.chat.configure(state="disabled")
        except Exception: pass

    def _append_code(self, code):
        if not hasattr(self, "chat"): return
        try:
            self.chat.configure(state="normal")
            self.chat.insert("end", "\n", "ai_msg")
            self.chat.insert("end", code + "\n\n", "code_block")
            self.chat.see("end"); self.chat.configure(state="disabled")
        except Exception: pass

    def _log_user(self, t): self._append("👤 Ты:", t, "user_name", "user_msg")
    def _log_ai(self, t): self._append("🤖 Дарвис:", t, "ai_name", "ai_msg")
    def _log_system(self, t): self._append("⚙", t, "sys_name", "sys_msg")

    def _clear_chat(self):
        try:
            self.chat.configure(state="normal")
            self.chat.delete("1.0", "end")
            self.chat.configure(state="disabled")
        except Exception: pass

    def _set_status(self, text, color):
        try:
            self.status_big.config(text=f"● {text.upper()}", fg=color)
            self.status_small.config(text=f"● {text.lower()}", fg=color)
            if hasattr(self, "av_canvas"):
                self.av_canvas.itemconfig(self.av_bg, fill=color)
        except Exception: pass

    def _toggle_listen(self):
        if self.listening: self._stop_listening()
        else: self._start_listening()

    def _start_listening(self):
        self.listening = True; self.active = False
        self.start_btn.config(text="■  СТОП", bg=T["red"])
        self._set_status("калибровка", T["yellow"])
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()

    def _stop_listening(self):
        self.listening = False
        self.start_btn.config(text="▶  НАЧАТЬ", bg=T["green"])
        self._set_status("остановлено", T["red"])
        self._log_system("Слушание остановлено.")

    def _listen_loop(self):
        self.out_q.put(("status", ("готов", T["green"])))
        if not self.first_calibration_done:
            try:
                with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                                     dtype='int16', blocksize=1024):
                    time.sleep(1.0)
                self.first_calibration_done = True
            except Exception: pass
        self.out_q.put(("say", "Дарвис запущен. Скажи: Привет, Дарвис."))

        while self.listening:
            try:
                wav_bytes = record_audio_sd(
                    duration=MAX_DURATION, silence_sec=SILENCE_AFTER_SPEECH,
                    stop_flag=lambda: self.listening,
                    tts_check=lambda: self.tts.is_speaking(),
                    device=self.mic_idx)
                if not wav_bytes: continue
                self.out_q.put(("status", ("думаю…", T["yellow"])))
                audio = sr.AudioData(wav_bytes, SAMPLE_RATE, 2)
                try:
                    text = self.recognizer.recognize_google(audio, language="ru-RU")
                except sr.UnknownValueError:
                    self.out_q.put(("status", ("готов", T["green"]))); continue
                except sr.RequestError as e:
                    self.out_q.put(("log_sys", f"Нет интернета: {e}"))
                    self.out_q.put(("status", ("готов", T["green"])))
                    time.sleep(1); continue
                if not text:
                    self.out_q.put(("status", ("готов", T["green"]))); continue
                self.out_q.put(("log_user", text))
                t = text.lower().strip()

                if not self.active:
                    if is_wake_word(t):
                        self.active = True
                        self.out_q.put(("status", ("активирован", T["accent"])))
                        self.out_q.put(("say", "Слушаю."))
                    else:
                        self.out_q.put(("status", ("готов", T["green"])))
                    continue

                if any(w in t for w in ["пока", "отдыхай", "хватит"]):
                    self.active = False
                    self.out_q.put(("status", ("готов", T["green"])))
                    self.out_q.put(("say", "Ушёл в режим ожидания."))
                    continue

                ans, code = process_command(t, self.brain)
                if code:
                    self.out_q.put(("answer_code", (ans, code)))
                else:
                    self.out_q.put(("answer", ans))
                self.out_q.put(("status", ("готов", T["green"])))
            except Exception as e:
                self.out_q.put(("log_sys", f"Ошибка: {e}"))
                self.out_q.put(("status", ("готов", T["green"])))
                time.sleep(0.5)
        self.out_q.put(("status", ("остановлено", T["red"])))

    def _poll_queue(self):
        try:
            while True:
                kind, data = self.out_q.get_nowait()
                if kind == "log_user": self._log_user(data)
                elif kind == "log_sys": self._log_system(data)
                elif kind == "answer":
                    self._log_ai(data); self.tts.say(data)
                    self.root.after(300, self._update_engine_lbl)
                elif kind == "answer_code":
                    ans, code = data
                    self._log_ai(ans); self._append_code(code); self.tts.say(ans)
                    self.root.after(300, self._update_engine_lbl)
                elif kind == "say":
                    self._log_ai(data); self.tts.say(data)
                    self.root.after(300, self._update_engine_lbl)
                elif kind == "status":
                    text, color = data; self._set_status(text, color)
        except queue.Empty: pass
        except Exception as e: print(f"poll: {e}")
        try: self.root.after(50, self._poll_queue)
        except Exception: pass

    def _test_voice(self):
        self.tts.say("Привет! Я Дарвис Beta Test. Умею рассказывать сказки, включать музыку и писать код.")

    def _show_help(self):
        win = tk.Toplevel(self.root); win.title("Что умеет Darvis Beta Test")
        win.configure(bg=T["bg"]); win.geometry("700x720"); win.transient(self.root)
        tk.Label(win, text="Darvis Beta Test — что умею", bg=T["bg"], fg=T["accent"],
                 font=("Segoe UI Semibold", 15)).pack(anchor="w", padx=20, pady=(16, 8))
        text = """АКТИВАЦИЯ:
  «Привет, Дарвис»

СКАЗКИ (голосом, целиком):
  «Расскажи сказку про колобка»
  «Найди мне сказку колобок и прочитай»
  «Прочитай сказку про репку»
  «Сказка про теремок»
  «Расскажи про курочку рябу»
  «Сказка про трёх медведей»
  «Расскажи про гусей-лебедей»

МУЗЫКА:
  «Включи музыку перемен»
  «Включи песню Imagine»
  «Поставь аудио Бетховен»
  «Найди песню Miyagi»

КОД:
  «Напиши код на Python»
  «Напиши код на Java»
  «Напиши программу на Python калькулятор»
  «Покажи пример на Python список»
  «Напиши код на Java класс»

ОТКРЫТИЕ / ЗАКРЫТИЕ:
  «Открой стим», «Закрой хром»

ПОИСК:
  «Найди яблоко», «Найди картинки кота»
  «Что такое квант»

МАТЕМАТИКА / ВРЕМЯ:
  «Сколько будет 5 плюс 3?»
  «Сколько времени?»

ЯЗЫКИ ПРОГРАММИРОВАНИЯ:
  «Что такое Python?», «Что такое Java?»"""
        box = tk.Frame(win, bg=T["panel"]); box.pack(fill="both", expand=True, padx=20, pady=(0, 16))
        tx = tk.Text(box, bg="#05070a", fg=T["text"], font=("Consolas", 10),
                     bd=0, padx=12, pady=10, wrap="word")
        vs = tk.Scrollbar(box, orient="vertical", command=tx.yview, bd=0)
        tx.configure(yscrollcommand=vs.set)
        tx.pack(side="left", fill="both", expand=True); vs.pack(side="right", fill="y")
        tx.insert("1.0", text)

def _report_callback_exception(exc_type, exc_value, exc_tb):
    print("Callback error:\n" + "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))

def main():
    try:
        root = tk.Tk()
        root.report_callback_exception = _report_callback_exception
        app = DarvisApp(root)
        root.mainloop()
    except Exception:
        tb = traceback.format_exc(); print(tb)
        try:
            r = tk.Tk(); r.withdraw()
            messagebox.showerror("Darvis Beta Test", tb); r.destroy()
        except Exception: pass

if __name__ == "__main__":
    main()