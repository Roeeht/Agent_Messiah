"""Language separation layer for Agent Messiah.

This module provides:
- Caller-facing Hebrew text (caller_he.py)
- Translation utilities (translator.py)
- Text provider interface (text_provider.py)
"""

from .caller_he import get_caller_text
from .translator import translate_he_to_en, translate_en_to_he

__all__ = ['get_caller_text', 'translate_he_to_en', 'translate_en_to_he']
