"""
Comprehensive Integration Tests for Report Generator Skill

This test suite validates:
1. Skill discovery and metadata parsing
2. Script execution with various scenarios
3. Reference file usage and structure
4. End-to-end integration workflows
5. Output validation for all formats
"""

import pytest
import json
import subprocess
import yaml
from pathlib import Path
from typing import Dict, Any, List

# Note: Full agent integration tests would require running the actual agent,
# which is complex for unit testing. These tests focus on:
# - Skill structure and metadata validation
# - Script execution and output validation
# - File structure and content validation


# Test Configuration
SKILL_NAME = "report-generator"
SKILLS_DIR = Path(__file__).parent / "skills"
WORKSPACE_DIR = Path(__file__).parent / "workspace"
TEST_DATA_JSON = WORKSPACE_DIR / "test_data.json"
TEST_DATA_CSV = WORKSPACE_DIR / "test_data.csv"


# ============================================================================
# Test Category 1: Skill Discovery Tests
# ============================================================================

class TestSkillDiscovery:
    """Test that report-generator skill is discovered correctly."""

    def test_skill_file_exists(self):
        """Test that SKILL.md file exists."""
        skill_file = SKILLS_DIR / SKILL_NAME / "SKILL.md"
        assert skill_file.exists(), f"SKILL.md not found at {skill_file}"

    def test_skill_yaml_frontmatter(self):
        """Test that SKILL.md has valid YAML frontmatter."""
        skill_file = SKILLS_DIR / SKILL_NAME / "SKILL.md"
        content = skill_file.read_text()

        # Extract YAML frontmatter
        assert content.startswith('---'), "SKILL.md must start with YAML frontmatter"

        # Split by --- markers
        parts = content.split('---', 2)
        assert len(parts) >= 3, "SKILL.md must have YAML frontmatter enclosed in ---"

        yaml_content = parts[1].strip()
        metadata = yaml.safe_load(yaml_content)

        # Verify required fields
        assert metadata['name'] == SKILL_NAME
        assert 'description' in metadata
        assert metadata['version'] == '1.0.0'
        assert 'tags' in metadata
        assert 'reporting' in metadata['tags']
        assert 'data-processing' in metadata['tags']

    def test_skill_documentation_structure(self):
        """Test that skill documentation has expected sections."""
        skill_file = SKILLS_DIR / SKILL_NAME / "SKILL.md"
        content = skill_file.read_text()

        # Verify key sections exist
        required_sections = [
            'Overview',
            'When to Use',
            'How It Works',
            'Usage',
            'Output Formats',
            'Reference Files',
        ]

        for section in required_sections:
            assert section in content, f"Missing required section: {section}"

    def test_skill_directory_structure(self):
        """Test that skill has correct directory structure."""
        skill_dir = SKILLS_DIR / SKILL_NAME

        # Check required directories
        assert (skill_dir / "scripts").exists(), "scripts/ directory missing"
        assert (skill_dir / "references").exists(), "references/ directory missing"

        # Check required files
        assert (skill_dir / "scripts" / "generate_report.py").exists(), "generate_report.py missing"
        assert (skill_dir / "scripts" / "generate_report.py").is_file()
        assert (skill_dir / "references" / "TEMPLATES.md").exists(), "TEMPLATES.md missing"
        assert (skill_dir / "references" / "report_template.html").exists(), "report_template.html missing"


# ============================================================================
# Test Category 2: Skill Script Execution Tests
# ============================================================================

class TestScriptExecution:
    """Test script execution with various parameters and scenarios."""

    @pytest.fixture
    def script_path(self):
        """Get the script path."""
        return SKILLS_DIR / SKILL_NAME / "scripts" / "generate_report.py"

    def test_execute_basic_report_markdown(self, script_path):
        """Test basic report generation (JSON to Markdown)."""
        output_file = WORKSPACE_DIR / "test_report_basic.md"

        # Execute script
        result = subprocess.run(
            [
                'python3', str(script_path),
                '--input', str(TEST_DATA_JSON),
                '--output', str(output_file),
                '--format', 'markdown',
                '--title', 'Test Report'
            ],
            capture_output=True,
            text=True
        )

        # Verify exit code 0
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Check output file created
        assert output_file.exists()

        # Validate markdown format
        content = output_file.read_text()
        assert '# Test Report' in content
        assert 'Product A' in content
        assert 'Summary' in content

        # Clean up
        output_file.unlink()

    def test_execute_html_report(self, script_path):
        """Test HTML report generation from CSV."""
        output_file = WORKSPACE_DIR / "test_report_html.html"

        # Execute script
        result = subprocess.run(
            [
                'python3', str(script_path),
                '--input', str(TEST_DATA_CSV),
                '--output', str(output_file),
                '--format', 'html',
                '--title', 'HTML Test Report'
            ],
            capture_output=True,
            text=True
        )

        # Verify exit code 0
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Check HTML tags present
        content = output_file.read_text()
        assert '<!DOCTYPE html>' in content
        assert '<table>' in content
        assert 'HTML Test Report' in content
        assert 'Product A' in content

        # Clean up
        output_file.unlink()

    def test_execute_json_report(self, script_path):
        """Test JSON report with aggregations."""
        output_file = WORKSPACE_DIR / "test_report_json.json"

        # Execute script
        result = subprocess.run(
            [
                'python3', str(script_path),
                '--input', str(TEST_DATA_JSON),
                '--output', str(output_file),
                '--format', 'json',
                '--title', 'JSON Test Report'
            ],
            capture_output=True,
            text=True
        )

        # Verify exit code 0
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Parse JSON output
        with open(output_file) as f:
            data = json.load(f)

        # Check structure
        assert 'title' in data
        assert data['title'] == 'JSON Test Report'
        assert 'summary' in data
        assert 'data' in data

        # Check aggregated statistics
        assert 'total_records' in data['summary']
        assert data['summary']['total_records'] == 5
        assert 'statistics' in data['summary']

        # Verify numeric field statistics
        stats = data['summary']['statistics']
        assert 'value' in stats
        assert 'sum' in stats['value']
        assert stats['value']['sum'] == 895  # Sum of all values

        # Clean up
        output_file.unlink()

    def test_execute_with_template(self, script_path):
        """Test report generation with custom template."""
        template_path = SKILLS_DIR / SKILL_NAME / "references" / "report_template.html"
        output_file = WORKSPACE_DIR / "test_report_template.html"

        # Execute script with template
        result = subprocess.run(
            [
                'python3', str(script_path),
                '--input', str(TEST_DATA_JSON),
                '--output', str(output_file),
                '--format', 'html',
                '--template', str(template_path),
                '--title', 'Template Test Report'
            ],
            capture_output=True,
            text=True
        )

        # Verify exit code 0
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Check template was applied
        content = output_file.read_text()
        assert 'Template Test Report' in content
        assert '{{TITLE}}' not in content  # Placeholders should be replaced
        assert '{{DATA}}' not in content
        assert '{{SUMMARY}}' not in content
        assert '{{TIMESTAMP}}' not in content

        # Verify template styling is present
        assert 'gradient' in content or 'Segoe UI' in content

        # Clean up
        output_file.unlink()

    def test_execute_invalid_template(self, script_path):
        """Test error handling for missing template."""
        output_file = WORKSPACE_DIR / "test_report_bad_template.html"

        # Execute with non-existent template
        result = subprocess.run(
            [
                'python3', str(script_path),
                '--input', str(TEST_DATA_JSON),
                '--output', str(output_file),
                '--format', 'html',
                '--template', '/nonexistent/template.html'
            ],
            capture_output=True,
            text=True
        )

        # Verify non-zero exit code
        assert result.returncode == 3, "Expected exit code 3 for template error"

        # Check error message
        assert 'Template file not found' in result.stderr or 'Error' in result.stderr

    def test_execute_missing_input(self, script_path):
        """Test error handling for missing input file."""
        output_file = WORKSPACE_DIR / "test_report_no_input.md"

        # Execute with non-existent input
        result = subprocess.run(
            [
                'python3', str(script_path),
                '--input', str(WORKSPACE_DIR / 'nonexistent.json'),
                '--output', str(output_file),
                '--format', 'markdown'
            ],
            capture_output=True,
            text=True
        )

        # Verify exit code 1 (file not found)
        assert result.returncode == 1, "Expected exit code 1 for missing file"

        # Check error message
        assert 'not found' in result.stderr.lower()

    def test_execute_invalid_format(self, script_path):
        """Test error handling for invalid data format."""
        # Create malformed JSON file
        malformed_file = WORKSPACE_DIR / "malformed.json"
        malformed_file.write_text('{"invalid": json data}')

        output_file = WORKSPACE_DIR / "test_report_malformed.md"

        # Execute with malformed input
        result = subprocess.run(
            [
                'python3', str(script_path),
                '--input', str(malformed_file),
                '--output', str(output_file),
                '--format', 'markdown'
            ],
            capture_output=True,
            text=True
        )

        # Verify non-zero exit code
        assert result.returncode == 2, "Expected exit code 2 for format error"

        # Check error message
        assert 'Invalid' in result.stderr or 'format' in result.stderr

        # Clean up
        malformed_file.unlink()


# ============================================================================
# Test Category 3: Skill Reference File Tests
# ============================================================================

class TestReferenceFiles:
    """Test reference file structure and content."""

    def test_templates_md_exists(self):
        """Test TEMPLATES.md reference file exists."""
        templates_path = SKILLS_DIR / SKILL_NAME / "references" / "TEMPLATES.md"
        assert templates_path.exists(), "TEMPLATES.md not found"

    def test_templates_md_content(self):
        """Test TEMPLATES.md has required documentation."""
        templates_path = SKILLS_DIR / SKILL_NAME / "references" / "TEMPLATES.md"
        content = templates_path.read_text()

        # Check for required sections
        required_sections = [
            'Template Placeholders',
            '{{TITLE}}',
            '{{TIMESTAMP}}',
            '{{SUMMARY}}',
            '{{DATA}}',
            'Creating Custom Templates',
        ]

        for section in required_sections:
            assert section in content, f"Missing section in TEMPLATES.md: {section}"

    def test_html_template_exists(self):
        """Test HTML template file exists."""
        template_path = SKILLS_DIR / SKILL_NAME / "references" / "report_template.html"
        assert template_path.exists(), "report_template.html not found"

    def test_html_template_has_placeholders(self):
        """Test HTML template contains all required placeholders."""
        template_path = SKILLS_DIR / SKILL_NAME / "references" / "report_template.html"
        content = template_path.read_text()

        # Verify required placeholders
        required_placeholders = ['{{TITLE}}', '{{DATA}}', '{{SUMMARY}}', '{{TIMESTAMP}}']
        for placeholder in required_placeholders:
            assert placeholder in content, f"Missing placeholder in template: {placeholder}"

    def test_html_template_valid_structure(self):
        """Test HTML template has valid HTML structure."""
        template_path = SKILLS_DIR / SKILL_NAME / "references" / "report_template.html"
        content = template_path.read_text()

        # Check basic HTML structure
        assert '<!DOCTYPE html>' in content or '<html' in content
        assert '<head>' in content
        assert '<body>' in content
        assert '<style>' in content  # Should have embedded CSS


# ============================================================================
# Test Category 4: Integration Tests
# ============================================================================

class TestIntegration:
    """Test complete workflows and multi-format scenarios."""

    @pytest.fixture
    def script_path(self):
        """Get the script path."""
        return SKILLS_DIR / SKILL_NAME / "scripts" / "generate_report.py"

    def test_end_to_end_workflow_validation(self, script_path):
        """Test complete workflow: verify inputs → execute → validate output."""
        output_file = WORKSPACE_DIR / "test_e2e_report.md"

        # Step 1: Verify input data exists
        assert TEST_DATA_JSON.exists(), "Test data file not found"

        # Step 2: Execute report generation
        result = subprocess.run(
            [
                'python3', str(script_path),
                '--input', str(TEST_DATA_JSON),
                '--output', str(output_file),
                '--format', 'markdown'
            ],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Step 3: Verify output exists and is valid
        assert output_file.exists()
        content = output_file.read_text()
        assert 'Product A' in content
        assert 'Summary' in content
        assert 'Total Records' in content

        # Clean up
        output_file.unlink()

    def test_multiple_report_formats(self, script_path):
        """Test generating reports in all supported formats."""
        formats = {
            'markdown': 'test_multi_format.md',
            'html': 'test_multi_format.html',
            'json': 'test_multi_format.json'
        }

        for fmt, filename in formats.items():
            output_file = WORKSPACE_DIR / filename

            # Generate report
            result = subprocess.run(
                [
                    'python3', str(script_path),
                    '--input', str(TEST_DATA_JSON),
                    '--output', str(output_file),
                    '--format', fmt
                ],
                capture_output=True,
                text=True
            )

            # Verify success
            assert result.returncode == 0, f"Failed to generate {fmt} report"
            assert output_file.exists()

            # Validate format-specific content
            content = output_file.read_text()
            if fmt == 'markdown':
                assert '# ' in content or '## ' in content
            elif fmt == 'html':
                assert '<html>' in content or '<!DOCTYPE' in content
            elif fmt == 'json':
                data = json.loads(content)
                assert 'title' in data

            # Clean up
            output_file.unlink()

    def test_csv_to_html_workflow(self, script_path):
        """Test CSV input to HTML output with template."""
        template_path = SKILLS_DIR / SKILL_NAME / "references" / "report_template.html"
        output_file = WORKSPACE_DIR / "test_csv_html.html"

        # Generate HTML report from CSV with template
        result = subprocess.run(
            [
                'python3', str(script_path),
                '--input', str(TEST_DATA_CSV),
                '--output', str(output_file),
                '--format', 'html',
                '--template', str(template_path),
                '--title', 'CSV to HTML Report'
            ],
            capture_output=True,
            text=True
        )

        # Verify success
        assert result.returncode == 0, f"Failed: {result.stderr}"

        # Verify proper CSV parsing and HTML generation
        content = output_file.read_text()
        assert 'CSV to HTML Report' in content
        assert 'Product A' in content  # From CSV
        assert '<table>' in content
        assert 'gradient' in content  # From template

        # Clean up
        output_file.unlink()


# ============================================================================
# Test Category 5: Data Validation Tests
# ============================================================================

class TestDataValidation:
    """Test data file validation and edge cases."""

    def test_json_test_data_valid(self):
        """Test that JSON test data is valid."""
        with open(TEST_DATA_JSON) as f:
            data = json.load(f)

        # Verify structure
        assert 'records' in data
        assert isinstance(data['records'], list)
        assert len(data['records']) == 5

        # Verify record structure
        for record in data['records']:
            assert 'id' in record
            assert 'name' in record
            assert 'value' in record
            assert 'category' in record

    def test_csv_test_data_valid(self):
        """Test that CSV test data is valid."""
        assert TEST_DATA_CSV.exists()
        content = TEST_DATA_CSV.read_text()

        # Verify header row
        lines = content.strip().split('\n')
        assert len(lines) == 6  # Header + 5 data rows
        assert lines[0] == 'id,name,value,category,quantity'

    def test_json_and_csv_data_equivalent(self):
        """Test that JSON and CSV contain same data."""
        # Load JSON
        with open(TEST_DATA_JSON) as f:
            json_data = json.load(f)

        # Load CSV
        csv_lines = TEST_DATA_CSV.read_text().strip().split('\n')[1:]  # Skip header

        # Compare counts
        assert len(json_data['records']) == len(csv_lines)


# ============================================================================
# Helper Functions and Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_test_outputs():
    """Clean up any test output files before and after tests."""
    # Before test
    yield
    # After test - clean up generated test files, but NOT test_data.json or test_data.csv
    for pattern in ['test_report_*.md', 'test_report_*.html', 'test_report_*.json',
                    'test_e2e_*.md', 'test_multi_*.md', 'test_multi_*.html', 'test_multi_*.json',
                    'docker_*.md', 'docker_*.html', 'malformed.json']:
        for file in WORKSPACE_DIR.glob(pattern):
            try:
                file.unlink()
            except Exception:
                pass


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
