# Contributing to RAIVEN

Thank you for your interest in contributing to RAIVEN! This document outlines the process for contributing code, reporting issues, and getting involved in the project.

## Getting Started

1. **Fork the Repository**: Create a personal fork of the RAIVEN repository on GitHub or your preferred platform.
2. **Clone Your Fork**: `git clone <your-fork-url>`
3. **Set Up Development Environment**: Use the provided Nix flake to get a consistent development environment.
   ```bash
   nix develop
   ```
   This will drop you into a shell with all necessary Python dependencies installed.

## Development Workflow

1. **Create a Branch**: For each feature or bug fix, create a new branch from `main` (or the default branch).
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. **Make Changes**: Implement your changes, ensuring they adhere to the project's style and architecture.
3. **Test Your Changes**: Ensure the application runs correctly with your modifications. For now, this involves manual testing of the ingestion and retrieval logic.
4. **Update Documentation**: If you add new features or change existing behavior, update the relevant documentation files (`README.md`, `USAGE.md`, `implementation guide.md`).
5. **Commit Your Changes**: Write clear, concise commit messages. Use conventional commits if possible (e.g., `feat: add new feature`, `fix: resolve issue`).
6. **Push to Your Fork**: `git push origin feature/my-new-feature`
7. **Open a Pull Request**: Submit a pull request from your fork to the main RAIVEN repository.

## Code Style

- **Python**: Follow PEP 8 guidelines. Use `black` for code formatting if possible.
- **Nix**: Follow general Nix community style practices.
- **Documentation**: Use standard Markdown formatting.

## Architecture Notes for Contributors

- The core logic resides in `raiven.py`, specifically within the `CognitiveMemory` class.
- The application is configured via environment variables, which are managed by the Home Manager module `hm-module.nix`.
- The `flake.nix` defines the build process and the development environment.
- The system relies on Neo4j for storage and Ollama for embeddings. Ensure your changes are compatible with these dependencies.

## Reporting Issues

- Use the GitHub issue tracker to report bugs or suggest features.
- Provide as much detail as possible, including steps to reproduce, expected vs. actual behavior, and your environment (Nix version, Python version if relevant, Neo4j/Ollama versions).
- Include relevant logs if the application fails.

## Questions?

If you have questions, feel free to open an issue for discussion.
