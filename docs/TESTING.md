# Testing Guide

## Test Types

### 1. Mock Tests (Fast, Free)
Run on every commit. Test business logic without API calls.

```bash
# Run all mock tests (excludes live tests)
uv run pytest -v -m "not live"

# Run specific test file
uv run pytest -v tests/test_retry_logic.py

# Run with coverage
uv run pytest --cov=src --cov-report=html
```

**When to use:**
- Testing database operations
- Testing UI state management
- Testing retry logic
- Testing error handling paths
- Continuous integration

### 2. Live Integration Tests (Slow, Costs $$$)
Make real API calls. Run before releases only.

```bash
# Run ONLY live tests
uv run pytest -v -m live

# Run specific live test
uv run pytest -v tests/test_live_integration.py::test_openai_integration
```

**When to use:**
- Before production releases
- Validating API key configuration
- Testing actual model behavior
- Verifying conversation context handling

**Cost:** ~$0.001-0.01 per test run

## Test Structure

```
tests/
├── test_db.py              # Database tests (mock)
├── test_ai.py              # AI logic tests (mock)
├── test_retry_logic.py     # Retry mechanism tests (mock)
├── test_ui.py              # UI component tests (mock)
└── test_live_integration.py # Real API tests (live)
```

## Writing Tests

### Mock Test Example
```python
@pytest.mark.asyncio
async def test_retry_success():
    """Test that retry logic works"""
    mock_func = AsyncMock(return_value="success")
    result = await retry_with_backoff(mock_func)
    assert result == "success"
```

### Live Test Example
```python
@pytest.mark.live
@pytest.mark.asyncio
async def test_openai_call():
    """Test actual OpenAI API"""
    if not os.getenv('OPENAI_API_KEY'):
        pytest.skip("API key not set")
    
    response = await generate_robot_response(robot, history)
    assert response is not None
```

## CI/CD Integration

### GitHub Actions
```yaml
# Run mock tests on every commit
- name: Run Tests
  run: uv run pytest -v -m "not live"

# Run live tests only on release
- name: Live Integration Tests
  if: github.event_name == 'release'
  run: uv run pytest -v -m live
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
```

## Best Practices

1. **Run mock tests frequently** - They're fast and free
2. **Run live tests sparingly** - They cost money
3. **Mark live tests clearly** - Use `@pytest.mark.live`
4. **Skip gracefully** - Check for API keys before running
5. **Document costs** - Note API costs in test docstrings

## Current Test Coverage

Run to see coverage report:
```bash
uv run pytest --cov=src --cov-report=term-missing
```

Target: **80% coverage** for production code
