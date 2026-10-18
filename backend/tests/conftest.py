"""Tests run offline: the API's safety gate uses the rule engine even when backend/.env has real keys.

Tests of the LLM gate build LLMGuard directly with a scripted chat().
"""

import os

os.environ["GUARD_MODE"] = "rules"
# Keyword + routing retrieval only, so tests do not load the embedding model; test_semantic_retrieval enables it.
os.environ["EMBEDDINGS"] = "off"
