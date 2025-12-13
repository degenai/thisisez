import sys
import time
import warnings

# Compatibility Patch for Python < 3.10
if sys.version_info < (3, 10):
    try:
        import importlib_metadata
        import importlib.metadata
        if not hasattr(importlib.metadata, 'packages_distributions'):
            importlib.metadata.packages_distributions = importlib_metadata.packages_distributions
    except ImportError:
        pass # importlib_metadata not installed

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import threading
import subprocess
import queue
import os
import random
import pygame
import math

# Suppress warnings for cleaner UI
warnings.filterwarnings("ignore", category=FutureWarning)

import harvester
import consolidator

class TextRedirector(object):
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.configure(state="normal")
        self.widget.insert("end", str, (self.tag,))
        self.widget.see("end")
        self.widget.configure(state="disabled")
        self.widget.update_idletasks()

    def flush(self):
        pass

class HarvesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AURA FARMER // HARVESTER CONTROL")
        self.root.geometry("900x700")
        self.root.configure(bg="black")

        # Styles
        self.font_style = ("Consolas", 10)
        self.bg_color = "#000000"
        self.fg_color = "#00FF00" # Hacker Green
        self.accent_color = "#003300"
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", background="#222", foreground="#888", padding=[10, 5], font=("Consolas", 10))
        style.map("TNotebook.Tab", background=[("selected", self.accent_color)], foreground=[("selected", self.fg_color)])
        style.configure("TFrame", background=self.bg_color)

        # Header Frame (Global)
        self.header_frame = tk.Frame(root, bg=self.bg_color)
        self.header_frame.pack(fill="x", padx=10, pady=10)
        
        # ASCII Art
        self.ascii_art = """
   ▄▄▄       █    ██  ██▀███   ▄▄▄      
  ▒████▄     ██  ▓██▒▓██ ▒ ██▒▒████▄    
  ▒██  ▀█▄  ▓██  ▒██░▓██ ░▄█ ▒▒██  ▀█▄  
  ░██▄▄▄▄██ ▓▓█  ░██░▒██▀▀█▄  ░██▄▄▄▄██ 
   ▓█   ▓██▒▒▒█████▓ ░██▓ ▒██▒ ▓█   ▓██▒
   ▒▒   ▓▒█░░▒▓▒ ▒ ▒ ░ ▒▓ ░▒▓░ ▒▒   ▓▒█░
        """
        self.header_label = tk.Label(self.header_frame, text=self.ascii_art, font=("Courier", 8), bg=self.bg_color, fg=self.fg_color, justify="left")
        self.header_label.pack(side="left")

        # Visualizer Canvas
        self.viz_canvas = tk.Canvas(self.header_frame, width=200, height=80, bg=self.bg_color, highlightthickness=0)
        self.viz_canvas.pack(side="right", padx=20)
        
        # 3D Viz State
        self.angle_x = 0
        self.angle_y = 0
        self.points = []
        self.base_radius = 30
        self.pulse_radius = 30
        
        # Generate Sphere Points
        num_points = 100
        phi = math.pi * (3. - math.sqrt(5.))
        for i in range(num_points):
            y = 1 - (i / float(num_points - 1)) * 2
            radius = math.sqrt(1 - y * y)
            theta = phi * i
            x = math.cos(theta) * radius
            z = math.sin(theta) * radius
            self.points.append([x, y, z])

        # Notebook (Tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # --- TAB 1: HARVEST ---
        self.tab_harvest = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_harvest, text="[ HARVEST ]")
        self.setup_harvest_tab()

        # --- TAB 2: UTILITIES ---
        self.tab_utils = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_utils, text="[ UTILITIES ]")
        self.setup_utils_tab()

        # Initialize Audio
        self.is_running = False
        self.music_on = False
        self.stop_event = threading.Event()
        self.playlist = []
        self.current_track = -1
        
        try:
            pygame.mixer.init()
            self.audio_available = True
            self.load_music()
        except Exception as e:
            print(f"[ERROR] Audio init failed: {e}")
            self.audio_available = False

        # Start loops
        self.check_music()
        self.update_viz()

    def setup_harvest_tab(self):
        # Controls Frame
        controls_frame = tk.Frame(self.tab_harvest, bg=self.bg_color, bd=1, relief="solid")
        controls_frame.pack(fill="x", padx=10, pady=5)

        # Config Section
        config_frame = tk.Frame(controls_frame, bg=self.bg_color)
        config_frame.pack(side="left", padx=10)

        tk.Label(config_frame, text="MAX THREADS (0=ALL):", bg=self.bg_color, fg=self.fg_color, font=self.font_style).grid(row=0, column=0, sticky="w")
        self.limit_entry = tk.Entry(config_frame, bg="#111", fg=self.fg_color, insertbackground=self.fg_color, font=self.font_style, width=5)
        self.limit_entry.insert(0, "0")
        self.limit_entry.grid(row=0, column=1, padx=5)

        tk.Label(config_frame, text="INTERVAL (HRS):", bg=self.bg_color, fg=self.fg_color, font=self.font_style).grid(row=1, column=0, sticky="w")
        self.interval_entry = tk.Entry(config_frame, bg="#111", fg=self.fg_color, insertbackground=self.fg_color, font=self.font_style, width=5)
        self.interval_entry.insert(0, "1.0")
        self.interval_entry.grid(row=1, column=1, padx=5)

        # Auto-Consolidate Toggle
        self.auto_consolidate = tk.BooleanVar(value=False)
        self.consolidate_chk = tk.Checkbutton(config_frame, text="AUTO-CONSOLIDATE", variable=self.auto_consolidate, bg=self.bg_color, fg="#00AAAA", selectcolor="#222", activebackground=self.bg_color, activeforeground="#00FFFF", font=("Consolas", 9))
        self.consolidate_chk.grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

        # Buttons
        btn_frame = tk.Frame(controls_frame, bg=self.bg_color)
        btn_frame.pack(side="right", padx=10, pady=10)

        self.start_btn = tk.Button(btn_frame, text="[ START HARVEST ]", command=self.start_harvest, bg=self.bg_color, fg=self.fg_color, activebackground=self.fg_color, activeforeground=self.bg_color, font=("Consolas", 12, "bold"), relief="flat", bd=1)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(btn_frame, text="[ STOP ]", command=self.stop_harvest, bg=self.bg_color, fg="red", activebackground="red", activeforeground="white", font=("Consolas", 12, "bold"), relief="flat", bd=1, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        self.music_btn = tk.Button(btn_frame, text="[ ♫ OFF ]", command=self.toggle_music, bg=self.bg_color, fg="#555", font=("Consolas", 10), relief="flat")
        self.music_btn.pack(side="left", padx=5)

        # Log Window
        log_frame = tk.Frame(self.tab_harvest, bg=self.bg_color)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        tk.Label(log_frame, text=":: SYSTEM LOG ::", bg=self.bg_color, fg=self.fg_color, font=self.font_style, anchor="w").pack(fill="x")

        self.log_text = scrolledtext.ScrolledText(log_frame, bg="#050505", fg="#00CC00", font=("Consolas", 9), state="disabled", insertbackground="green")
        self.log_text.pack(fill="both", expand=True)

        # Redirect stdout
        sys.stdout = TextRedirector(self.log_text)
        sys.stderr = TextRedirector(self.log_text, "stderr")
        self.log_text.tag_config("stderr", foreground="red")

    def setup_utils_tab(self):
        # Janitor Section
        janitor_frame = tk.LabelFrame(self.tab_utils, text="[ CANONICAL ASSET JANITOR ]", bg=self.bg_color, fg="#00AAAA", font=("Consolas", 10, "bold"))
        janitor_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Instructions
        tk.Label(janitor_frame, text="Use this tool to merge new aliases into the Canonical Assets list.", bg=self.bg_color, fg="#888", font=("Consolas", 9)).pack(anchor="w", padx=10, pady=5)

        # Terminal Output
        self.janitor_out = scrolledtext.ScrolledText(janitor_frame, bg="#050505", fg="#00AAAA", font=("Consolas", 9), state="disabled", height=15)
        self.janitor_out.pack(fill="both", expand=True, padx=10, pady=5)

        # Input Area
        input_frame = tk.Frame(janitor_frame, bg=self.bg_color)
        input_frame.pack(fill="x", padx=10, pady=10)

        self.janitor_entry = tk.Entry(input_frame, bg="#111", fg="#00AAAA", insertbackground="#00AAAA", font=("Consolas", 10))
        self.janitor_entry.pack(side="left", fill="x", expand=True)
        self.janitor_entry.bind("<Return>", self.send_janitor_input)

        self.janitor_btn = tk.Button(input_frame, text="[ LAUNCH JANITOR ]", command=self.launch_janitor, bg=self.bg_color, fg="#00AAAA", font=("Consolas", 10, "bold"), relief="flat", bd=1)
        self.janitor_btn.pack(side="right", padx=5)

        self.janitor_proc = None
        self.janitor_queue = queue.Queue()

    def launch_janitor(self):
        if self.janitor_proc and self.janitor_proc.poll() is None:
            messagebox.showwarning("Busy", "Janitor is already running.")
            return

        self.janitor_out.configure(state="normal")
        self.janitor_out.delete(1.0, tk.END)
        self.janitor_out.configure(state="disabled")
        
        self.janitor_btn.config(state="disabled", text="[ RUNNING... ]")
        self.janitor_entry.focus()

        # Start Process
        try:
            # -u for unbuffered output
            self.janitor_proc = subprocess.Popen(
                [sys.executable, "-u", "janitor.py"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Start Reader Thread
            threading.Thread(target=self.read_janitor_output, daemon=True).start()
            
        except Exception as e:
            self.append_janitor_text(f"[ERROR] Failed to start Janitor: {e}\n")
            self.janitor_btn.config(state="normal", text="[ LAUNCH JANITOR ]")

    def read_janitor_output(self):
        while True:
            output = self.janitor_proc.stdout.readline()
            if output == '' and self.janitor_proc.poll() is not None:
                break
            if output:
                self.append_janitor_text(output)
        
        # Process finished
        self.append_janitor_text("\n[PROCESS FINISHED]\n")
        self.root.after(0, lambda: self.janitor_btn.config(state="normal", text="[ LAUNCH JANITOR ]"))
        self.janitor_proc = None

    def send_janitor_input(self, event=None):
        if not self.janitor_proc or self.janitor_proc.poll() is not None:
            return
        
        text = self.janitor_entry.get()
        self.janitor_entry.delete(0, tk.END)
        
        self.append_janitor_text(f"> {text}\n")
        
        try:
            self.janitor_proc.stdin.write(text + "\n")
            self.janitor_proc.stdin.flush()
        except Exception as e:
            self.append_janitor_text(f"[ERROR] Failed to send input: {e}\n")

    def append_janitor_text(self, text):
        self.janitor_out.configure(state="normal")
        self.janitor_out.insert(tk.END, text)
        self.janitor_out.see(tk.END)
        self.janitor_out.configure(state="disabled")

    # --- EXISTING METHODS ---
    def update_viz(self):
        self.viz_canvas.delete("all")
        cx, cy = 100, 40
        self.angle_x += 0.02
        self.angle_y += 0.03

        if self.music_on and pygame.mixer.music.get_busy():
            if random.random() < 0.1:
                self.pulse_radius = 45 
        
        self.pulse_radius += (self.base_radius - self.pulse_radius) * 0.1
        cos_x, sin_x = math.cos(self.angle_x), math.sin(self.angle_x)
        cos_y, sin_y = math.cos(self.angle_y), math.sin(self.angle_y)

        for p in self.points:
            x, y, z = p[0], p[1], p[2]
            rx = x * cos_y - z * sin_y
            rz = x * sin_y + z * cos_y
            x = rx
            z = rz
            ry = y * cos_x - z * sin_x
            rz = y * sin_x + z * cos_x
            y = ry
            z = rz
            scale = self.pulse_radius
            factor = 200 / (200 + z * scale) 
            px = cx + x * scale * factor
            py = cy + y * scale * factor
            size = 1.5 if z > 0 else 0.5
            color = self.fg_color if z > 0 else "#005500"
            self.viz_canvas.create_oval(px-size, py-size, px+size, py+size, fill=color, outline="")
        
        self.root.after(33, self.update_viz)

    def load_music(self):
        music_dir = os.path.join(os.getcwd(), "chiptunes")
        if not os.path.exists(music_dir):
            os.makedirs(music_dir)
            return
        for file in os.listdir(music_dir):
            if file.lower().endswith(('.mp3', '.wav', '.ogg')):
                self.playlist.append(os.path.join(music_dir, file))
        random.shuffle(self.playlist)

    def check_music(self):
        if self.music_on and self.audio_available and not pygame.mixer.music.get_busy():
            self.play_next_track()
        self.root.after(1000, self.check_music)

    def play_next_track(self):
        if not self.playlist:
            return
        self.current_track = (self.current_track + 1) % len(self.playlist)
        track = self.playlist[self.current_track]
        try:
            pygame.mixer.music.load(track)
            pygame.mixer.music.play()
            print(f"[AUDIO] NOW PLAYING: {os.path.basename(track)}")
        except Exception as e:
            print(f"[ERROR] Failed to play track: {e}")

    def toggle_music(self):
        if not self.audio_available:
            print("[ERROR] Audio system unavailable.")
            return
        self.music_on = not self.music_on
        if self.music_on:
            self.music_btn.config(text="[ ♫ ON ]", fg=self.fg_color)
            if not pygame.mixer.music.get_busy():
                self.play_next_track()
            else:
                pygame.mixer.music.unpause()
            print("[AUDIO] Music enabled")
        else:
            self.music_btn.config(text="[ ♫ OFF ]", fg="#555")
            pygame.mixer.music.pause()
            print("[AUDIO] Music paused")

    def start_harvest(self):
        if self.is_running:
            return
        try:
            self.limit = int(self.limit_entry.get())
            self.interval = float(self.interval_entry.get())
        except ValueError:
            messagebox.showerror("Input Error", "Invalid numeric values for Limit or Interval.")
            return

        self.is_running = True
        self.stop_event.clear()
        self.start_btn.config(state="disabled", fg="#555")
        self.stop_btn.config(state="normal", fg="red")
        
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()

    def stop_harvest(self):
        if not self.is_running:
            return
        print("[SYSTEM] STOPPING HARVEST AFTER CURRENT CYCLE...")
        self.stop_event.set()
        self.is_running = False
        self.start_btn.config(state="normal", fg=self.fg_color)
        self.stop_btn.config(state="disabled", fg="#555")

    def run_loop(self):
        print(f"[SYSTEM] STARTING HARVEST LOOP. LIMIT={self.limit}, INTERVAL={self.interval}h")
        while not self.stop_event.is_set():
            print(f"\n[SYSTEM] EXECUTING HARVEST CYCLE @ {time.strftime('%H:%M:%S')}...")
            try:
                # Skip consolidation in harvester if GUI will auto-consolidate
                harvester.main(limit=self.limit, skip_consolidation=self.auto_consolidate.get())
            except Exception as e:
                print(f"[ERROR] Harvester crashed: {e}")
            
            if self.auto_consolidate.get() and not self.stop_event.is_set():
                print("[SYSTEM] AUTO-CONSOLIDATING ASSETS...")
                try:
                    consolidator.consolidate()
                    print("[SYSTEM] CONSOLIDATION COMPLETE.")
                except Exception as e:
                    print(f"[ERROR] Auto-consolidation failed: {e}")

            if self.stop_event.is_set():
                break

            print(f"[SYSTEM] CYCLE COMPLETE. SLEEPING FOR {self.interval} HOURS...")
            sleep_seconds = int(self.interval * 3600)
            for _ in range(sleep_seconds):
                if self.stop_event.is_set():
                    break
                time.sleep(1)
        print("[SYSTEM] HARVEST LOOP STOPPED.")

    def run_consolidation(self):
        if self.is_running:
            messagebox.showwarning("Busy", "Cannot consolidate while harvester is running.")
            return
        if messagebox.askyesno("Confirm", "Run Asset Consolidation? This uses Gemini API calls."):
            print("[SYSTEM] STARTING ASSET CONSOLIDATION...")
            threading.Thread(target=self._consolidation_worker, daemon=True).start()

    def _consolidation_worker(self):
        try:
            consolidator.consolidate()
            print("[SYSTEM] CONSOLIDATION COMPLETE.")
            messagebox.showinfo("Success", "Assets Consolidated.")
        except Exception as e:
            print(f"[ERROR] Consolidation failed: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = HarvesterGUI(root)
    root.mainloop()
