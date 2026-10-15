# AI Docs Hub

AI Docs Hub is a local documentation and context hub. It keeps project documentation in each connected project. It provides local indexes, generated context, templates, a docs site, and scoped MCP access.

## Requirements

- Python 3.11 as `python3.11`
- Node.js 22 LTS and npm 10+
- Git and `make`

## Quick Start

```sh
make setup
make healthcheck
make hub-dev
```

Open `http://localhost:4321/`. Use `make hub-status` to check the running local system.

## Documentation

- [Documentation map](docs/README.md)
- [Architecture](docs/architecture/overview.md)
- [Command reference](docs/operations/command-reference.md)
- [Documentation ownership](docs/standards/documentation-hygiene.md)
- [Generated artifacts](docs/standards/generated-artifacts.md)
- [Technical writing style](docs/standards/technical-writing.md)

Connected-project configs, indexes, reports, generated pages, and `llms*.txt` are local derived artifacts. Do not commit them. For repository and agent boundaries, read [AGENTS.md](AGENTS.md).
