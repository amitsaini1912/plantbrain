"""Central configuration. Keep all tunable constants in one place."""
from pathlib import Path
from dotenv import load_dotenv

# Load secrets from a local .env file (we create that next step; never commit it).
load_dotenv()

# --- Identity ---
APP_NAME = "PlantBrain"
APP_TAGLINE = "Industrial Knowledge Intelligence — your unified asset & operations brain."

# --- Paths (auto-created if missing) ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"     # uploaded source documents
STORE_DIR = BASE_DIR / "store"   # vector database lives here
DATA_DIR.mkdir(exist_ok=True)
STORE_DIR.mkdir(exist_ok=True)

# --- Keys (we wire this up in the next step) ---
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")