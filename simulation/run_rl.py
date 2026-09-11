"""Register this task, then use the installed Isaac Lab official training/play script.

Pass --isaaclab-root for the installed checkout; generated assets use build/local.
"""
import argparse
from pathlib import Path
import runpy
import sys
from asset_integrity import verify_smoke

parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("--isaaclab-root", required=True, type=Path)
parser.add_argument("--mode", choices=("train", "play"), default="train")
args, remaining = parser.parse_known_args()
from paths import SIMULATION as here, SOURCE_SIMULATION
try:
    verify_smoke(here, SOURCE_SIMULATION / "microduckling_lab/environment.py")
except (OSError, ValueError) as exc:
    raise SystemExit(str(exc)) from exc
script = args.isaaclab_root.resolve() / f"scripts/reinforcement_learning/rsl_rl/{args.mode}.py"
if not script.is_file():
    raise SystemExit(f"Official Isaac Lab script missing: {script}")
sys.path.insert(0, str(SOURCE_SIMULATION))
sys.path.insert(0, str(script.parent))
import microduckling_lab  # only registers strings; does not import the simulator

sys.argv = [str(script), *remaining]
runpy.run_path(str(script), run_name="__main__")
