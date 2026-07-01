import os
import sys

# Ensure the project root is importable so tests can `import app` / `import eval`
# regardless of pytest's working directory.
sys.path.insert(0, os.path.dirname(__file__))
