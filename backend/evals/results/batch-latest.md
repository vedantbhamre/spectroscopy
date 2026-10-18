# Batch validation report

11 of 14 cases ran · turns per case: 1

| Case | Status (turns) | Citation pass | Number hits | Repeated questions | Missing sections | Repairs | Sentences moved | Expectations | Model (turns) | Tokens |
|---|---|---|---|---|---|---|---|---|---|---|
| D01 | provisional | 16/16 (100%) | 1 | 0 | 0 | 0 | 0 | 1.0 | gpt-oss-120b via groq | 8,398 |
| D02 | provisional | 16/16 (100%) | 0 | 0 | 0 | 0 | 2 | 1.0 | gpt-oss-120b via groq | 9,297 |
| D03 | provisional | 12/12 (100%) | 0 | 0 | 0 | 0 | 0 | 1.0 | gpt-oss-120b via groq | 9,098 |
| D04 | provisional | 14/14 (100%) | 1 | 0 | 0 | 0 | 0 | 1.0 | gpt-oss-120b via groq | 8,462 |
| D05 | insufficient | 12/12 (100%) | 2 | 0 | 0 | 0 | 2 | 1.0 | gpt-oss-120b via groq | 8,941 |
| D06 | provisional | 9/9 (100%) | 0 | 0 | 0 | 0 | 0 | 1.0 | gpt-oss-120b via groq | 8,139 |
| D07 | insufficient | 0/0 | 0 | 0 | 0 | 0 | 0 | 1.0 | gpt-oss-20b via groq | 7,473 |
| D08 | provisional | 14/14 (100%) | 2 | 0 | 0 | 0 | 2 | 1.0 | gpt-oss-120b via groq | 8,770 |
| H01 | provisional → provisional | 5/7 (71%) | 3 | 0 | 0 | 1 | 3 | 1.0 |  | 0 |
| H02 | provisional → provisional | 4/10 (40%) | 2 | 0 | 1 | 1 | 2 | 1.0 |  | 0 |
| H03 | FAILED: All LLM targets failed: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01jvw984shfvvrk7rcm2nj2e9f` service tier `on_demand` on tokens p | | | | | | | | | |
| H04 | FAILED: All LLM targets failed: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01jvw984shfvvrk7rcm2nj2e9f` service tier `on_demand` on tokens p | | | | | | | | | |
| H05 | FAILED: All LLM targets failed: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01jvw984shfvvrk7rcm2nj2e9f` service tier `on_demand` on tokens p | | | | | | | | | |
| H06 | out_of_scope | 6/6 (100%) | 1 | 0 | 0 | 0 | 2 | 1.0 | gpt-oss-120b via groq | 8,067 |

## Acceptance violations

- **H02** required sections present: turn 1: missing recommendation

## Golden expectation failures (turn 1)

None.
