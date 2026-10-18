# Batch validation report

10 of 14 cases ran · turns per case: 2

| Case | Status (turns) | Citation pass | Number hits | Repeated questions | Missing sections | Repairs | Sentences moved | Expectations | Time |
|---|---|---|---|---|---|---|---|---|---|
| D01 | provisional → provisional | 9/10 (90%) | 2 | 0 | 0 | 0 | 1 | 1.0 | 34 s |
| D02 | insufficient → insufficient | 0/0 | 1 | 0 | 1 | 1 | 0 | 0.25 | 124 s |
| D03 | insufficient → insufficient | 8/8 (100%) | 2 | 0 | 0 | 2 | 4 | 1.0 | 87 s |
| D04 | provisional → provisional | 4/9 (44%) | 2 | 0 | 1 | 1 | 3 | 1.0 | 131 s |
| D05 | insufficient → insufficient | 3/7 (43%) | 5 | 0 | 0 | 0 | 4 | 1.0 | 93 s |
| D06 | insufficient → provisional | 5/8 (62%) | 3 | 0 | 1 | 1 | 5 | 1.0 | 105 s |
| D07 | insufficient → insufficient | 3/3 (100%) | 2 | 0 | 0 | 0 | 0 | 1.0 | 104 s |
| D08 | insufficient → insufficient | 14/14 (100%) | 12 | 0 | 0 | 0 | 8 | 1.0 | 45 s |
| H01 | provisional → provisional | 5/7 (71%) | 3 | 0 | 0 | 1 | 3 | 1.0 | 125 s |
| H02 | provisional → provisional | 4/10 (40%) | 2 | 0 | 1 | 1 | 2 | 1.0 | 117 s |
| H03 | FAILED: All LLM targets failed: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01jvw984shfvvrk7rcm2nj2e9f` service tier `on_demand` on tokens p | | | | | | | | 15 s |
| H04 | FAILED: All LLM targets failed: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01jvw984shfvvrk7rcm2nj2e9f` service tier `on_demand` on tokens p | | | | | | | | 12 s |
| H05 | FAILED: All LLM targets failed: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01jvw984shfvvrk7rcm2nj2e9f` service tier `on_demand` on tokens p | | | | | | | | 7 s |
| H06 | FAILED: All LLM targets failed: Error code: 429 - {'error': {'message': 'Rate limit reached for model `openai/gpt-oss-20b` in organization `org_01jvw984shfvvrk7rcm2nj2e9f` service tier `on_demand` on tokens p | | | | | | | | 0 s |

## Acceptance violations

- **D02** required sections present: turn 1: missing assumptions
- **D04** required sections present: turn 2: missing recommendation
- **D06** required sections present: turn 2: missing recommendation
- **H02** required sections present: turn 1: missing recommendation

## Golden expectation failures (turn 1)

- **D02**: decision status in ['provisional'] (got insufficient)
- **D02**: mentions one of ['nir']
- **D02**: mentions one of ['reflection']
