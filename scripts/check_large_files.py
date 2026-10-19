"""Reject oversized committed blobs in HEAD and an optional new-commit range."""

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

MAX_FILE_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class OversizedBlob:
    oid: str
    size: int
    paths: tuple[str, ...]


def find_oversized_blobs(
    repository: Path, base_ref: str | None = None, limit_bytes: int = MAX_FILE_BYTES,
) -> list[OversizedBlob]:
    """Inspect Git metadata, including blobs later removed within the range.

    Untracked files and uncommitted edits are intentionally outside this check.
    An invalid/missing base raises an error rather than silently skipping history.
    """
    def git(*args, data=None):
        return subprocess.run(
            ["git", "-C", str(repository), *args], input=data,
            check=True, capture_output=True,
        ).stdout

    head = git("rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    base = None
    if base_ref:
        base = git(
            "rev-parse", "--verify", "--end-of-options", f"{base_ref}^{{commit}}",
        ).decode().strip()

    sizes: dict[str, int] = {}
    paths: dict[str, list[str]] = {}
    for entry in git("ls-tree", "-r", "-l", "-z", head).split(b"\0"):
        if not entry:
            continue
        header, path = entry.split(b"\t", 1)
        _, kind, oid, size = header.split()
        if kind == b"blob" and int(size) > limit_bytes:
            key = oid.decode("ascii")
            sizes[key] = int(size)
            paths.setdefault(key, []).append(os.fsdecode(path))

    if base:
        objects = git("rev-list", "--objects", "--no-object-names", f"{base}..{head}")
        if objects.strip():
            metadata = git(
                "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                data=objects,
            )
            for line in metadata.splitlines():
                oid, kind, size = line.split()
                if kind == b"blob" and int(size) > limit_bytes:
                    sizes[oid.decode("ascii")] = int(size)

    return [
        OversizedBlob(oid, size, tuple(sorted(paths.get(oid, []))))
        for oid, size in sorted(sizes.items())
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", help="Compare new history against this fetched commit/ref")
    args = parser.parse_args()
    try:
        failures = find_oversized_blobs(Path.cwd(), base_ref=args.base_ref)
    except subprocess.CalledProcessError as exc:
        print("File-size check could not inspect Git history; failing closed.")
        print(exc.stderr.decode(errors="replace").strip())
        return 2
    if failures:
        print(f"FAIL: Git files must be at most {MAX_FILE_BYTES} bytes (10 MiB).")
        for item in failures:
            location = ", ".join(repr(p) for p in item.paths) or "removed/superseded history blob"
            print(f"  {item.size} bytes: {location}; blob {item.oid}")
        print("Store large data/models externally and remove the blob from every new commit.")
        print("Deleting it in a later commit does not remove the earlier Git object.")
        return 1
    print("PASS: no committed Git blob exceeds 10 MiB in HEAD or the checked new history.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
