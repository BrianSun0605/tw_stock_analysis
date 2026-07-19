import shutil
import uuid
from pathlib import Path

from app_runtime.single_instance import SingleInstance


def test_second_instance_is_rejected_and_reads_existing_port():
    root = (
        Path(__file__).resolve().parents[1]
        / "output"
        / f".instance-test-{uuid.uuid4().hex}"
    )
    first = SingleInstance(str(root))
    second = SingleInstance(str(root))
    try:
        assert first.acquire() is True
        first.write_state(port=5123, version="test")
        assert second.acquire() is False
        assert second.read_state()["port"] == 5123
        first.release()
        assert second.acquire() is True
    finally:
        second.release()
        first.release()
        if (
            root.is_dir()
            and root.parent == Path(__file__).resolve().parents[1] / "output"
        ):
            shutil.rmtree(root)
