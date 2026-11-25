#!/usr/bin/env bash
# EEGformer (update 8) on the GPU workstation, start to finish, in one script.
#
#   bash scripts/run_eegformer_ws.sh preflight          before registration; produces no results
#   bash scripts/run_eegformer_ws.sh run --registered   only after update 8 is submitted on OSF
#   bash scripts/run_eegformer_ws.sh status             progress of a running or finished run
#
# preflight (about 1-2 h): environment record, unit tests, fidelity check A (architecture),
#   signal cache for the 4 temporal channels, a 2-epoch smoke run of both designs on real data,
#   and the repeatability check: one full job (chb02 pre-training + fold 0, seed 0) run at the
#   same time on GPU 0 and GPU 1, compared array by array without opening any metric, then
#   deleted. Writes runs/stage4_eegformer/PREFLIGHT.md (environment, pass/fail, times) for the
#   update 8 brackets.
# run --registered (restarts itself in the background with nohup; resumable: rerun the same
#   command after a crash or reboot and finished jobs are skipped):
#   1. fidelity check C: EEGformer's own protocol on chb01-08, seeds 0-2  -> runs/eegformer_check
#   2. confirmatory run: 24 patients, seeds 0-4, pre-training then the plan's folds
#                                                                        -> runs/stage4_eegformer
#   3. W4A8 and FP16 from the saved FP32 weights (exploratory)           -> runs/stage4_eegformer_bitwidths
#   4. analyses: check C report, frontier summary with fidelity check B, statistics, caps
# One runner per GPU (CUDA_VISIBLE_DEVICES), GPU_WORKERS jobs each (default 2); training on the
# GPU with cuDNN's deterministic mode, quantization and scoring on the CPU at 4 threads per job.
#
# Settings (environment variables): PY (default ~/venvs/eegcv/bin/python), GPU_WORKERS (2),
# RESCORE_WORKERS (8), CACHE (~/eegcv_cache).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="${PY:-$HOME/venvs/eegcv/bin/python}"
P="$PY -W ignore"
GPU_WORKERS="${GPU_WORKERS:-2}"
RESCORE_WORKERS="${RESCORE_WORKERS:-8}"
CACHE="${CACHE:-$HOME/eegcv_cache}"
MAIN=runs/stage4_eegformer
CHECK=runs/eegformer_check
BITS=runs/stage4_eegformer_bitwidths
SEEDS_MAIN="0 1 2 3 4"
SEEDS_CHECK="0 1 2"
mkdir -p "$MAIN" "$CHECK" "$BITS"

count_done() {  # finished pre-training and fold jobs in a run folder: "<pre> <fold>"
  local pre fold
  pre=$(find "$1/_pretrain" -maxdepth 1 -name '*.json' 2>/dev/null | wc -l || true)
  fold=$(find "$1" -mindepth 2 -maxdepth 2 -name 'fold*_seed*.json' -not -path '*/_pretrain/*' 2>/dev/null | wc -l || true)
  echo "$pre $fold"
}

say() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"; }
die() { say "STOP: $*"; exit 1; }

warm_cache() {
  say "signal cache (temporal4, all CHB-MIT records; fast when already built)"
  $P - "$CACHE" <<'EOF'
import os, sys
sys.path.insert(0, "src")
import chbmit
root, cache = "data/chbmit", sys.argv[1]
n = 0
for pat in chbmit.list_patients(root):
    for p, _ in chbmit.usable_records(root, pat, "temporal4"):
        chbmit.load_record(p, cache, "temporal4")
        n += 1
print(f"{n} records cached")
EOF
}

# Two runners, one per GPU, sharing the output folder (jobs are claimed exclusively). Blocks
# until both finish. Arguments: output folder, then run_patient.py arguments.
# Each call writes fresh logs, runner_gpu<g>_<start time>.log, so a resumed run is judged on
# its own attempt.
two_runners() {
  local out="$1"; shift
  TAG="$(date -u +%Y%m%dT%H%M%SZ)"
  for g in 0 1; do
    CUDA_VISIBLE_DEVICES=$g $P scripts/run_patient.py --model eegformer "$@" --workers 0 \
      --gpu-workers "$GPU_WORKERS" --gpu-device cuda --threads 4 --cache "$CACHE" --out "$out" \
      > "$out/runner_gpu${g}_$TAG.log" 2>&1 &
  done
  wait
}

report_runners() {  # after two_runners: this attempt's logs, plus how many jobs are done in total
  local out="$1" expect="$2"
  local logs=("$out"/runner_gpu*_"$TAG".log) ok failed mem done_ pre fold
  ok=$(cat "${logs[@]}" | grep -c ': ok in' || true)
  failed=$(cat "${logs[@]}" | grep -c ': FAILED' || true)
  mem=$(cat "${logs[@]}" | grep -ciE 'out of memory|CUDACachingAllocator|cudaMalloc retries' || true)
  read -r pre fold <<< "$(count_done "$out")"
  done_=$(( pre + fold ))
  say "$out: this attempt $ok ok, $failed FAILED, $mem GPU memory warning line(s); $done_ of $expect jobs done"
  [ "$failed" = 0 ] || die "$out has failed jobs (see ${logs[*]}); fix, then rerun this command (finished jobs are skipped)"
  [ "$done_" = "$expect" ] || die "$out: $done_ of $expect jobs done; rerun this command (finished jobs are skipped)"
  [ "$mem" = 0 ] || say "WARNING: GPU memory warnings in $out (rerun check as in update 7 before analysis)"
}

compare_dirs() {  # identical saved arrays in two output folders; prints no metric
  $P - "$1" "$2" <<'EOF'
import glob, os, sys
import numpy as np
a, b = sys.argv[1:3]
files = sorted(os.path.relpath(p, a) for p in glob.glob(os.path.join(a, "**", "*.npz"), recursive=True))
if not files:
    sys.exit("no saved arrays to compare")
bad = []
for f in files:
    x, y = np.load(os.path.join(a, f)), np.load(os.path.join(b, f))
    if sorted(x.files) != sorted(y.files):
        bad.append(f"{f}: different array names")
        continue
    bad += [f"{f}:{k}" for k in x.files if not np.array_equal(x[k], y[k])]
print(f"compared {len(files)} files: " + ("identical" if not bad else "DIFFER: " + ", ".join(bad[:20])))
sys.exit(1 if bad else 0)
EOF
}

job_seconds() {  # total_s of a job summary (timing only)
  $P -c "import json,sys; print(round(json.load(open(sys.argv[1]))['timing']['total_s']))" "$1"
}

preflight() {
  local rep="$MAIN/PREFLIGHT.md" tmp
  tmp="$(mktemp -d /tmp/eegformer_preflight.XXXX)"
  say "preflight; scratch folder $tmp"
  {
    echo "# EEGformer preflight (update 8), $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo "No result was produced or inspected: the repeatability runs are compared array by array and deleted."
    echo
    echo "## Environment"
    echo
    echo "- commit: $(git rev-parse HEAD)$( [ -z "$(git status --porcelain --untracked-files=no)" ] || echo ' (tracked files modified!)')"
    echo "- $(lsb_release -ds 2>/dev/null || uname -sr)"
    echo "- NVIDIA driver $(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1); GPUs: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader | paste -sd ';')"
    echo "- CPU: $(lscpu | sed -n 's/^Model name: *//p' | head -1), $(nproc) threads; RAM $(free -g | awk '/Mem:/ {print $2}') GB"
    $P -c "import platform, torch, onnxruntime as o; print(f'- Python {platform.python_version()}, torch {torch.__version__} (CUDA {torch.version.cuda}, cuDNN {torch.backends.cudnn.version()}), onnxruntime {o.__version__}; CUDA available: {torch.cuda.is_available()}')"
  } > "$rep"
  $PY -c "import torch; assert torch.cuda.is_available() and torch.cuda.device_count() >= 2" || die "need 2 CUDA GPUs"

  say "unit tests"
  if $P -m pytest -q tests > "$tmp/pytest.log" 2>&1; then t="PASS ($(tail -1 "$tmp/pytest.log"))"; else t="FAIL"; fi
  printf '\n## Checks\n\n- unit tests: %s\n' "$t" >> "$rep"
  [ "$t" != FAIL ] || { tail -40 "$tmp/pytest.log"; die "unit tests failed"; }

  say "fidelity check A"
  $P scripts/check_eegformer.py --out "$MAIN" > "$tmp/check_a.log" 2>&1 || die "fidelity check A failed ($MAIN/fidelity_check_a.md)"
  echo "- fidelity check A (architecture): PASS ($MAIN/fidelity_check_a.md)" >> "$rep"

  warm_cache

  say "smoke run (2 epochs, real data): main design and check C, chb02 fold 0"
  CUDA_VISIBLE_DEVICES=0 $P scripts/run_patient.py --model eegformer --patients chb02 --folds 0 --seeds 0 \
    --workers 0 --gpu-workers 1 --gpu-device cuda --threads 4 --cache "$CACHE" --smoke --out "$tmp/smoke_main" > "$tmp/smoke_main.log" 2>&1
  CUDA_VISIBLE_DEVICES=1 $P scripts/run_patient.py --model eegformer --protocol eegformer --patients chb02 --folds 0 --seeds 0 \
    --workers 0 --gpu-workers 1 --gpu-device cuda --threads 4 --cache "$CACHE" --smoke --out "$tmp/smoke_check" > "$tmp/smoke_check.log" 2>&1
  for f in smoke_main smoke_check; do
    grep -q FAILED "$tmp/$f.log" && { cat "$tmp/$f.log"; die "smoke run $f failed"; }
    [ "$(grep -c ': ok in' "$tmp/$f.log")" = 2 ] || { cat "$tmp/$f.log"; die "smoke run $f did not finish 2 jobs"; }
  done
  echo "- smoke run, 2 epochs on real data (main design and check C, chb02 fold 0, both phases): PASS" >> "$rep"

  say "repeatability: chb02 pre-training + fold 0 seed 0, full epochs, on GPU 0 and GPU 1 at once (about 1 h)"
  for g in 0 1; do
    CUDA_VISIBLE_DEVICES=$g $P scripts/run_patient.py --model eegformer --patients chb02 --folds 0 --seeds 0 \
      --workers 0 --gpu-workers 1 --gpu-device cuda --threads 4 --cache "$CACHE" --out "$tmp/repeat_gpu$g" > "$tmp/repeat_gpu$g.log" 2>&1 &
  done
  wait
  for g in 0 1; do
    grep -q FAILED "$tmp/repeat_gpu$g.log" && { cat "$tmp/repeat_gpu$g.log"; die "repeatability run on GPU $g failed"; }
  done
  local same pre0 pre1 fold0 fold1
  if same=$(compare_dirs "$tmp/repeat_gpu0" "$tmp/repeat_gpu1"); then r=PASS; else r=FAIL; fi
  pre0=$(job_seconds "$tmp/repeat_gpu0/_pretrain/chb02_seed0.json"); pre1=$(job_seconds "$tmp/repeat_gpu1/_pretrain/chb02_seed0.json")
  fold0=$(job_seconds "$tmp/repeat_gpu0/chb02/fold0_seed0.json"); fold1=$(job_seconds "$tmp/repeat_gpu1/chb02/fold0_seed0.json")
  {
    echo "- repeatability (chb02 pre-training + fold 0 seed 0, GPU 0 vs GPU 1, all saved arrays): $r ($same)"
    echo
    echo "## Time per job (one job per GPU; the run uses $GPU_WORKERS per GPU)"
    echo
    echo "- pre-training (chb02's pool): ${pre0} s and ${pre1} s"
    echo "- fold job (chb02 fold 0): ${fold0} s and ${fold1} s"
    $PY -c "
pre, fold = (int('$pre0') + int('$pre1')) / 2, (int('$fold0') + int('$fold1')) / 2
slots = 2 * int('$GPU_WORKERS')
main = (120 * pre + 690 * fold) / slots / 3600
print(f'- rough estimate, ignoring slowdown from sharing a GPU: main run (120 pre-training + 690 fold jobs) about {main:.0f} h; '
      f'check C (24 smaller pre-trainings + 120 fold jobs) a few hours')"
  } >> "$rep"
  rm -rf "$tmp"
  [ "$r" = PASS ] || die "repeatability check failed: see $rep; the run must not start (update 3's rule)"
  say "preflight passed: $rep"
  cat "$rep"
}

status() {
  for d in "$CHECK" "$MAIN" "$BITS"; do
    local pre fold
    read -r pre fold <<< "$(count_done "$d")"
    echo "$d: $pre pre-training, $fold fold jobs done; FAILED lines (all attempts): $(cat "$d"/runner*.log "$d"/rescore.log 2>/dev/null | grep -c FAILED || true)"
  done
  echo "(check C: 24 pre-training + 120 fold jobs; main: 120 + 690; bitwidths: 690)"
  tail -3 "$MAIN/pipeline.log" 2>/dev/null || true
  nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader 2>/dev/null || true
}

run() {
  [ "${1:-}" = "--registered" ] || die "start the run only after update 8 is submitted on OSF: bash $0 run --registered"
  [ -z "$(git status --porcelain --untracked-files=no)" ] || die "tracked files are modified; the run must use a clean, registered commit"
  [ -f "$MAIN/PREFLIGHT.md" ] && grep -q "repeatability.*PASS" "$MAIN/PREFLIGHT.md" || die "run the preflight first (and pass it)"
  if [ -z "${EEGF_BACKGROUND:-}" ]; then
    EEGF_BACKGROUND=1 nohup bash "$0" run --registered >> "$MAIN/pipeline.log" 2>&1 &
    echo "started in the background (pid $!). Follow:  tail -f $MAIN/pipeline.log   Progress:  bash $0 status"
    exit 0
  fi
  say "run at commit $(git rev-parse HEAD)"
  git rev-parse HEAD > "$MAIN/RUN_COMMIT"
  warm_cache

  say "1/4 fidelity check C: chb01-08, seeds $SEEDS_CHECK"
  two_runners "$CHECK" --protocol eegformer --patients all --seeds $SEEDS_CHECK
  report_runners "$CHECK" 144   # 8 patients x 3 seeds pre-training + 40 folds x 3 seeds
  $P scripts/eegformer_gate.py --runs "$CHECK" > /dev/null
  say "check C report written: $CHECK/fidelity_check_c.md (whatever it shows, the confirmatory run goes ahead, as registered)"

  say "2/4 confirmatory run: 24 patients, seeds $SEEDS_MAIN"
  two_runners "$MAIN" --patients all --seeds $SEEDS_MAIN
  report_runners "$MAIN" 810    # 24 patients x 5 seeds pre-training + 138 folds x 5 seeds

  say "3/4 W4A8 and FP16 from the saved weights"
  $P scripts/rescore_bitwidths.py --runs "$MAIN" --out "$BITS" --workers "$RESCORE_WORKERS" --threads 4 --cache "$CACHE" >> "$BITS/rescore.log" 2>&1
  grep -q FAILED "$BITS/rescore.log" && die "rescore had failures (see $BITS/rescore.log); rerun this command"

  say "4/4 analyses"
  $P scripts/analyze_frontier.py --runs "$MAIN" > "$MAIN/frontier.txt" 2>&1
  $P scripts/analyze_stats.py --runs "$MAIN" > "$MAIN/stats.txt" 2>&1
  $P scripts/analyze_stats.py --runs "$MAIN" --caps 0.5 1 2 > "$MAIN/caps.txt" 2>&1
  $P scripts/analyze_stats.py --runs "$BITS" --models int8 sim6 sim4 w4a8 fp16 --excess-only > "$BITS/excess.txt" 2>&1
  $P scripts/analyze_stats.py --runs "$BITS" --models int8 sim6 sim4 w4a8 fp16 --excess-only --caps 0.5 1 2 > "$BITS/caps.txt" 2>&1
  date -u +%Y-%m-%dT%H:%M:%SZ > "$MAIN/DONE"
  say "done. Reports: $CHECK/fidelity_check_c.md, $MAIN/summary.md, $MAIN/stats.md, $MAIN/caps.md, $BITS/excess.md, $BITS/caps.md"
}

case "${1:-}" in
  preflight) preflight ;;
  run) shift; run "$@" ;;
  status) status ;;
  *) sed -n 2,26p "$0"; exit 2 ;;
esac
