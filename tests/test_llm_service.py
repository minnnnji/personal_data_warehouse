import json
import os
import pytest
import httpx
from unittest.mock import patch, MagicMock

from backend.llm_service import (
    _call_llm,
    _call_internal_llm,
    generate_metadata,
    search_files,
    generate_combine_code,
)
