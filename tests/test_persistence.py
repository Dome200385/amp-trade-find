from pathlib import Path
import tempfile

def test_persistent_paths_are_absolute():
    from app.config import settings
    assert Path(settings.database_path).is_absolute()
    assert Path(settings.persistent_data_dir).is_absolute()
