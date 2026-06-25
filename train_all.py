"""
GeoTrade AI - Batch Training Runner (Phase 4)
==============================================
Phase 4 Architecture: Universal-only.

Individual asset models are deprecated — all inference goes through the
Universal ensemble + per-asset Platt calibrators.

train_asset.py is kept on disk for reference but is no longer called here.

Usage:
    python train_all.py
    python train_all.py --dry-run   (validate environment, skip actual training)
"""

import subprocess
import sys
import os
import argparse
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PYTHON   = sys.executable


def run(cmd, desc):
    print("\n" + "=" * 70)
    print(f">>> {desc}")
    print("=" * 70)
    t0     = time.time()
    result = subprocess.run(cmd, cwd=BASE_DIR)
    elapsed = time.time() - t0
    status = "OK" if result.returncode == 0 else f"FAILED (exit {result.returncode})"
    print(f"\n[{status}] {desc}  (elapsed: {elapsed:.0f}s)\n")
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Check environment + imports only, skip training",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("=" * 70)
        print("DRY RUN — validating environment")
        print("=" * 70)
        ok = run(
            [PYTHON, "-c",
             "import torch, xgboost, lightgbm, arch, yfinance, sklearn, joblib; "
             "print('All dependencies OK')"],
            "Dependency check",
        )
        if ok:
            print("Environment is ready. Run without --dry-run to train.")
        else:
            print("Fix missing dependencies above before training.")
        return

    print("=" * 70)
    print("GeoTrade AI — Phase 4 Universal Training")
    print("Architecture: Universal model + per-asset Platt calibrators")
    print("Expected time: 40–60 min on CPU")
    print("=" * 70)

    ok = run(
        [PYTHON, "train_ensemble.py"],
        "Training Universal Ensemble (Phase 4: 14 assets, SELL-aware, Platt calibration)",
    )

    print("\n" + "=" * 70)
    print("TRAINING SUMMARY")
    print("=" * 70)
    mark = "OK" if ok else "FAILED"
    print(f"  [{mark}] Universal Ensemble")

    if ok:
        print("\nAll models trained successfully!")
        print("\nNext step: run evaluation")
        print(f"  {PYTHON} evaluate_all.py")
    else:
        print("\nTraining failed. Check the output above.")


if __name__ == "__main__":
    main()
