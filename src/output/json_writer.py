"""
JSON serialization for causal briefings.

Why JSON output?
- Machine-readable: APIs, dashboards, downstream processing
- Structured: Preserves all fields including nested causal_chain
- Portable: Can be consumed by any language/tool
- Versioned: Easy to diff changes over time

The JSON files in outputs/ serve as:
1. API responses for programmatic access
2. Input for visualization tools
3. Historical record of briefing evolution
4. Test fixtures for regression testing

Usage:
    writer = JSONWriter()
    filepath = writer.write(briefing, portfolio_id="P001")
    print(f"Wrote briefing to {filepath}")
"""

import json
from datetime import datetime
from pathlib import Path

from src.config import OUTPUTS_DIR
from src.schemas import CausalBriefing


class JSONWriter:
    """
    Writes CausalBriefing objects to JSON files.

    Output path pattern: outputs/{portfolio_id}_{timestamp}.json

    Usage:
        writer = JSONWriter()
        writer.write(briefing, portfolio_id="PORTFOLIO_001")
        # Creates: outputs/PORTFOLIO_001_2026-04-23T10-30-00.json
    """

    def __init__(self, output_dir: Path = OUTPUTS_DIR) -> None:
        """
        Args:
            output_dir: Directory where JSON files will be written.
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def write(self, briefing: CausalBriefing, portfolio_id: str) -> Path:
        """
        Serializes a briefing to a timestamped JSON file.

        Uses Pydantic's model_dump(mode='json') to ensure all types
        (Literals, nested models, floats) serialize correctly.

        Returns:
            Path to the written file.
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%S")
        filepath = self.output_dir / f"{portfolio_id}_{timestamp}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(briefing.model_dump(mode="json"), f, indent=2, ensure_ascii=False)

        return filepath
