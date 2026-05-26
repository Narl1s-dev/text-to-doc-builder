from pathlib import Path

from app.core.config import Settings, get_settings
from app.db.models import Artifact


class StorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def get_artifact_file_path(self, artifact: Artifact) -> Path:
        if not artifact.file_path:
            raise FileNotFoundError("Artifact does not have a file path.")
        path = Path(artifact.file_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError("Artifact file does not exist.")
        return path

