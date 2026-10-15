# Public Metadata Lifecycle Paths

Project config can declare exact public metadata paths in `docs/` for the lifecycle path-name heuristic. The declaration does not include the file in RAG discovery. It does not disable exclude rules. It does not disable the diff secret scan.

Use the field only for declarative public data such as design token values. The schema rejects glob paths, paths outside `docs/`, and unsupported file types.
