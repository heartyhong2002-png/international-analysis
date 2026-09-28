"""Create time-aligned, inspectable signals for a video that may be analyzed locally.

The program intentionally does not fetch from YouTube.  Give it a local media file or
an authorized/public-domain media URL, plus an SRT subtitle file or URL.  It produces
JSON consumed by the UNGA Speech Lens prototype.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
import urllib.request
import wave
from pathlib import Path

import numpy as np


def command_output(command: list[str], *, binary: bool = False) -> bytes | str:
    result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout if binary else result.stdout.decode("utf-8", errors="replace")


def probe_media(source: str) -> dict:
    raw = command_output(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height", "-of", "json", source])
    payload = json.loads(raw)
    video_stream = next((item for item in payload.get("streams", []) if item.get("width")), {})
    return {
        "duration": float(payload["format"]["duration"]),
        "width": int(video_stream.get("width", 160)),
        "height": int(video_stream.get("height", 90)),
    }


def read_text(path_or_url: str) -> str:
    if path_or_url.startswith(("https://", "http://")):
        request = urllib.request.Request(path_or_url, headers={"User-Agent": "International-Analysis-Prototype/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read().decode("utf-8-sig", errors="replace")
    return Path(path_or_url).read_text(encoding="utf-8-sig")


def srt_time(value: str) -> float:
    hours, minutes, seconds = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_srt(path_or_url: str, duration: float) -> list[dict]:
    source = read_text(path_or_url).replace("\r\n", "\n")
    blocks = re.split(r"\n\s*\n", source.strip())
    segments: list[dict] = []
    for block in blocks:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if len(lines) < 3 or "-->" not in lines[1]:
            continue
        start_raw, end_raw = (part.strip() for part in lines[1].split("-->"))
        start, end = srt_time(start_raw), srt_time(end_raw)
        if start >= duration:
            continue
        text = re.sub(r"<[^>]+>", "", " ".join(lines[2:]))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            segments.append({"start": round(start, 3), "end": round(min(end, duration), 3), "text": text})
    return segments


def estimate_pitch(frame: np.ndarray, rate: int) -> float | None:
    frame = frame.astype(np.float32)
    frame -= frame.mean()
    if len(frame) < 1024 or np.sqrt(np.mean(frame * frame)) < 0.008:
        return None
    frame *= np.hanning(len(frame))
    fft_size = 1 << math.ceil(math.log2(len(frame) * 2))
    autocorrelation = np.fft.irfft(np.abs(np.fft.rfft(frame, fft_size)) ** 2)[: len(frame)]
    low_lag, high_lag = max(1, int(rate / 350)), min(len(frame) - 1, int(rate / 75))
    if high_lag <= low_lag:
        return None
    section = autocorrelation[low_lag : high_lag + 1]
    lag = low_lag + int(np.argmax(section))
    if autocorrelation[lag] / max(autocorrelation[0], 1e-9) < 0.18:
        return None
    return round(rate / lag, 1)


def audio_features(source: str, seconds: float, work: Path) -> list[dict]:
    audio_path = work / "audio.wav"
    command_output([
        "ffmpeg", "-y", "-v", "error", "-t", str(seconds), "-i", source,
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio_path),
    ])
    with wave.open(str(audio_path), "rb") as audio:
        rate = audio.getframerate()
        values = np.frombuffer(audio.readframes(audio.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    samples: list[dict] = []
    step = rate
    for index, offset in enumerate(range(0, len(values), step)):
        chunk = values[offset : offset + step]
        if not len(chunk):
            continue
        center = chunk[max(0, len(chunk) // 2 - 2048) : len(chunk) // 2 + 2048]
        samples.append({
            "time": index,
            "rms": float(np.sqrt(np.mean(chunk * chunk))),
            "pitch_hz": estimate_pitch(center, rate),
        })
    rms_values = np.array([item["rms"] for item in samples], dtype=float)
    rms_reference = float(np.percentile(rms_values, 95)) if len(rms_values) else 1.0
    previous_pitch: float | None = None
    for item in samples:
        pitch = item["pitch_hz"]
        pitch_change = 0.0 if pitch is None or previous_pitch is None else min(100.0, abs(pitch - previous_pitch) / 0.7)
        loudness = min(100.0, item["rms"] / max(rms_reference, 1e-6) * 100)
        item["voice_signal"] = round(0.58 * pitch_change + 0.42 * loudness, 1)
        if pitch is not None:
            previous_pitch = pitch
        item["rms"] = round(item["rms"], 5)
    return samples


def visual_motion(source: str, seconds: float, width: int, height: int) -> list[float]:
    scaled_height = max(2, round((height * 160 / width) / 2) * 2)
    raw = command_output([
        "ffmpeg", "-v", "error", "-t", str(seconds), "-i", source,
        "-vf", f"fps=1,scale=160:{scaled_height},format=gray", "-f", "rawvideo", "-",
    ], binary=True)
    frame_size = 160 * scaled_height
    frames = np.frombuffer(raw, dtype=np.uint8)
    frame_count = len(frames) // frame_size
    if frame_count < 2:
        return [0.0] * max(1, frame_count)
    frames = frames[: frame_count * frame_size].reshape(frame_count, frame_size).astype(np.int16)
    motion = np.mean(np.abs(np.diff(frames, axis=0)), axis=1) / 255.0
    reference = max(float(np.percentile(motion, 95)), 1e-6)
    return [0.0] + [round(min(100.0, value / reference * 100), 1) for value in motion]


def add_speech_rate(segments: list[dict], duration: float) -> float:
    words = sum(len(re.findall(r"[A-Za-z0-9']+", segment["text"])) for segment in segments)
    return round(words / max(duration, 1) * 60, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create prototype data from authorized local/public-domain video.")
    parser.add_argument("--video", required=True, help="Local path or authorized/public-domain media URL")
    parser.add_argument("--subtitles", required=True, help="SRT path or URL with time-coded subtitles")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--title", required=True)
    parser.add_argument("--source-url", required=True, help="Canonical public source page URL")
    parser.add_argument("--max-seconds", type=float, default=180, help="Analyze only the first N seconds (default: 180)")
    args = parser.parse_args()

    metadata = probe_media(args.video)
    duration = min(metadata["duration"], args.max_seconds)
    with tempfile.TemporaryDirectory(prefix="speech-lens-") as folder:
        work = Path(folder)
        samples = audio_features(args.video, duration, work)
        motion = visual_motion(args.video, duration, metadata["width"], metadata["height"])
    for index, sample in enumerate(samples):
        sample["visual_motion"] = motion[min(index, len(motion) - 1)] if motion else 0.0
    subtitles = parse_srt(args.subtitles, duration)
    valid_pitches = [item["pitch_hz"] for item in samples if item["pitch_hz"] is not None]
    output = {
        "schema_version": "1.0",
        "analysis_status": "complete",
        "title": args.title,
        "source_url": args.source_url,
        "analyzed_seconds": round(duration, 3),
        "caption_source": args.subtitles,
        "method": {
            "transcript": "time-coded SRT caption ingestion",
            "voice": "1-second RMS and autocorrelation pitch proxy",
            "visual": "1 fps frame-difference proxy; this is not hand-pose detection",
        },
        "summary": {
            "caption_segments": len(subtitles),
            "speech_rate_wpm": add_speech_rate(subtitles, duration),
            "median_pitch_hz": round(float(np.median(valid_pitches)), 1) if valid_pitches else None,
            "median_visual_motion": round(float(np.median([item["visual_motion"] for item in samples])), 1) if samples else 0,
        },
        "transcript_segments": subtitles,
        "samples": samples,
        "limitations": [
            "Signals identify review points; they do not infer emotion, intent, truthfulness, or diplomacy outcomes.",
            "Visual motion is a whole-frame movement proxy and can be affected by camera cuts and framing.",
            "Captions may differ from spoken audio and should be checked against the source video.",
        ],
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {output_path} with {len(subtitles)} caption segments and {len(samples)} signal samples.")


if __name__ == "__main__":
    try:
        main()
    except (subprocess.CalledProcessError, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Analysis failed: {error}", file=sys.stderr)
        raise SystemExit(1)
