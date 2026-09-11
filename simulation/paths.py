"""Shared local build paths; simulation source stays in the repository."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from build_paths import BUILD_ROOT, REPOSITORY

SIMULATION = BUILD_ROOT / "simulation"
SOURCE_SIMULATION = REPOSITORY / "simulation"
