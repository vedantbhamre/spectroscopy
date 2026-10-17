# Eval run 2026-10-17T17:14:08+00:00

Mode: live pipeline · judge: openai:gpt-4o (JUDGE_OPENAI_API_KEY) · judge calls: 46

| Scenario | Status | citation_validity | grounding | clarification | feasibility | expectations | faithfulness | answer_relevancy | context_precision | context_recall | answer_correctness | Time |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D01 | provisional | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.71 | 0.80 | 0.93 | 0.60 | 0.62 | 8.8s |
| D02 | provisional | 1.00 | 0.50 | 1.00 | 1.00 | 1.00 | 0.83 | 0.80 | 0.86 | 0.11 | 0.67 | 7.8s |
| D03 | provisional | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.57 | 0.95 | 0.68 | – | – | 8.0s |
| D04 | insufficient | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.71 | 0.85 | 0.85 | – | – | 14.3s |
| D05 | insufficient | 1.00 | – | 1.00 | 1.00 | 1.00 | 0.67 | 0.70 | 0.78 | – | – | 5.9s |
| D06 | insufficient | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.75 | 0.43 | 0.73 | – | – | 8.2s |
| D07 | insufficient | 1.00 | – | 1.00 | 1.00 | 0.50 | 0.50 | 0.80 | 0.81 | – | – | 9.4s |
| D08 | insufficient | 1.00 | – | 1.00 | 1.00 | 1.00 | 0.67 | 0.60 | 0.94 | – | – | 7.9s |
| H01 | insufficient | 1.00 | – | 1.00 | 1.00 | 1.00 | 0.50 | 0.90 | 0.42 | – | – | 6.7s |
| H02 | provisional | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 0.83 | 0.90 | 0.82 | – | – | 8.5s |
| H03 | insufficient | 1.00 | – | 1.00 | 1.00 | 1.00 | 0.33 | 0.60 | 0.82 | – | – | 7.5s |
| H04 | insufficient | 1.00 | – | 1.00 | 1.00 | 1.00 | 1.00 | 0.80 | 0.92 | – | – | 6.2s |
| H05 | insufficient | 1.00 | – | 1.00 | 1.00 | 1.00 | 1.00 | 0.40 | 0.80 | – | – | 5.7s |
| H06 | out_of_scope | 1.00 | – | 1.00 | 1.00 | 1.00 | 1.00 | 0.80 | 0.95 | – | – | 6.5s |

## Averages

| Metric | All | Development | Evaluation |
|---|---|---|---|
| citation_validity | 1.00 | 1.00 | 1.00 |
| grounding | 0.92 | 0.90 | 1.00 |
| clarification | 1.00 | 1.00 | 1.00 |
| feasibility | 1.00 | 1.00 | 1.00 |
| expectations | 0.96 | 0.94 | 1.00 |
| faithfulness | 0.72 | 0.68 | 0.78 |
| answer_relevancy | 0.74 | 0.74 | 0.73 |
| context_precision | 0.81 | 0.82 | 0.79 |
| context_recall | 0.36 | 0.36 | – |
| answer_correctness | 0.65 | 0.65 | – |

## Expectation failures

- **D07**: mentions one of ['mir', 'atr', 'raman', 'nir']

## Claims the judge found unsupported by the retrieved pages

- **D01**: Potential interference from excipients in the blend.
- **D01**: Need for matrix-specific calibration models.
- **D02**: There is a risk of potential interference from product temperature and texture variations.
- **D03**: Monitor protein concentration in a whey stream with varying turbidity using spectroscopy.
- **D03**: Raman shift typically 200–3400 cm-1 with excitation around 785 nm.
- **D03**: Potential interference from turbidity affecting spectral measurements.
- **D04**: In situ spectroscopy is used for monitoring glucose and lactate in cell culture.
- **D04**: Calibration complexity arises due to medium and cell population changes.
- **D05**: Undefined measurement targets may lead to inappropriate method selection.
- **D06**: Potential challenges in fiber coupling efficiency over long distances.
- **D07**: Unspecified measurement variable may lead to inappropriate method selection.
- **D07**: High temperature and material build-up could affect probe performance.
- **D08**: The study aims to compare MIR ATR and fluorescence for classifying biological tissues.
- **D08**: The combination's benefit is a hypothesis to test.
- **H01**: Each method should be evaluated independently before considering a combination.
- **H01**: Existing NIR calibration may not transfer to the new blend.
- **H01**: Adding Raman does not guarantee the old calibration's validity.
- **H02**: NIR (Transmission) is suitable for relatively clear whey stream, allowing deeper light penetration.
- **H03**: Fluorescence spectroscopy requires a defined fluorescent target for accurate measurement of glucose and biomass.
- **H03**: Lack of a defined fluorescent target may lead to inaccurate measurements.
