from tree_sitter import Language
import os

__all__ = ["XML_LANGUAGE"]

# Loads the vendored language binary (works from source or wheel)
language_path = os.path.join(os.path.dirname(__file__), "xml")
XML_LANGUAGE = Language(language_path, "xml")
