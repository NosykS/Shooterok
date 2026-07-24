# tools/generate_sounds.py
"""
Одноразовий скрипт для процедурної генерації простих ретро звукових ефектів
(у дусі Duke Nukem 3D — короткі, "хрусткі" 8/16-бітні семпли) та фонової музики
для гри. Не використовує сторонніх залежностей (лише стандартна бібліотека),
щоб не додавати нових пакетів у requirements.txt.

Запуск: python tools/generate_sounds.py
Результат: assets/sounds/*.wav
"""
import math
import os
import random
import struct
import wave

SAMPLE_RATE = 22050
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "sounds")

NOTE_FREQS = {
    "F3": 174.61, "G3": 196.00, "A3": 220.00, "B3": 246.94,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00,
    "A4": 440.00, "B4": 493.88, "C5": 523.25, "E5": 659.25, "G5": 783.99,
}


# --- Базові будівельні блоки синтезу ---

def silence(duration):
    return [0.0] * int(SAMPLE_RATE * duration)


def noise_burst(duration, decay=8.0, amp=1.0, seed=None):
    """Шум з експоненційним загасанням — основа для пострілів/ударів."""
    n = int(SAMPLE_RATE * duration)
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        env = math.exp(-decay * t)
        out.append(rnd.uniform(-1.0, 1.0) * env * amp)
    return out


def tone(freq, duration, wave_type="sine", amp=1.0, decay=0.0, freq_end=None):
    """Простий тон (sine/square/saw) з опційним загасанням та зміною частоти (glide)."""
    n = int(SAMPLE_RATE * duration)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        f = freq if freq_end is None else freq + (freq_end - freq) * (t / duration)
        phase = 2 * math.pi * f * t
        if wave_type == "square":
            s = 1.0 if math.sin(phase) >= 0 else -1.0
        elif wave_type == "saw":
            s = 2 * ((f * t) % 1) - 1
        else:
            s = math.sin(phase)
        env = math.exp(-decay * t) if decay else 1.0
        out.append(s * amp * env)
    return out


def mix(*tracks):
    length = max(len(t) for t in tracks)
    out = [0.0] * length
    for track in tracks:
        for i, v in enumerate(track):
            out[i] += v
    return out


def concat(*tracks):
    out = []
    for t in tracks:
        out.extend(t)
    return out


def apply_fade_out(samples, fade_duration=0.02):
    n = min(int(SAMPLE_RATE * fade_duration), len(samples))
    for i in range(n):
        samples[-(i + 1)] *= (1 - i / n)
    return samples


def normalize(samples, peak=0.9):
    m = max((abs(s) for s in samples), default=0)
    if m == 0:
        return samples
    factor = peak / m
    return [s * factor for s in samples]


def write_wav(rel_path, samples):
    path = os.path.join(OUT_DIR, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    clamped = [max(-1.0, min(1.0, s)) for s in samples]
    frames = b"".join(struct.pack("<h", int(s * 32767)) for s in clamped)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(frames)
    print(f"[OK] {rel_path} ({len(samples) / SAMPLE_RATE:.2f}s)")


def make_note(name, duration, wave_type="square", amp=0.35, decay=3.5):
    return tone(NOTE_FREQS[name], duration, wave_type, amp=amp, decay=decay)


# --- Звуки зброї ---

def make_pistol_silenced():
    n = noise_burst(0.10, decay=35, amp=0.6, seed=1)
    t = tone(150, 0.08, "sine", amp=0.35, decay=20)
    return normalize(apply_fade_out(mix(n, t), 0.02), 0.7)


def make_rifle():
    n1 = noise_burst(0.06, decay=25, amp=1.0, seed=2)
    crack = tone(90, 0.05, "square", amp=0.5, decay=30)
    tail = noise_burst(0.12, decay=12, amp=0.3, seed=3)
    return normalize(apply_fade_out(mix(n1, crack, tail), 0.03), 0.95)


def make_shotgun():
    n1 = noise_burst(0.18, decay=9, amp=1.0, seed=4)
    boom = tone(70, 0.15, "sine", amp=0.6, decay=10)
    boom2 = tone(55, 0.20, "square", amp=0.25, decay=8)
    return normalize(apply_fade_out(mix(n1, boom, boom2), 0.04), 1.0)


def make_knife():
    swish = noise_burst(0.12, decay=15, amp=0.5, seed=5)
    for i in range(len(swish)):
        t = i / SAMPLE_RATE
        mod = 0.5 + 0.5 * math.sin(2 * math.pi * (6 + 20 * t) * t)
        swish[i] *= mod
    thud = mix(
        tone(110, 0.06, "sine", amp=0.5, decay=25),
        noise_burst(0.05, decay=40, amp=0.4, seed=6),
    )
    return normalize(apply_fade_out(concat(swish, thud), 0.02), 0.8)


# --- Смерть гравця / ворога ---

def make_player_death():
    groan = mix(
        tone(220, 0.5, "square", amp=0.35, decay=2.5, freq_end=80),
        tone(180, 0.5, "sine", amp=0.30, decay=2.0, freq_end=60),
        noise_burst(0.5, decay=4, amp=0.25, seed=7),
    )
    thud = tone(60, 0.3, "sine", amp=0.4, decay=6)
    return normalize(apply_fade_out(concat(groan, thud), 0.05), 0.9)


def make_enemy_death():
    bark = mix(
        tone(320, 0.25, "square", amp=0.4, decay=6, freq_end=140),
        noise_burst(0.2, decay=12, amp=0.3, seed=8),
    )
    return normalize(apply_fade_out(bark, 0.03), 0.85)


# --- Кроки ---

def make_footstep(freq, seed):
    thud = mix(
        tone(freq, 0.07, "sine", amp=0.5, decay=35),
        noise_burst(0.05, decay=45, amp=0.25, seed=seed),
    )
    return normalize(apply_fade_out(thud, 0.01), 0.5)


# --- Мелодії програшу / перемоги ---

def make_defeat_jingle():
    seq = [("E4", 0.28), ("D4", 0.28), ("C4", 0.28), ("B3", 0.28), ("A3", 0.5), ("F3", 0.9)]
    parts = []
    for name, dur in seq:
        parts.append(make_note(name, dur, "square", amp=0.35, decay=4.5))
        parts.append(silence(0.02))
    return normalize(apply_fade_out(concat(*parts), 0.08), 0.8)


def make_victory_jingle():
    seq = [("C4", 0.12), ("E4", 0.12), ("G4", 0.12), ("C5", 0.12), ("E5", 0.12)]
    parts = []
    for name, dur in seq:
        parts.append(make_note(name, dur, "square", amp=0.3, decay=3.0))
        parts.append(silence(0.015))
    chord = mix(
        make_note("C5", 0.6, "square", amp=0.2, decay=2.0),
        make_note("E5", 0.6, "square", amp=0.2, decay=2.0),
        make_note("G5", 0.6, "square", amp=0.2, decay=2.0),
    )
    return normalize(apply_fade_out(concat(*parts, chord), 0.08), 0.85)


# --- Фонова музика (безшовний луп) ---

def make_ambient_loop(duration=8.0):
    n = int(SAMPLE_RATE * duration)
    out = [0.0] * n

    # Частоти підібрані кратними 1/duration Гц, щоб луп замикався без клацання
    pad_freqs = [110.0, 132.0, 165.0]

    for i in range(n):
        t = i / SAMPLE_RATE
        lfo = 0.5 + 0.5 * math.sin(2 * math.pi * (1.0 / duration) * t)
        val = sum(math.sin(2 * math.pi * f * t) * 0.12 for f in pad_freqs)
        out[i] = val * (0.4 + 0.6 * lfo)

    for pos in (0.5, 2.5, 4.5, 6.5):
        pulse = tone(65, 0.35, "sine", amp=0.3, decay=6)
        start = int(pos * SAMPLE_RATE)
        for j, v in enumerate(pulse):
            idx = start + j
            if idx < n:
                out[idx] += v

    return normalize(out, 0.5)


def main():
    write_wav("weapons/knife.wav", make_knife())
    write_wav("weapons/pistol_silenced.wav", make_pistol_silenced())
    write_wav("weapons/rifle.wav", make_rifle())
    write_wav("weapons/shotgun.wav", make_shotgun())

    write_wav("player_death.wav", make_player_death())
    write_wav("enemy_death.wav", make_enemy_death())

    write_wav("footstep1.wav", make_footstep(95, seed=9))
    write_wav("footstep2.wav", make_footstep(80, seed=10))

    write_wav("defeat_jingle.wav", make_defeat_jingle())
    write_wav("victory_jingle.wav", make_victory_jingle())

    write_wav("music_ambient.wav", make_ambient_loop())

    print("\nГотово! Усі звуки згенеровано в assets/sounds/")


if __name__ == "__main__":
    main()
