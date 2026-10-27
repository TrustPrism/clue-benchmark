"""Explicit, checksummed local reproduction archive extraction."""

import re
import shutil
import tarfile
from pathlib import Path, PurePosixPath

from .community_bundle import file_hash


def unpack_archive(archive, expected_sha256, output, maximum_bytes=1_000_000_000):
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("a published lowercase SHA-256 checksum is required")
    if type(maximum_bytes) is not int or maximum_bytes < 1:
        raise ValueError("archive byte limit must be positive")
    if file_hash(archive) != expected_sha256:
        raise ValueError("archive checksum mismatch; nothing extracted")
    root = Path(output)
    if root.exists():
        raise ValueError("archive output exists; choose a new directory")
    with tarfile.open(archive, "r:*") as stream:
        members = stream.getmembers()
        seen, total = set(), 0
        for member in members:
            path = PurePosixPath(member.name)
            if (
                not member.name
                or path.is_absolute()
                or ".." in path.parts
                or "\\" in member.name
                or ":" in member.name
                or str(path) in seen
                or not (member.isdir() or member.isfile())
            ):
                raise ValueError(
                    "unsafe archive member; links and traversal are forbidden"
                )
            seen.add(str(path))
            total += member.size
            if total > maximum_bytes:
                raise ValueError("archive exceeds explicit uncompressed byte limit")
        root.mkdir(parents=True, exist_ok=False)
        try:
            for member in members:
                target = root.joinpath(*PurePosixPath(member.name).parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with (
                        stream.extractfile(member) as source,
                        target.open("xb") as destination,
                    ):
                        shutil.copyfileobj(source, destination)
        except BaseException:
            shutil.rmtree(root)
            raise
    return {
        "sha256": expected_sha256,
        "output": str(root),
        "members": len(members),
        "uncompressed_bytes": total,
        "external_inference": False,
    }
