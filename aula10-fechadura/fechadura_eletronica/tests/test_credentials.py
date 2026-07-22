from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from credentials import CredentialStore


def test_credentials_round_trip(tmp_path: Path) -> None:
    store = CredentialStore(tmp_path / "credentials.json")
    store.set_pin("2580")
    assert store.verify("2580")
    assert not store.verify("2581")
    assert "2580" not in (tmp_path / "credentials.json").read_text()
