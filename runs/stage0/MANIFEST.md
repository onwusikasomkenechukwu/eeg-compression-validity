# Stage 0 run manifest

- Started: 2026-10-25 13:48 UTC
- Registered beforehand on OSF (embargoed); code: commit 3a9b77dda20ffe1da0abfa28988d505701de539f
- Command (WSL2 Ubuntu, ~/venvs/eegcv, Python 3.12, torch 2.14.1 CPU):
  python scripts/run_patient.py --dataset chbmit --model epidenet --arm patient --patients all --seeds 0 1 2 --workers 2 --threads 4 --out runs/stage0
- Expected: 138 folds x 3 seeds = 414 jobs
- Paused 2026-10-26 by request, with 236 jobs finished (chb01-chb14 complete, chb15 in progress). The two jobs running at the time (chb15 fold0 seed2, fold1 seed0) were discarded and rerun from scratch on resume; no finished job is affected. Resume with the same command.
- Resumed 2026-10-26 15:16 UTC with the same command, code and environment: 178 jobs remaining.
