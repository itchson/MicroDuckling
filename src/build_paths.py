"""Separate locally generated vendor-containing artifacts from published files."""
import os
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]


def build_root() -> Path:
    value = os.environ.get("MICRODUCKLING_BUILD_ROOT")
    result = Path(value).expanduser().resolve() if value else REPOSITORY / "build/local"
    # A mistaken output root must not replace the repository's public cad files.
    if result == REPOSITORY or REPOSITORY.is_relative_to(result):
        raise ValueError("MICRODUCKLING_BUILD_ROOT must be a separate generated-output directory")
    if result.is_relative_to(REPOSITORY):
        relative = result.relative_to(REPOSITORY)
        if relative.parts[0] not in {"build", "work"}:
            raise ValueError("Inside the repository, use a build/ or work/ directory for local output")
    return result


BUILD_ROOT = build_root()
