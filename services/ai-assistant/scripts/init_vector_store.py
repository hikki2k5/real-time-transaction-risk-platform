from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.vector_store import PgVectorStore

if __name__ == "__main__":
    PgVectorStore(get_settings()).initialize()
    print("pgvector extension and ai knowledge tables are ready")
