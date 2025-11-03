# Contributing to ChainReader

Thank you for your interest in contributing to ChainReader! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git
- pip

### Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/chainreader.git
   cd chainreader
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks**
   ```bash
   pre-commit install
   ```

## Development Workflow

### Before Committing

Our pre-commit hooks will automatically run the following checks:

- **Black** - Code formatting
- **Ruff** - Linting and import sorting
- **MyPy** - Type checking (with warnings)
- **Pytest** - Run all tests with minimum 55% coverage

If any check fails, the commit will be blocked. Fix the issues and try again.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=chainreader --cov-report=html

# Run specific test file
pytest tests/test_provider_manager.py

# Run with verbose output
pytest -v

# Run and stop at first failure
pytest -x
```

### Code Quality Checks

```bash
# Format code with black
black .

# Check formatting
black --check .

# Lint with ruff
ruff check .

# Auto-fix linting issues
ruff check --fix .

# Type checking
mypy chainreader --ignore-missing-imports
```

### Running Pre-commit Manually

```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

## Making Changes

### Branching Strategy

- `main` - Stable, production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates

### Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, descriptive commit messages
   - Add tests for new functionality
   - Update documentation as needed
   - Ensure all tests pass

3. **Push your branch**
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create a Pull Request**
   - Provide a clear description of changes
   - Reference any related issues
   - Ensure CI passes

5. **Address review feedback**
   - Make requested changes
   - Push updates to the same branch

## Code Style Guidelines

### Python Style

- Follow PEP 8 (enforced by Black and Ruff)
- Use type hints for all functions
- Write docstrings for all public methods
- Keep functions focused and small
- Prefer descriptive variable names

### Documentation Style

- Use Google-style docstrings
- Include parameter types and descriptions
- Provide usage examples where helpful
- Keep line length to 100 characters

### Example

```python
async def get_balance(self, address: str, block: str | int = "latest") -> int:
    """
    Get the balance of an address.

    Args:
        address: Ethereum address (hex string)
        block: Block number, hash, or 'latest'/'earliest' (default: 'latest')

    Returns:
        Balance in wei (as integer)

    Raises:
        InvalidAddressError: If address format is invalid
        AllProvidersFailedError: If all providers fail

    Example:
        >>> balance = await reader.get_balance('0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb')
        >>> print(f"Balance: {balance / 10**18} ETH")
    """
    params = {"address": address, "block": block}
    return await self.request_handler.execute("get_balance", params)
```

## Testing Guidelines

### Writing Tests

- Write tests for all new functionality
- Aim for >80% code coverage
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern
- Use fixtures for common setup

### Test Structure

```python
def test_feature_description():
    """Test what this test validates"""
    # Arrange
    cache = CacheManager()

    # Act
    result = cache.get("key")

    # Assert
    assert result is None
```

### Async Tests

```python
@pytest.mark.asyncio
async def test_async_feature():
    """Test async functionality"""
    reader = ChainReader(chain_id=1, providers=[...])
    balance = await reader.get_balance("0x...")
    assert balance >= 0
```

## Continuous Integration

Our CI pipeline runs on every push and pull request:

1. **Lint Check** - Runs Black and Ruff
2. **Type Check** - Runs MyPy (warnings only)
3. **Tests** - Runs pytest with coverage on Python 3.9, 3.10, 3.11, 3.12
4. **Coverage Upload** - Uploads coverage to Codecov (Python 3.12 only)

All checks must pass before a PR can be merged.

## Coverage Requirements

- Overall project coverage: >60%
- New code (patches): >70%
- Critical modules (provider_manager, cache_manager): >90%

## Documentation

### Updating Documentation

- Update README.md for user-facing changes
- Update docstrings for API changes
- Add examples for new features
- Update CHANGELOG.md

### Building Documentation (Future)

```bash
# Generate API docs (to be implemented in future)
# make docs
```

## Reporting Issues

### Bug Reports

Include:
- Python version
- Operating system
- ChainReader version
- Minimal reproducible example
- Expected vs actual behavior
- Error messages and stack traces

### Feature Requests

Include:
- Use case description
- Proposed API/interface
- Examples of how it would be used
- Any alternatives considered

## Getting Help

- Open an issue for bugs or feature requests
- Check existing issues before creating new ones
- Join discussions in pull requests

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Assume good intentions

## License

By contributing to ChainReader, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to ChainReader! 🎉
