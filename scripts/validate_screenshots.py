#!/usr/bin/env python3
"""Validate overlay screenshots using Claude's vision capability.

This script sends screenshots to Claude and asks it to validate them
against defined visual criteria. Used in CI to automatically verify
the overlay UI renders correctly.

Usage:
    python scripts/validate_screenshots.py screenshots/

Environment:
    ANTHROPIC_API_KEY: Required API key for Claude

Exit codes:
    0: All validations passed
    1: One or more validations failed
    2: Error (missing files, API error, etc.)
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Validation criteria for each test scenario
VALIDATION_CRITERIA: dict[str, dict[str, str | list[str]]] = {
    "01_empty": {
        "name": "Empty Overlay",
        "description": "Overlay window with no suggestions displayed",
        "must_have": [
            "A small window or transparent area visible",
            "No suggestion chips or text content",
            "Window should be minimal/empty",
        ],
        "must_not_have": [
            "Any keyboard shortcut text like 'Meta+' or 'Ctrl+'",
            "Any description text",
            "Multiple UI elements or chips",
        ],
    },
    "02_suggestions": {
        "name": "Demo Suggestions",
        "description": "Overlay showing two demo suggestions",
        "must_have": [
            "Two suggestion chips visible",
            "Text 'Meta+Tab' visible as a keyboard shortcut",
            "Text 'Meta+Left' visible as a keyboard shortcut",
            "Description text near each shortcut",
            "Dark/semi-transparent background on chips",
        ],
        "must_not_have": [
            "More than 3 chips",
            "Broken or garbled text",
        ],
    },
    "03_single": {
        "name": "Single Suggestion",
        "description": "Overlay showing exactly one suggestion",
        "must_have": [
            "Exactly one suggestion chip visible",
            "Text 'Meta+Tab' visible",
            "Description text visible",
        ],
        "must_not_have": [
            "Multiple chips",
            "Text 'Meta+Left'",
        ],
    },
    "04_max_three": {
        "name": "Maximum Suggestions (Truncation Test)",
        "description": "Overlay showing maximum of 3 suggestions (4 were provided, verifying truncation)",
        "must_have": [
            "Exactly three suggestion chips visible",
            "Text 'Meta+Tab' visible",
            "Text 'Meta+Left' visible",
            "Text 'Meta+Right' visible",
            "Chips arranged horizontally or in a row",
        ],
        "must_not_have": [
            "More than 3 chips",
            "Fourth suggestion visible (Meta+Down)",
            "Text 'Minimize' visible",
        ],
    },
    "05_cleared": {
        "name": "Cleared Suggestions",
        "description": "Overlay after suggestions have been cleared",
        "must_have": [
            "Empty or minimal window",
            "No suggestion chips visible",
        ],
        "must_not_have": [
            "Any keyboard shortcut text",
            "Any suggestion chips",
            "Previous suggestions still showing",
        ],
    },
}


@dataclass
class ValidationResult:
    """Result of validating a single screenshot."""

    test_id: str
    test_name: str
    passed: bool
    reasoning: str
    criteria_met: list[str]
    criteria_failed: list[str]
    confidence: str  # "high", "medium", "low"
    error: str | None = None


def encode_image_to_base64(image_path: Path) -> str:
    """Encode an image file to base64."""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def get_image_media_type(image_path: Path) -> str:
    """Get the media type for an image file."""
    suffix = image_path.suffix.lower()
    media_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return media_types.get(suffix, "image/png")


def build_validation_prompt(criteria: dict[str, str | list[str]]) -> str:
    """Build the validation prompt for Claude."""
    must_have = criteria.get("must_have", [])
    must_not_have = criteria.get("must_not_have", [])

    prompt = f"""You are validating a screenshot of the Shortcut Sage overlay UI.

**Context**: Shortcut Sage is a KDE Plasma desktop tool that suggests keyboard shortcuts based on user actions. The overlay displays suggestion "chips" - small UI elements showing a keyboard shortcut and description.

**Test Scenario**: {criteria['name']}
**Expected State**: {criteria['description']}

## Validation Criteria

### MUST HAVE (all required):
{chr(10).join(f"- {item}" for item in must_have)}

### MUST NOT HAVE (none allowed):
{chr(10).join(f"- {item}" for item in must_not_have)}

## Your Task

Analyze the screenshot and determine if it meets ALL the criteria above.

Respond with a JSON object in this exact format:
```json
{{
    "passed": true or false,
    "confidence": "high" or "medium" or "low",
    "reasoning": "Brief explanation of your assessment",
    "criteria_met": ["list", "of", "criteria", "that", "passed"],
    "criteria_failed": ["list", "of", "criteria", "that", "failed"]
}}
```

Be strict but fair. If you cannot clearly see something due to image quality, note it but don't fail on ambiguity. Focus on functional correctness over pixel-perfect styling."""

    return prompt


def validate_screenshot_with_claude(
    image_path: Path,
    test_id: str,
    api_key: str,
    max_retries: int = 3,
) -> ValidationResult:
    """Send a screenshot to Claude for validation with error handling."""
    import anthropic

    if test_id not in VALIDATION_CRITERIA:
        return ValidationResult(
            test_id=test_id,
            test_name=test_id,
            passed=False,
            reasoning=f"Unknown test ID: {test_id}",
            criteria_met=[],
            criteria_failed=["Unknown test scenario"],
            confidence="high",
            error=f"Unknown test ID: {test_id}",
        )

    criteria = VALIDATION_CRITERIA[test_id]

    # Encode image
    try:
        image_data = encode_image_to_base64(image_path)
        media_type = get_image_media_type(image_path)
    except Exception as e:
        return ValidationResult(
            test_id=test_id,
            test_name=criteria["name"],
            passed=False,
            reasoning=f"Failed to read image: {e}",
            criteria_met=[],
            criteria_failed=["Image read error"],
            confidence="high",
            error=str(e),
        )

    prompt = build_validation_prompt(criteria)

    # Call Claude API with retries
    client = anthropic.Anthropic(api_key=api_key)
    last_error = None

    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            # Extract text from all content blocks
            response_text = ""
            for block in message.content:
                if hasattr(block, "text"):
                    response_text += block.text

            # Parse response
            return parse_claude_response(response_text, test_id, criteria)

        except anthropic.APIConnectionError as e:
            last_error = f"Connection error: {e}"
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
        except anthropic.RateLimitError as e:
            last_error = f"Rate limit error: {e}"
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))  # Longer wait for rate limits
                continue
        except anthropic.APIStatusError as e:
            last_error = f"API error: {e.status_code} - {e.message}"
            break  # Don't retry on API errors
        except Exception as e:
            last_error = f"Unexpected error: {e}"
            break

    # All retries failed
    return ValidationResult(
        test_id=test_id,
        test_name=criteria["name"],
        passed=False,
        reasoning=f"API call failed after {max_retries} attempts: {last_error}",
        criteria_met=[],
        criteria_failed=["API error"],
        confidence="low",
        error=last_error,
    )


def parse_claude_response(
    response_text: str,
    test_id: str,
    criteria: dict[str, str | list[str]],
) -> ValidationResult:
    """Parse Claude's response into a ValidationResult."""
    try:
        # Find JSON in response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            result_data = json.loads(json_str)
        else:
            raise ValueError("No JSON found in response")

        return ValidationResult(
            test_id=test_id,
            test_name=criteria["name"],
            passed=result_data.get("passed", False),
            reasoning=result_data.get("reasoning", "No reasoning provided"),
            criteria_met=result_data.get("criteria_met", []),
            criteria_failed=result_data.get("criteria_failed", []),
            confidence=result_data.get("confidence", "low"),
        )

    except (json.JSONDecodeError, ValueError) as e:
        return ValidationResult(
            test_id=test_id,
            test_name=criteria["name"],
            passed=False,
            reasoning=f"Failed to parse response: {e}\nRaw: {response_text[:500]}",
            criteria_met=[],
            criteria_failed=["Response parsing error"],
            confidence="low",
            error=str(e),
        )


def find_screenshots(screenshots_dir: Path) -> dict[str, Path]:
    """Find and categorize screenshots by test ID.

    Selects the most recent screenshot for each test ID if duplicates exist.
    """
    screenshots: dict[str, Path] = {}

    for png_file in sorted(screenshots_dir.glob("overlay_test_*.png"), reverse=True):
        # Extract test ID from filename like "overlay_test_01_empty_20250107_123456.png"
        name = png_file.stem
        for test_id in VALIDATION_CRITERIA:
            if test_id in name and test_id not in screenshots:
                # Only take the first (most recent due to reverse sort)
                screenshots[test_id] = png_file
                break

    return screenshots


def print_result(result: ValidationResult) -> None:
    """Print a validation result."""
    status = "✅ PASS" if result.passed else "❌ FAIL"
    print(f"\n{'='*60}")
    print(f"{status} | {result.test_name} | Confidence: {result.confidence}")
    print(f"{'='*60}")
    print(f"Reasoning: {result.reasoning}")

    if result.error:
        print(f"\n⚠️ Error: {result.error}")

    if result.criteria_met:
        print(f"\n✓ Criteria met:")
        for c in result.criteria_met:
            print(f"  - {c}")

    if result.criteria_failed:
        print(f"\n✗ Criteria failed:")
        for c in result.criteria_failed:
            print(f"  - {c}")


def generate_report(results: list[ValidationResult], output_path: Path | None) -> dict:
    """Generate a JSON report of all validation results."""
    errors = [r for r in results if r.error]

    report = {
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "errors": len(errors),
            "pass_rate": f"{sum(1 for r in results if r.passed) / len(results) * 100:.1f}%" if results else "0%",
        },
        "results": [
            {
                "test_id": r.test_id,
                "test_name": r.test_name,
                "passed": r.passed,
                "confidence": r.confidence,
                "reasoning": r.reasoning,
                "criteria_met": r.criteria_met,
                "criteria_failed": r.criteria_failed,
                "error": r.error,
            }
            for r in results
        ],
    }

    if output_path:
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {output_path}")

    return report


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate overlay screenshots using Claude vision"
    )
    parser.add_argument(
        "screenshots_dir",
        type=Path,
        help="Directory containing screenshots to validate",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON report path",
        default=None,
    )
    parser.add_argument(
        "--api-key",
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
        default=None,
    )
    args = parser.parse_args()

    # Get API key
    import os
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        return 2

    # Check for anthropic package
    try:
        import anthropic  # noqa: F401
    except ImportError:
        print("ERROR: anthropic package not installed")
        print("Install with: pip install anthropic")
        return 2

    # Find screenshots
    if not args.screenshots_dir.exists():
        print(f"ERROR: Screenshots directory not found: {args.screenshots_dir}")
        return 2

    screenshots = find_screenshots(args.screenshots_dir)
    if not screenshots:
        print(f"ERROR: No screenshots found in {args.screenshots_dir}")
        print("Expected files like: overlay_test_01_empty_*.png")
        return 2

    print(f"Found {len(screenshots)} screenshots to validate:")
    for test_id, path in sorted(screenshots.items()):
        print(f"  - {test_id}: {path.name}")

    # Check for missing test scenarios
    missing = set(VALIDATION_CRITERIA.keys()) - set(screenshots.keys())
    if missing:
        print(f"\n⚠️ Missing screenshots for: {', '.join(sorted(missing))}")

    # Validate each screenshot
    results: list[ValidationResult] = []
    for test_id, screenshot_path in sorted(screenshots.items()):
        print(f"\nValidating {test_id}...")
        result = validate_screenshot_with_claude(screenshot_path, test_id, api_key)
        results.append(result)
        print_result(result)

    # Generate report
    report = generate_report(results, args.output)

    # Summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total:  {report['summary']['total']}")
    print(f"Passed: {report['summary']['passed']}")
    print(f"Failed: {report['summary']['failed']}")
    print(f"Errors: {report['summary']['errors']}")
    print(f"Rate:   {report['summary']['pass_rate']}")

    # Return exit code
    if report["summary"]["failed"] > 0:
        print("\n❌ Some validations failed!")
        return 1
    elif report["summary"]["errors"] > 0:
        print("\n⚠️ Some validations had errors!")
        return 2
    else:
        print("\n✅ All validations passed!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
