"""Lets the LinearMD tests import the helpers kept beside them."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
