# Report Generator Skill - Testing Documentation

## Overview

This document describes the comprehensive test suite for the `report-generator` skill. The tests validate all aspects of the skill system including skill discovery, agent tool invocations, script execution, reference files, and end-to-end workflows.

## Test Suite Location

The main test suite is located at:
```
examples/skill-agent/test_skill_integration.py
```

## Test Categories

The test suite includes 25+ tests organized into these categories:

### 1. Skill Discovery Tests (2 tests)
Validates that the skill is correctly discovered and metadata is properly parsed.

**Tests:**
- `test_skill_discovery` - Verifies skill appears in skill list with correct metadata
- `test_skill_metadata_structure` - Validates metadata structure and required fields

**What's Tested:**
- YAML frontmatter parsing
- Skill name, description, version, tags
- Content loading (progressive disclosure)

### 2. Agent Tool Invocation Tests (5 tests)
Verifies that the AI agent correctly uses file operation tools.

**Tests:**
- `test_agent_ls_workspace` - Agent lists workspace directory files
- `test_agent_read_input_file` - Agent reads JSON/CSV data files
- `test_agent_glob_data_files` - Agent finds files by pattern
- `test_agent_grep_search_data` - Agent searches within files
- `test_agent_write_output_file` - Agent writes generated reports

**What's Tested:**
- File system tool invocations (ls, read_file, write_file, glob, grep)
- Agent understanding of file operations
- Correct tool parameter passing

### 3. Script Execution Tests (7 tests)
Tests direct execution of the generate_report.py script with various parameters.

**Tests:**
- `test_execute_basic_report_markdown` - Generate Markdown report from JSON
- `test_execute_html_report` - Generate HTML report from CSV
- `test_execute_json_report` - Generate JSON report with statistics
- `test_execute_with_template` - Use custom HTML template
- `test_execute_invalid_template` - Handle missing template error
- `test_execute_missing_input` - Handle missing input file error
- `test_execute_invalid_format` - Handle malformed data error

**What's Tested:**
- Multiple input formats (JSON, CSV)
- Multiple output formats (Markdown, HTML, JSON)
- Template application and placeholder replacement
- Error handling and exit codes
- Data aggregation (sum, average, min, max)

### 4. Reference File Tests (3 tests)
Validates reference file access and progressive disclosure pattern.

**Tests:**
- `test_agent_read_templates_reference` - Agent reads TEMPLATES.md
- `test_agent_read_html_template` - Agent reads HTML template file
- `test_skill_references_not_loaded_by_default` - Verifies lazy loading

**What's Tested:**
- Reference file accessibility
- Progressive disclosure (metadata first, details on-demand)
- Agent understanding of template system

### 5. Integration Tests (3 tests)
End-to-end workflows testing the complete skill system.

**Tests:**
- `test_end_to_end_report_workflow` - Complete workflow from discovery to output
- `test_multiple_report_formats` - Generate all format types
- `test_csv_to_html_workflow` - CSV input with HTML template output

**What's Tested:**
- Multi-step workflows
- Integration of all components
- Format conversion pipelines

### 6. Docker Backend Tests (3 tests)
Validates script execution in Docker containers.

**Tests:**
- `test_script_runs_in_docker` - Script executes in container
- `test_docker_script_access_volumes` - Access mounted volumes
- `test_docker_backend_timeout` - Timeout handling (skipped by default)

**What's Tested:**
- Docker execution environment
- Volume mounting (/skills/, /workspace/)
- Container isolation

## Test Data Files

The test suite uses these data files:

### JSON Test Data
**File:** `workspace/test_data.json`

```json
{
  "records": [
    {"id": 1, "name": "Product A", "value": 100, "category": "Electronics", "quantity": 5},
    {"id": 2, "name": "Product B", "value": 250, "category": "Electronics", "quantity": 3},
    {"id": 3, "name": "Product C", "value": 75, "category": "Furniture", "quantity": 8},
    {"id": 4, "name": "Product D", "value": 150, "category": "Furniture", "quantity": 2},
    {"id": 5, "name": "Product E", "value": 320, "category": "Electronics", "quantity": 4}
  ]
}
```

**Statistics:**
- 5 records total
- Value sum: 895
- Value average: 179
- Categories: Electronics (3), Furniture (2)

### CSV Test Data
**File:** `workspace/test_data.csv`

Same data as JSON, in CSV format with headers.

## Running Tests

### Prerequisites

1. Python 3.8+ installed
2. pytest installed: `pip install pytest`
3. Agent framework dependencies installed
4. Docker running (for Docker backend tests)

### Run All Tests

```bash
cd examples/skill-agent
pytest test_skill_integration.py -v
```

### Run Specific Test Category

```bash
# Skill discovery tests
pytest test_skill_integration.py::TestSkillDiscovery -v

# Agent tool tests
pytest test_skill_integration.py::TestAgentToolInvocations -v

# Script execution tests
pytest test_skill_integration.py::TestScriptExecution -v

# Reference file tests
pytest test_skill_integration.py::TestReferenceFiles -v

# Integration tests
pytest test_skill_integration.py::TestIntegration -v

# Docker tests
pytest test_skill_integration.py::TestDockerBackend -v
```

### Run Single Test

```bash
pytest test_skill_integration.py::TestScriptExecution::test_execute_basic_report_markdown -v
```

### Run with Coverage

```bash
pytest test_skill_integration.py --cov=skills/report-generator --cov-report=html
```

Coverage report will be in `htmlcov/index.html`.

### Run with Verbose Output

```bash
pytest test_skill_integration.py -vv --tb=long
```

## Expected Test Results

### All Tests Passing

When all tests pass, you should see:

```
======================== test session starts =========================
collected 23 items

test_skill_integration.py::TestSkillDiscovery::test_skill_discovery PASSED
test_skill_integration.py::TestSkillDiscovery::test_skill_metadata_structure PASSED
test_skill_integration.py::TestAgentToolInvocations::test_agent_ls_workspace PASSED
test_skill_integration.py::TestAgentToolInvocations::test_agent_read_input_file PASSED
test_skill_integration.py::TestAgentToolInvocations::test_agent_glob_data_files PASSED
test_skill_integration.py::TestAgentToolInvocations::test_agent_grep_search_data PASSED
test_skill_integration.py::TestAgentToolInvocations::test_agent_write_output_file PASSED
test_skill_integration.py::TestScriptExecution::test_execute_basic_report_markdown PASSED
test_skill_integration.py::TestScriptExecution::test_execute_html_report PASSED
test_skill_integration.py::TestScriptExecution::test_execute_json_report PASSED
test_skill_integration.py::TestScriptExecution::test_execute_with_template PASSED
test_skill_integration.py::TestScriptExecution::test_execute_invalid_template PASSED
test_skill_integration.py::TestScriptExecution::test_execute_missing_input PASSED
test_skill_integration.py::TestScriptExecution::test_execute_invalid_format PASSED
test_skill_integration.py::TestReferenceFiles::test_agent_read_templates_reference PASSED
test_skill_integration.py::TestReferenceFiles::test_agent_read_html_template PASSED
test_skill_integration.py::TestReferenceFiles::test_skill_references_not_loaded_by_default PASSED
test_skill_integration.py::TestIntegration::test_end_to_end_report_workflow PASSED
test_skill_integration.py::TestIntegration::test_multiple_report_formats PASSED
test_skill_integration.py::TestIntegration::test_csv_to_html_workflow PASSED
test_skill_integration.py::TestDockerBackend::test_script_runs_in_docker PASSED
test_skill_integration.py::TestDockerBackend::test_docker_script_access_volumes PASSED

===================== 22 passed, 1 skipped in 12.34s ======================
```

### Test Statistics

- **Total Tests**: 23 (22 active + 1 skipped)
- **Expected Duration**: 10-15 seconds (without Docker tests)
- **Expected Pass Rate**: 100%

## Troubleshooting

### Test Failures

#### Import Errors

**Error:** `ModuleNotFoundError: No module named 'agent'`

**Solution:**
- Ensure you're in the correct directory: `examples/skill-agent/`
- Install dependencies: `pip install -r requirements.txt`
- Check Python path includes the project root

#### File Not Found Errors

**Error:** `FileNotFoundError: test_data.json not found`

**Solution:**
- Verify test data files exist in `workspace/` directory
- Run from correct directory: `examples/skill-agent/`
- Check file permissions

#### Script Execution Failures

**Error:** `Script failed with exit code 1`

**Solution:**
- Verify script has execute permissions: `chmod +x skills/report-generator/scripts/generate_report.py`
- Check Python 3 is available: `python3 --version`
- Verify script syntax: `python3 -m py_compile skills/report-generator/scripts/generate_report.py`

#### Docker Tests Failing

**Error:** `Docker backend not available`

**Solution:**
- Start Docker daemon: `docker info`
- Build Docker image: `docker build -t skill-agent .`
- Check Docker permissions

### Skipped Tests

Some tests are marked with `@pytest.mark.skip` for specific reasons:

- `test_docker_backend_timeout` - Skipped by default to avoid long test runs

To run skipped tests:
```bash
pytest test_skill_integration.py --run-skipped
```

## Manual Testing

### Quick Manual Test

Test the skill manually without pytest:

```bash
cd examples/skill-agent

# Generate Markdown report
python3 skills/report-generator/scripts/generate_report.py \
  --input workspace/test_data.json \
  --output workspace/manual_test.md \
  --format markdown \
  --title "Manual Test Report"

# View output
cat workspace/manual_test.md

# Generate HTML report with template
python3 skills/report-generator/scripts/generate_report.py \
  --input workspace/test_data.csv \
  --output workspace/manual_test.html \
  --format html \
  --template skills/report-generator/references/report_template.html \
  --title "HTML Manual Test"

# Open in browser
open workspace/manual_test.html
```

### Test with Agent

Test through the agent interface:

```bash
cd examples/skill-agent
python main.py

# In agent prompt:
> "List available skills"
> "Generate a markdown report from workspace/test_data.json"
> "Create an HTML report with the template"
```

## Test Data Validation

### Verify Test Data Integrity

```bash
# Validate JSON
python3 -m json.tool workspace/test_data.json

# Check CSV structure
head workspace/test_data.csv

# Count records
python3 -c "import json; data = json.load(open('workspace/test_data.json')); print(f'Records: {len(data[\"records\"])}')"
```

### Create Custom Test Data

To test with your own data:

1. Create a JSON file with `records` array:
```json
{
  "records": [
    {"field1": "value1", "field2": 123},
    {"field1": "value2", "field2": 456}
  ]
}
```

2. Or create a CSV with headers:
```csv
field1,field2
value1,123
value2,456
```

3. Run tests with custom data:
```bash
python3 skills/report-generator/scripts/generate_report.py \
  --input your_data.json \
  --output output.md
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Test Report Generator Skill

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          cd examples/skill-agent
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          cd examples/skill-agent
          pytest test_skill_integration.py -v --cov=skills/report-generator
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Performance Benchmarks

Expected performance for test suite:

| Test Category | Tests | Avg Time | Notes |
|---------------|-------|----------|-------|
| Skill Discovery | 2 | 0.1s | Fast metadata parsing |
| Agent Tools | 5 | 1.0s | Depends on agent latency |
| Script Execution | 7 | 2.0s | File I/O operations |
| Reference Files | 3 | 0.5s | Small file reads |
| Integration | 3 | 2.0s | Multi-step workflows |
| Docker Backend | 2 | 5.0s | Container overhead |
| **Total** | **22** | **~11s** | Without network I/O |

## Best Practices

### Writing New Tests

1. **Follow naming convention**: `test_<what>_<scenario>`
2. **Use descriptive docstrings**: Explain what and why
3. **Clean up resources**: Use fixtures for setup/teardown
4. **Test one thing**: Each test should verify one behavior
5. **Use assertions wisely**: Clear failure messages

### Test Data Management

1. **Keep test data small**: 5-10 records sufficient
2. **Use realistic data**: Representative of actual use cases
3. **Version control test data**: Commit test files
4. **Document data structure**: Explain fields and values

### Maintaining Tests

1. **Run tests frequently**: Before commits, after changes
2. **Update tests with code**: Keep tests in sync
3. **Fix flaky tests**: Investigate intermittent failures
4. **Monitor performance**: Watch for slow tests

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Python unittest Documentation](https://docs.python.org/3/library/unittest.html)
- [Test-Driven Development Guide](https://testdriven.io/)
- [Docker Testing Best Practices](https://docs.docker.com/develop/dev-best-practices/)

## Support

For issues or questions:

1. Check this documentation first
2. Review test output and error messages
3. Verify test data and environment setup
4. Open an issue with details and logs

## Version History

- **1.0.0** (2024-01): Initial test suite with 22 active tests
