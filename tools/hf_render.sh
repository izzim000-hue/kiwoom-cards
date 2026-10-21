#!/usr/bin/env bash
# HyperFrames 릴스 렌더: tools/hf_render.sh <프로젝트폴더> <출력.mp4>
# gsap을 로컬로 복사(CDN 차단 환경 대응) → 렌더 → 무음 오디오 트랙 추가(인스타 음악 추가용).
set -euo pipefail
P="$1"; OUT="$2"; V=0.8.181
command -v fc-list >/dev/null && fc-list | grep -qi "noto sans cjk" || { apt-get update -qq && apt-get install -y -qq fonts-noto-cjk; }
if [ ! -f "$P/gsap.min.js" ]; then T=$(mktemp -d); (cd "$T" && npm pack gsap@3.14.2 -s >/dev/null && tar xzf gsap-3.14.2.tgz); cp "$T/package/dist/gsap.min.js" "$P/"; fi
export HYPERFRAMES_SKIP_SKILLS=1
(cd "$P" && npx --yes hyperframes@$V telemetry disable >/dev/null 2>&1 || true; npx --yes hyperframes@$V lint && npx --yes hyperframes@$V render -q high -o /tmp/hf_raw.mp4)
ffmpeg -loglevel error -y -i /tmp/hf_raw.mp4 -f lavfi -i anullsrc=r=44100:cl=stereo -c:v copy -c:a aac -shortest -movflags +faststart "$OUT"
echo "done: $OUT"
