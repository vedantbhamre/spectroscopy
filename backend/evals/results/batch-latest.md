# Batch validation report

11 of 14 cases ran · turns per case: 1

| Case | Status (turns) | Citation pass | Number hits | Repeated questions | Missing sections | Repairs | Sentences moved | Expectations | Model (turns) | Tokens |
|---|---|---|---|---|---|---|---|---|---|---|
| D01 | provisional → provisional | 9/10 (90%) | 2 | 0 | 0 | 0 | 1 | 1.0 |  | 0 |
| D02 | insufficient → insufficient | 0/0 | 1 | 0 | 1 | 1 | 0 | 0.25 |  | 0 |
| D03 | insufficient → insufficient | 8/8 (100%) | 2 | 0 | 0 | 2 | 4 | 1.0 |  | 0 |
| D04 | provisional → provisional | 4/9 (44%) | 2 | 0 | 1 | 1 | 3 | 1.0 |  | 0 |
| D05 | insufficient → insufficient | 3/7 (43%) | 5 | 0 | 0 | 0 | 4 | 1.0 |  | 0 |
| D06 | insufficient → provisional | 5/8 (62%) | 3 | 0 | 1 | 1 | 5 | 1.0 |  | 0 |
| D07 | insufficient → insufficient | 3/3 (100%) | 2 | 0 | 0 | 0 | 0 | 1.0 |  | 0 |
| D08 | insufficient → insufficient | 14/14 (100%) | 12 | 0 | 0 | 0 | 8 | 1.0 |  | 0 |
| H01 | provisional → provisional | 5/7 (71%) | 3 | 0 | 0 | 1 | 3 | 1.0 |  | 0 |
| H02 | provisional → provisional | 4/10 (40%) | 2 | 0 | 1 | 1 | 2 | 1.0 |  | 0 |
| H03 | FAILED: All LLM targets failed: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01jvw984shfvvrk7rcm2nj2e9f` service tier `on_demand` on tokens p | | | | | | | | | |
| H04 | FAILED: All LLM targets failed: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01jvw984shfvvrk7rcm2nj2e9f` service tier `on_demand` on tokens p | | | | | | | | | |
| H05 | FAILED: All LLM targets failed: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01jvw984shfvvrk7rcm2nj2e9f` service tier `on_demand` on tokens p | | | | | | | | | |
| H06 | out_of_scope | 6/6 (100%) | 1 | 0 | 0 | 0 | 2 | 1.0 | gpt-oss-120b via groq | 8,067 |

## Acceptance violations

- **D02** required sections present: turn 1: missing assumptions
- **D04** required sections present: turn 2: missing recommendation
- **D06** required sections present: turn 2: missing recommendation
- **H02** required sections present: turn 1: missing recommendation

## Golden expectation failures (turn 1)

- **D02**: decision status in ['provisional'] (got insufficient)
- **D02**: mentions one of ['nir']
- **D02**: mentions one of ['reflection']
