# E0 pilot study — selection-level results

Run: `20261021T161749Z` · commit `d362d53c56b7704d0fd164b9bc73b18bc56af6a7`

Generation-level metrics (cause accuracy, step correctness, citation precision) are not in this table — they need hand-labelled gold data (D-14), not yet collected.

| Method | Budget | Full coverage | Answered-incomplete (H1) | Insufficient | Mean tokens | Abstention P | Abstention R |
|---|---|---|---|---|---|---|---|
| topk | 500 | 67% | 33% | 0% | 435 | n/a | 0% |
| topk | 1000 | 83% | 17% | 0% | 973 | n/a | 0% |
| topk | 2000 | 83% | 17% | 0% | 1967 | n/a | 0% |
| knapsack | 500 | 8% | 92% | 0% | 460 | n/a | 0% |
| knapsack | 1000 | 42% | 58% | 0% | 980 | n/a | 0% |
| knapsack | 2000 | 67% | 33% | 0% | 1988 | n/a | 0% |
| mmr | 500 | 67% | 33% | 0% | 435 | n/a | 0% |
| mmr | 1000 | 67% | 33% | 0% | 970 | n/a | 0% |
| mmr | 2000 | 67% | 33% | 0% | 1938 | n/a | 0% |
| safety_slot | 500 | 67% | 33% | 0% | 435 | n/a | 0% |
| safety_slot | 1000 | 83% | 17% | 0% | 975 | n/a | 0% |
| safety_slot | 2000 | 83% | 17% | 0% | 1976 | n/a | 0% |
| requirement_complete | 500 | 83% | 0% | 17% | 300 | 100% | 100% |
| requirement_complete | 1000 | 83% | 0% | 17% | 636 | 100% | 100% |
| requirement_complete | 2000 | 83% | 0% | 17% | 1245 | 100% | 100% |
