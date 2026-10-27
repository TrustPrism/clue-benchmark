import io
import tarfile

import pytest

from clue_benchmark.archives import unpack_archive
from clue_benchmark.community_bundle import file_hash


def archive(path, name, kind=None):
    with tarfile.open(path, "w:gz") as stream:
        member = tarfile.TarInfo(name)
        if kind:
            member.type = kind
            member.linkname = "../outside"
        else:
            member.size = 2
        stream.addfile(member, None if kind else io.BytesIO(b"ok"))
    return path


@pytest.mark.parametrize(
    "name,kind",
    [
        ("../escape", None),
        ("/absolute", None),
        ("C:\\escape", None),
        ("nested/link", tarfile.SYMTYPE),
        ("hard", tarfile.LNKTYPE),
    ],
)
def test_rejects_traversal_and_links_before_creating_output(tmp_path, name, kind):
    source = archive(tmp_path / "data.tar.gz", name, kind)
    with pytest.raises(ValueError, match="unsafe"):
        unpack_archive(source, file_hash(source), tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_checksum_size_and_success(tmp_path):
    source = archive(tmp_path / "data.tar.gz", "safe/data.json")
    with pytest.raises(ValueError, match="checksum"):
        unpack_archive(source, "0" * 64, tmp_path / "out")
    with pytest.raises(ValueError, match="byte limit"):
        unpack_archive(source, file_hash(source), tmp_path / "out", maximum_bytes=1)
    unpack_archive(source, file_hash(source), tmp_path / "out")
    assert (tmp_path / "out/safe/data.json").read_text() == "ok"
    with pytest.raises(ValueError, match="exists"):
        unpack_archive(source, file_hash(source), tmp_path / "out")
