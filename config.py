"""Central configuration — keep all tunable constants in one place."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Identity ---
APP_NAME = "PlantBrain"
APP_TAGLINE = "Industrial Knowledge Intelligence — your unified asset & operations brain."

# --- Paths (auto-created if missing) ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STORE_DIR = BASE_DIR / "store"
SAMPLE_DIR = BASE_DIR / "sample_docs"
DATA_DIR.mkdir(exist_ok=True)
STORE_DIR.mkdir(exist_ok=True)

# --- LLM ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = "claude-sonnet-4-6"

# --- Embeddings ---
EMBED_MODEL = "all-MiniLM-L6-v2"   # 384-dim, fast, good for industrial text
EMBED_DIM   = 384
TOP_K       = 6                      # chunks returned per RAG query

# --- Chunking ---
CHUNK_SIZE  = 1000
CHUNK_OVERLAP = 150
