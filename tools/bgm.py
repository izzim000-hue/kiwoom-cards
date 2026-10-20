"""키움멘토 릴스용 자체 제작 배경음 (저작권 걱정 없는 합성음, 잔잔한 피아노 + 패드, 80 BPM)
사용: python3 tools/bgm.py 입력.mp4 출력.mp4 [강조_시작초]
강조_시작초부터 높은 음 멜로디가 더해짐 (예: 복리 차이 장면). 영상 길이에 맞춰 만들고 끝 2.5초는 페이드아웃.
"""
import sys, subprocess, wave
import numpy as np
SR = 44100; BPM = 80; BEAT = 60 / BPM
# Cmaj7 - Am7 - Fmaj7 - G6, 한 코드당 2마디(8박)
CHORDS = [[48, 55, 59, 64], [45, 52, 55, 60], [41, 48, 52, 57], [43, 50, 55, 59]]
MELODY = [76, 74, 72, 71, 72, 74, 76, 79]  # 강조 구간 높은 음

def hz(m): return 440 * 2 ** ((m - 69) / 12)

def piano(m, dur, vel):
    t = np.arange(int(SR * dur)) / SR; f = hz(m)
    tone = sum(a * np.sin(2 * np.pi * f * k * t) for k, a in [(1, 1), (2, .45), (3, .18), (4, .08)])
    env = np.exp(-t * (2.2 + m / 40)) * (1 - np.exp(-t * 300))
    return vel * tone * env

def pad(ms, dur):
    t = np.arange(int(SR * dur)) / SR
    s = sum(np.sin(2 * np.pi * hz(m) * d * t) for m in ms for d in (0.997, 1.003))
    env = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.2)
    return 0.05 * s * env

def add(buf, x, at):
    i = int(at * SR); n = min(len(x), len(buf) - i)
    if n > 0: buf[i:i + n] += x[:n]

def make(length, lift):
    buf = np.zeros(int(SR * (length + 3)))
    bar = 8 * BEAT; c = 0; t = 0.0
    while t < length:
        ch = CHORDS[c % 4]
        add(buf, pad(ch[1:], bar + 0.6), t)
        add(buf, piano(ch[0] - 12, 3.0, .35), t)
        for k in range(16):  # 8분음표 아르페지오
            note = ch[[1, 2, 3, 2][k % 4]] + (12 if k % 8 >= 4 else 0)
            add(buf, piano(note, 1.6, .16 if k % 2 else .22), t + k * BEAT / 2)
        if t + bar > lift:
            for k, m in enumerate(MELODY):
                at = t + k * BEAT
                if at >= lift: add(buf, piano(m, 2.0, .14), at)
        t += bar; c += 1
    ir_t = np.arange(int(SR * 1.8)) / SR  # 간단한 잔향
    ir = np.random.default_rng(7).standard_normal(len(ir_t)) * np.exp(-ir_t * 3.2) * .02; ir[0] = 1
    n = len(buf) + len(ir)
    buf = np.fft.irfft(np.fft.rfft(buf, n) * np.fft.rfft(ir, n), n)[:int(SR * length)]
    tt = np.arange(len(buf)) / SR
    buf *= np.minimum(1, tt / 1.0) * np.clip((length - tt) / 2.5, 0, 1)
    return (buf / np.abs(buf).max() * 0.9 * 32767).astype(np.int16)

def main(src, out, lift=1e9):
    length = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src],
                                  capture_output=True, text=True, check=True).stdout)
    pcm = make(length, float(lift)); w = out + ".wav"
    with wave.open(w, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-i", w, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-shortest", "-movflags", "+faststart", out], check=True)
    print(f"bgm {length:.1f}s -> {out}")

if __name__ == "__main__": main(*sys.argv[1:])
