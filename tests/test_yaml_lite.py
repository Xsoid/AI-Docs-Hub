from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from rag.yaml_lite import _load_restricted_yaml


class RestrictedYamlTests(unittest.TestCase):
    def test_parses_nested_list_of_mappings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.yaml"
            path.write_text(
                """documentation_readiness:
  items:
    - path: docs/README.md
      kind: file
      label: documentation entrypoint
      category: core
""",
                encoding="utf-8",
            )
            self.assertEqual(
                _load_restricted_yaml(path),
                {
                    "documentation_readiness": {
                        "items": [
                            {
                                "path": "docs/README.md",
                                "kind": "file",
                                "label": "documentation entrypoint",
                                "category": "core",
                            }
                        ]
                    }
                },
            )


if __name__ == "__main__":
    unittest.main()
