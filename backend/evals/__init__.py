"""Evaluation suite: RAGAS-style metrics with a judge LLM, plus deterministic checks.

    python -m evals.run_evals              # all D01–D08, H01–H06, live pipeline + judge
    python -m evals.run_evals D01 H04      # selected scenarios
    python -m evals.run_evals --no-judge   # deterministic metrics only (no judge LLM cost)
"""
