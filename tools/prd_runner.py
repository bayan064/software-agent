import os
from typing import Dict, Any

from agent.graph import app


def run_prd_text(prd_text: str, output_dir: str, language: str = "Python") -> Dict[str, Any]:
    """
    Run the agent with PRD text and write outputs to output_dir.
    Returns the graph result containing code, test_code, and test_result.
    """
    if not prd_text or not prd_text.strip():
        raise ValueError("PRD text is empty")

    print(f"PRD preview: {prd_text[:80]}")

    os.makedirs(output_dir, exist_ok=True)

    return app.invoke({
        "messages": [],
        "steps": 0,
        "code": "",
        "test_code": "",
        "test_result": {},
        "requirement": prd_text.strip(),
        "output_dir": output_dir,
        "language": language,
    })


def run_prd_file(prd_file: str, output_dir: str, language: str = "Python") -> Dict[str, Any]:
    """
    Read PRD from file and run the agent.
    """
    if not os.path.exists(prd_file):
        raise FileNotFoundError(f"PRD file not found: {prd_file}")

    with open(prd_file, "r", encoding="utf-8") as f:
        prd_text = f.read()

    return run_prd_text(prd_text, output_dir, language)
