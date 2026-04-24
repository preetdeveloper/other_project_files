import os
import threading
from tkinter import filedialog

import customtkinter as ctk
import librosa
import matplotlib.pyplot as plt
import numpy as np
import sounddevice as sd
import soundfile as sf
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

NOTE_TO_PC = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}

SCALES = {
    "None": None,
    "C Major": [0, 2, 4, 5, 7, 9, 11],
    "A Minor": [0, 2, 3, 5, 7, 8, 10],
    "G Major": [0, 2, 4, 6, 7, 9, 11],
    "D Major": [0, 2, 4, 5, 7, 9, 11],
    "Chromatic": list(range(12)),
}

# Auto-save folder
AUTOSAVE_DIR = os.path.join(os.path.expanduser("~"), "VocalTune_AutoSave")
os.makedirs(AUTOSAVE_DIR, exist_ok=True)


class VocalTune(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VocalTune - Pitch Correction")
        self.geometry("980x780")
        self.resizable(True, True)

        self.audio_data = None
        self.sample_rate = None
        self.corrected_audio = None
        self.recording = False
        self.processing = False
        self.live_stream = None
        self.live_monitoring = False

        # Auto-save settings
        self.autosave_enabled = True
        self.autosave_counter = 0
        self.current_source_name = "recording"

        self.build_ui()

    def build_ui(self):
        title = ctk.CTkLabel(self, text="VocalTune", font=ctk.CTkFont(size=28, weight="bold"))
        title.pack(pady=10)

        # === TOP BUTTONS ===
        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(pady=5, padx=20, fill="x")

        self.load_btn = ctk.CTkButton(btn_frame, text="Load Audio", command=self.load_audio, width=130)
        self.load_btn.grid(row=0, column=0, padx=8, pady=10)

        self.record_btn = ctk.CTkButton(btn_frame, text="Record", command=self.toggle_record, width=110, fg_color="red")
        self.record_btn.grid(row=0, column=1, padx=8, pady=10)

        self.live_btn = ctk.CTkButton(btn_frame, text="Live Monitor", command=self.toggle_live_monitor, width=120, fg_color="#1f6aa5")
        self.live_btn.grid(row=0, column=2, padx=8, pady=10)

        self.play_original_btn = ctk.CTkButton(btn_frame, text="Play Original", command=self.play_original, width=120)
        self.play_original_btn.grid(row=0, column=3, padx=8, pady=10)

        self.apply_btn = ctk.CTkButton(btn_frame, text="Apply AutoTune", command=self.apply_autotune, width=130, fg_color="green")
        self.apply_btn.grid(row=0, column=4, padx=8, pady=10)

        self.play_corrected_btn = ctk.CTkButton(btn_frame, text="Play Corrected", command=self.play_corrected, width=120)
        self.play_corrected_btn.grid(row=0, column=5, padx=8, pady=10)

        self.save_btn = ctk.CTkButton(btn_frame, text="Save WAV", command=self.save_audio, width=110)
        self.save_btn.grid(row=0, column=6, padx=8, pady=10)

        # === CONTROLS ===
        controls = ctk.CTkFrame(self)
        controls.pack(pady=10, padx=20, fill="x")

        ctk.CTkLabel(controls, text="Pitch Shift (semitones):", font=ctk.CTkFont(size=13)).grid(row=0, column=0, padx=10, pady=5)
        self.pitch_slider = ctk.CTkSlider(controls, from_=-12, to=12, number_of_steps=48, width=220, command=self.update_labels)
        self.pitch_slider.set(0)
        self.pitch_slider.grid(row=0, column=1, padx=10)
        self.pitch_label = ctk.CTkLabel(controls, text="0.0")
        self.pitch_label.grid(row=0, column=2, padx=5)

        ctk.CTkLabel(controls, text="Retune Speed:", font=ctk.CTkFont(size=13)).grid(row=1, column=0, padx=10, pady=5)
        self.retune_slider = ctk.CTkSlider(controls, from_=0.1, to=3.0, number_of_steps=29, width=220, command=self.update_labels)
        self.retune_slider.set(1.0)
        self.retune_slider.grid(row=1, column=1, padx=10)
        self.retune_label = ctk.CTkLabel(controls, text="1.0")
        self.retune_label.grid(row=1, column=2, padx=5)

        ctk.CTkLabel(controls, text="Formant Shift:", font=ctk.CTkFont(size=13)).grid(row=2, column=0, padx=10, pady=5)
        self.formant_slider = ctk.CTkSlider(controls, from_=-5, to=5, number_of_steps=20, width=220, command=self.update_labels)
        self.formant_slider.set(0)
        self.formant_slider.grid(row=2, column=1, padx=10)
        self.formant_label = ctk.CTkLabel(controls, text="0.0")
        self.formant_label.grid(row=2, column=2, padx=5)

        ctk.CTkLabel(controls, text="Scale:", font=ctk.CTkFont(size=13)).grid(row=0, column=3, padx=10)
        self.scale_menu = ctk.CTkOptionMenu(controls, values=list(SCALES.keys()), width=160)
        self.scale_menu.set("None")
        self.scale_menu.grid(row=0, column=4, padx=10)

        ctk.CTkLabel(controls, text="Live Level:", font=ctk.CTkFont(size=13)).grid(row=1, column=3, padx=10)
        self.live_gain_slider = ctk.CTkSlider(controls, from_=0.0, to=2.0, number_of_steps=40, width=160)
        self.live_gain_slider.set(1.0)
        self.live_gain_slider.grid(row=1, column=4, padx=10)

        ctk.CTkLabel(controls, text="Theme:", font=ctk.CTkFont(size=13)).grid(row=2, column=3, padx=10)
        self.theme_menu = ctk.CTkOptionMenu(controls, values=["dark", "light", "system"], command=self.change_theme, width=160)
        self.theme_menu.set("dark")
        self.theme_menu.grid(row=2, column=4, padx=10)

        self.stop_btn = ctk.CTkButton(controls, text="Stop", command=self.stop_audio, fg_color="gray", width=100)
        self.stop_btn.grid(row=0, column=5, rowspan=3, padx=12, pady=5)

        # === VOICE GENDER FRAME ===
        gender_frame = ctk.CTkFrame(self)
        gender_frame.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(gender_frame, text="Voice Preset:", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=8)

        self.male_btn = ctk.CTkButton(gender_frame, text="Male Voice", command=self.set_male_voice, width=130, fg_color="#2d6a9f")
        self.male_btn.grid(row=0, column=1, padx=10, pady=8)

        self.neutral_btn = ctk.CTkButton(gender_frame, text="Neutral", command=self.set_neutral_voice, width=130, fg_color="#555555")
        self.neutral_btn.grid(row=0, column=2, padx=10, pady=8)

        self.female_btn = ctk.CTkButton(gender_frame, text="Female Voice", command=self.set_female_voice, width=130, fg_color="#9b4dca")
        self.female_btn.grid(row=0, column=3, padx=10, pady=8)

        self.child_btn = ctk.CTkButton(gender_frame, text="Child Voice", command=self.set_child_voice, width=130, fg_color="#e07b39")
        self.child_btn.grid(row=0, column=4, padx=10, pady=8)

        self.voice_label = ctk.CTkLabel(gender_frame, text="Current: Neutral", font=ctk.CTkFont(size=12), text_color="gray")
        self.voice_label.grid(row=0, column=5, padx=15)

        # === AUTO-SAVE FRAME ===
        autosave_frame = ctk.CTkFrame(self)
        autosave_frame.pack(pady=5, padx=20, fill="x")

        ctk.CTkLabel(autosave_frame, text="Auto-Save:", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, padx=15, pady=8)

        self.autosave_switch = ctk.CTkSwitch(autosave_frame, text="Enabled", command=self.toggle_autosave)
        self.autosave_switch.select()
        self.autosave_switch.grid(row=0, column=1, padx=10)

        self.autosave_path_label = ctk.CTkLabel(autosave_frame, text=f"Folder: {AUTOSAVE_DIR}", font=ctk.CTkFont(size=11), text_color="gray")
        self.autosave_path_label.grid(row=0, column=2, padx=15)

        self.open_folder_btn = ctk.CTkButton(autosave_frame, text="Open Folder", command=self.open_autosave_folder, width=120)
        self.open_folder_btn.grid(row=0, column=3, padx=10)

        self.autosave_status = ctk.CTkLabel(autosave_frame, text="No auto-save yet", font=ctk.CTkFont(size=11), text_color="gray")
        self.autosave_status.grid(row=0, column=4, padx=15)

        # === WAVEFORM ===
        self.fig, self.ax = plt.subplots(figsize=(8, 2.4), facecolor="#1a1a2e")
        self.ax.set_facecolor("#1a1a2e")
        self.ax.set_title("Waveform", color="white")
        self.ax.tick_params(colors="white")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(padx=20, pady=5, fill="x")

        self.status_label = ctk.CTkLabel(self, text="Status: Ready", font=ctk.CTkFont(size=12), text_color="gray")
        self.status_label.pack(pady=5)

    # === VOICE PRESETS ===
    def set_male_voice(self):
        self.pitch_slider.set(-3)
        self.formant_slider.set(-2)
        self.update_labels()
        self.voice_label.configure(text="Current: Male")
        self.set_status("Male voice preset applied.")

    def set_female_voice(self):
        self.pitch_slider.set(4)
        self.formant_slider.set(3)
        self.update_labels()
        self.voice_label.configure(text="Current: Female")
        self.set_status("Female voice preset applied.")

    def set_child_voice(self):
        self.pitch_slider.set(7)
        self.formant_slider.set(4)
        self.update_labels()
        self.voice_label.configure(text="Current: Child")
        self.set_status("Child voice preset applied.")

    def set_neutral_voice(self):
        self.pitch_slider.set(0)
        self.formant_slider.set(0)
        self.update_labels()
        self.voice_label.configure(text="Current: Neutral")
        self.set_status("Neutral preset applied.")

    # === AUTO-SAVE ===
    def toggle_autosave(self):
        self.autosave_enabled = self.autosave_switch.get()
        state = "ON" if self.autosave_enabled else "OFF"
        self.set_status(f"Auto-save {state}.")

    def open_autosave_folder(self):
        os.startfile(AUTOSAVE_DIR)

    def do_autosave(self, audio):
        if not self.autosave_enabled:
            return
        try:
            self.autosave_counter += 1
            filename = f"{self.current_source_name}_autosave_{self.autosave_counter:03d}.wav"
            path = os.path.join(AUTOSAVE_DIR, filename)
            sf.write(path, audio, self.sample_rate)
            self.on_ui(self.autosave_status.configure, text=f"Auto-saved: {filename}")
        except Exception as exc:
            self.on_ui(self.autosave_status.configure, text=f"Auto-save error: {exc}")

    # === HELPERS ===
    def on_ui(self, fn, *args, **kwargs):
        self.after(0, lambda: fn(*args, **kwargs))

    def update_labels(self, _val=None):
        self.pitch_label.configure(text=f"{self.pitch_slider.get():.1f}")
        self.retune_label.configure(text=f"{self.retune_slider.get():.1f}")
        self.formant_label.configure(text=f"{self.formant_slider.get():.1f}")

    def change_theme(self, theme):
        ctk.set_appearance_mode(theme)

    def set_status(self, msg):
        self.on_ui(self.status_label.configure, text=f"Status: {msg}")

    def set_apply_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.on_ui(self.apply_btn.configure, state=state)

    def load_audio(self):
        path = filedialog.askopenfilename(
            filetypes=[("Audio files", "*.wav *.mp3 *.flac *.ogg *.m4a"), ("WAV files", "*.wav")]
        )
        if not path:
            return
        try:
            audio, sr = librosa.load(path, sr=None, mono=True)
            self.audio_data = audio.astype(np.float32)
            self.sample_rate = int(sr)
            self.corrected_audio = None
            self.current_source_name = os.path.splitext(os.path.basename(path))[0]
            self.set_status(f"Loaded: {os.path.basename(path)}")
            self.draw_waveform(self.audio_data, "Original Waveform")
        except Exception as exc:
            self.set_status(f"Load error: {exc}")

    def draw_waveform(self, audio, title="Waveform"):
        audio = np.asarray(audio)
        def _draw():
            self.ax.clear()
            self.ax.set_facecolor("#1a1a2e")
            idx = np.linspace(0, audio.size - 1, min(30000, audio.size), dtype=int)
            self.ax.plot(audio[idx], color="#00bfff", linewidth=0.5)
            self.ax.set_title(title, color="white")
            self.ax.tick_params(colors="white")
            self.canvas.draw()
        self.on_ui(_draw)

    def toggle_record(self):
        if not self.recording:
            self.recording = True
            self.record_btn.configure(text="Stop Recording", fg_color="gray")
            self.set_status("Recording...")
            threading.Thread(target=self.record_audio, daemon=True).start()
        else:
            self.recording = False
            self.record_btn.configure(text="Record", fg_color="red")
            self.set_status("Recording stopped.")

    def record_audio(self):
        recorded = []
        sr = 44100
        try:
            with sd.InputStream(samplerate=sr, channels=1, dtype="float32") as stream:
                while self.recording:
                    data, _ = stream.read(1024)
                    recorded.append(data.copy())
        except Exception as exc:
            self.recording = False
            self.on_ui(self.record_btn.configure, text="Record", fg_color="red")
            self.set_status(f"Record error: {exc}")
            return

        if recorded:
            self.audio_data = np.concatenate(recorded).flatten().astype(np.float32)
            self.sample_rate = sr
            self.corrected_audio = None
            self.current_source_name = "recording"
            self.draw_waveform(self.audio_data, "Recorded Waveform")
            # Auto-save original recording too
            self.do_autosave(self.audio_data)
            self.set_status("Recording saved.")

    def toggle_live_monitor(self):
        if self.live_monitoring:
            self.stop_live_monitor()
        else:
            self.start_live_monitor()

    def start_live_monitor(self):
        if self.processing:
            self.set_status("Wait for processing to finish.")
            return
        try:
            self.live_stream = sd.Stream(
                samplerate=44100, channels=1, dtype="float32",
                callback=self._live_callback, blocksize=1024, latency="low"
            )
            self.live_stream.start()
            self.live_monitoring = True
            self.live_btn.configure(text="Stop Live", fg_color="gray")
            self.set_status("Live monitor ON.")
        except Exception as exc:
            self.live_stream = None
            self.live_monitoring = False
            self.set_status(f"Live monitor error: {exc}")

    def stop_live_monitor(self):
        if self.live_stream:
            try:
                self.live_stream.stop()
                self.live_stream.close()
            except Exception:
                pass
        self.live_stream = None
        self.live_monitoring = False
        self.live_btn.configure(text="Live Monitor", fg_color="#1f6aa5")
        self.set_status("Live monitor OFF.")

    def _live_callback(self, indata, outdata, _frames, _time, _status):
        gain = float(self.live_gain_slider.get())
        outdata[:] = np.clip(indata * gain, -1.0, 1.0)

    def apply_autotune(self):
        if self.audio_data is None:
            self.set_status("Load or record audio first.")
            return
        if self.processing:
            self.set_status("Already processing...")
            return
        self.processing = True
        self.set_apply_enabled(False)
        self.set_status("Applying AutoTune...")
        threading.Thread(target=self._process, daemon=True).start()

    def _scale_shift_estimate(self, y, sr, scale_name):
        if scale_name == "None":
            return 0.0
        allowed = SCALES.get(scale_name)
        if not allowed:
            return 0.0
        root = scale_name.split()[0]
        root_pc = NOTE_TO_PC.get(root, 0)
        target_pitch_classes = {(root_pc + interval) % 12 for interval in allowed}
        f0 = librosa.yin(y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"),
                         sr=sr, frame_length=2048, hop_length=512)
        voiced = np.isfinite(f0) & (f0 > 0)
        if not np.any(voiced):
            return 0.0
        midi = librosa.hz_to_midi(f0[voiced])
        rounded = np.round(midi)
        diffs = []
        for note in rounded:
            candidates = []
            base = int(note)
            for octave_shift in (-12, 0, 12):
                candidate_base = base + octave_shift
                for n in range(candidate_base - 12, candidate_base + 13):
                    if (n % 12) in target_pitch_classes:
                        candidates.append(n)
            if not candidates:
                continue
            nearest = min(candidates, key=lambda n: abs(n - note))
            diffs.append(nearest - note)
        if not diffs:
            return 0.0
        return float(np.median(diffs))

    def _process(self):
        try:
            y = self.audio_data.astype(np.float32)
            sr = int(self.sample_rate)
            manual_shift = float(self.pitch_slider.get())
            retune_speed = float(self.retune_slider.get())
            formant = float(self.formant_slider.get())
            scale_name = self.scale_menu.get()

            auto_shift = self._scale_shift_estimate(y, sr, scale_name)
            retune_mix = np.clip((retune_speed - 0.1) / (3.0 - 0.1), 0.0, 1.0)
            total_shift = manual_shift + (auto_shift * retune_mix)

            corrected = librosa.effects.pitch_shift(y, sr=sr, n_steps=total_shift)

            if formant != 0:
                corrected = librosa.effects.pitch_shift(corrected, sr=sr, n_steps=formant * 0.35)

            self.corrected_audio = np.clip(corrected, -1.0, 1.0).astype(np.float32)
            self.draw_waveform(self.corrected_audio, "Corrected Waveform")

            # AUTO-SAVE after every apply
            threading.Thread(target=self.do_autosave, args=(self.corrected_audio,), daemon=True).start()

            self.set_status(
                f"Done. Shift {total_shift:+.2f} st (manual {manual_shift:+.2f}, scale {auto_shift:+.2f} x {retune_mix:.2f})"
            )
        except Exception as exc:
            self.set_status(f"Process error: {exc}")
        finally:
            self.processing = False
            self.set_apply_enabled(True)

    def play_original(self):
        if self.audio_data is None:
            self.set_status("No audio loaded.")
            return
        try:
            sd.stop()
            threading.Thread(target=lambda: sd.play(self.audio_data, self.sample_rate), daemon=True).start()
            self.set_status("Playing original...")
        except Exception as exc:
            self.set_status(f"Play error: {exc}")

    def play_corrected(self):
        if self.corrected_audio is None:
            self.set_status("No corrected audio yet.")
            return
        try:
            sd.stop()
            threading.Thread(target=lambda: sd.play(self.corrected_audio, self.sample_rate), daemon=True).start()
            self.set_status("Playing corrected...")
        except Exception as exc:
            self.set_status(f"Play error: {exc}")

    def stop_audio(self):
        sd.stop()
        self.stop_live_monitor()
        self.set_status("Stopped.")

    def save_audio(self):
        if self.corrected_audio is None:
            self.set_status("Nothing to save yet.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
        if not path:
            return
        try:
            sf.write(path, self.corrected_audio, self.sample_rate)
            self.set_status(f"Saved: {os.path.basename(path)}")
        except Exception as exc:
            self.set_status(f"Save error: {exc}")

    def on_close(self):
        self.recording = False
        self.stop_audio()
        self.destroy()


if __name__ == "__main__":
    app = VocalTune()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()