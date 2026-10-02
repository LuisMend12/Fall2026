# Baseline results — WikiCS

- 215603 clean undirected edges, edge homophily 0.654
- 55912 text-similar, cross-label candidate pairs (top-20 SBERT neighbours)
- mean ± std over 1 splits; GCN = 2-layer, 64 hidden, GloVe features

## Node classification (test set)

| model | attack | budget | acc | NLL | ECE | Brier | acc (touched) | acc (untouched) |
|---|---|---|---|---|---|---|---|---|
| MLP (no graph) | — | — | 0.680 ± 0.000 | 0.955 ± 0.000 | 0.049 ± 0.000 | 0.443 ± 0.000 | — | — |
| GCN | none | 0% | 0.720 ± 0.000 | 0.920 ± 0.000 | 0.097 ± 0.000 | 0.408 ± 0.000 | — | 0.720 ± 0.000 |
| GCN | text | 10% | 0.666 ± 0.000 | 1.087 ± 0.000 | 0.091 ± 0.000 | 0.481 ± 0.000 | 0.614 ± 0.000 | 0.918 ± 0.000 |
| GCN | random | 20% | 0.582 ± 0.000 | 1.322 ± 0.000 | 0.119 ± 0.000 | 0.570 ± 0.000 | 0.582 ± 0.000 | 0.571 ± 0.000 |

GCN at budget 0% is also the oracle defense (all fake edges removed) for every attacked row.

## Fake-edge detection (AUROC / AUPRC, fake = positive)

| attack | budget | text_sbert | text_glove | struct_jaccard | struct_gcn_disagree | naive_mix(sbert+gcn) | naive_mix(sbert+jaccard) |
|---|---|---|---|---|---|---|---|
| text | 10% | 0.252 / 0.057 | 0.492 / 0.086 | 0.859 / 0.402 | 0.626 / 0.111 | 0.415 / 0.070 | 0.588 / 0.098 |
| random | 20% | 0.889 / 0.631 | 0.853 / 0.532 | 0.960 / 0.810 | 0.722 / 0.288 | 0.872 / 0.546 | 0.969 / 0.882 |
