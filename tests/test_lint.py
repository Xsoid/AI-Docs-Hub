from __future__ import annotations

import unittest

from rag.lint import _check_broken_wiki_links, _check_orphan_pages
from rag.security import scan_text_for_secrets


def make_index(files: dict[str, str]) -> dict:
    return {
        "documents": [{"source_path": path, "chunk_ids": [path]} for path in files],
        "chunks": [{"source_path": path, "text": text, "section": ""} for path, text in files.items()],
    }


class LintLinkTests(unittest.TestCase):
    def test_shell_test_brackets_are_not_wiki_links(self) -> None:
        index = make_index(
            {
                "scripts/build.sh": 'if [[ -z "$CLIENT_ID" ]]; then exit 1; fi\n',
                "docs/guide.md": "See [[missing-page]].\n",
            }
        )

        issues = _check_broken_wiki_links(index, {"guide", "build"})

        self.assertEqual([(i["source_path"], i["target"]) for i in issues], [("docs/guide.md", "missing-page")])

    def test_orphan_check_ignores_code_and_counts_markdown_links(self) -> None:
        index = make_index(
            {
                "core/src/worker.rs": "fn main() {}\n",
                "docs/README.md": "[Architecture](architecture/overview.md)\n",
                "docs/architecture/overview.md": "# Overview\n\nNo outgoing links.\n",
                "docs/development/linked-out.md": "Back to [docs](../README.md#top).\n",
                "docs/lonely.md": "# Lonely\n\n`[not](a-link.md)` stays code.\n",
            }
        )

        issues = _check_orphan_pages(index, set())

        self.assertEqual([issue["source_path"] for issue in issues], ["docs/lonely.md"])


class SecretPatternTests(unittest.TestCase):
    def test_call_expression_is_not_an_assigned_secret(self) -> None:
        self.assertEqual(scan_text_for_secrets("  password: z.string().min(8)"), [])
        self.assertEqual(scan_text_for_secrets("password = read_password()"), [])
        self.assertEqual(scan_text_for_secrets("client = Client(api_key=gemini_api_key)"), [])
        self.assertEqual(scan_text_for_secrets("func load(session: URLSession) -> Void"), [])

    def test_literal_assigned_secrets_are_still_detected(self) -> None:
        for line in ('PASSWORD="synthetic-value-123"', "api_key=synthetic1234567890", "token: synthetic.value-123", "api_key=synthetic1234567890)"):
            with self.subTest(line=line):
                self.assertEqual(scan_text_for_secrets(line)[0]["kind"], "assignment_secret")


if __name__ == "__main__":
    unittest.main()
