"""Extract representative samples from AISHELL-3 to voice_library/."""

import os
import json
import subprocess
import random

AISHELL_DIR = "data/aishell3"
SPK_INFO = os.path.join(AISHELL_DIR, "spk-info.txt")
OUTPUT_DIR = "voice_library/samples"
METADATA_FILE = "voice_library/metadata.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

AGE_MAP = {"A": "child", "B": "young", "C": "middle", "D": "elderly"}

speakers = []
with open(SPK_INFO) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 3:
            spk_id, age, gender = parts[0], parts[1], parts[2]
            speakers.append((spk_id, age, gender))

print(f"Total speakers: {len(speakers)}")

# Select representatives from each group
groups = {}
for spk_id, age, gender in speakers:
    key = (age, gender)
    groups.setdefault(key, []).append(spk_id)

selected = []
# Pick 2-3 from each group (or all if small group)
for key, spk_list in sorted(groups.items()):
    age, gender = key
    count = min(len(spk_list), 3)
    picked = random.sample(spk_list, count)
    for spk_id in picked:
        selected.append((spk_id, age, gender))
    age_label = AGE_MAP.get(age, age)
    print(f"  {gender} {age_label}: {count}/{len(spk_list)}")

print(f"\nSelected {len(selected)} speakers")

# Find a WAV file for each speaker
GENDER_LABELS = {"male": "男", "female": "女"}
AGE_LABELS_SHORT = {"child": "童", "young": "青年", "middle": "中年", "elderly": "老年"}


def find_wav(spk_id):
    for prefix in ["train", "test"]:
        wav_dir = os.path.join(AISHELL_DIR, prefix, "wav", spk_id)
        if os.path.isdir(wav_dir):
            files = sorted(os.listdir(wav_dir))
            if files:
                return os.path.join(wav_dir, files[0])
    return None

entries = []
for spk_id, age, gender in selected:
    wav_path = find_wav(spk_id)
    if not wav_path:
        print(f"  WARN: no wav found for {spk_id}")
        continue

    # Extract 0-5 seconds
    age_label = AGE_MAP.get(age, age)
    name = f"aishell3_{spk_id}"
    out_path = os.path.join(OUTPUT_DIR, f"{name}.wav")

    if not os.path.exists(out_path):
        subprocess.run([
            "ffmpeg", "-y", "-i", wav_path,
            "-t", "5", "-ar", "24000", "-ac", "1",
            out_path
        ], check=True, capture_output=True)

    duration = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", out_path],
        capture_output=True, text=True
    ).stdout.strip())

    display_age = AGE_LABELS_SHORT.get(age_label, age_label)
    display_gender = GENDER_LABELS.get(gender, gender)

    entries.append({
        "name": f"{spk_id} ({display_age}{display_gender})",
        "gender": gender,
        "age_group": age_label,
        "description": f"AISHELL-3 speaker {spk_id}, {gender}, age group {age_label}",
        "audio_path": out_path,
        "source": "AISHELL-3",
    })
    print(f"  {spk_id}: {gender} {age_label}, {duration:.1f}s -> {out_path}")

# Save metadata
with open(METADATA_FILE, "w", encoding="utf-8") as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)

print(f"\nSaved {len(entries)} entries to {METADATA_FILE}")
