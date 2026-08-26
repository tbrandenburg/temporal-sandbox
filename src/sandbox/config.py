"""Env-overridable settings, read once at import time."""

import os

TEMPORAL_ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "127.0.0.1:7233")
TEMPORAL_NAMESPACE = os.environ.get("TEMPORAL_NAMESPACE", "default")
TEMPORAL_UI_URL = os.environ.get("TEMPORAL_UI_URL", "http://127.0.0.1:8233")
SANDBOX_BUNDLES = os.environ.get("SANDBOX_BUNDLES", "")
