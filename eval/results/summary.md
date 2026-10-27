# E0 pilot study — selection-level results

Run: `20261025T122406Z` · commit `7657054e350b31323957fcb287a04ae25b218d88`

Generation-level metrics (cause accuracy, step correctness, citation precision) are not in this table — they need hand-labelled gold data (D-14), not yet collected.

| Method | Budget | Full coverage | Answered-incomplete (H1) | Insufficient | Mean tokens | Abstention P | Abstention R |
|---|---|---|---|---|---|---|---|
| topk | 500 | 59% | 41% | 0% | 433 | n/a | 0% |
| topk | 1000 | 62% | 38% | 0% | 967 | n/a | 0% |
| topk | 2000 | 66% | 34% | 0% | 1957 | n/a | 0% |
| knapsack | 500 | 0% | 100% | 0% | 454 | n/a | 0% |
| knapsack | 1000 | 9% | 91% | 0% | 986 | n/a | 0% |
| knapsack | 2000 | 28% | 72% | 0% | 1989 | n/a | 0% |
| mmr | 500 | 59% | 41% | 0% | 433 | n/a | 0% |
| mmr | 1000 | 59% | 41% | 0% | 963 | n/a | 0% |
| mmr | 2000 | 59% | 41% | 0% | 1947 | n/a | 0% |
| safety_slot | 500 | 59% | 41% | 0% | 433 | n/a | 0% |
| safety_slot | 1000 | 62% | 38% | 0% | 967 | n/a | 0% |
| safety_slot | 2000 | 69% | 31% | 0% | 1963 | n/a | 0% |
| requirement_complete | 500 | 75% | 0% | 25% | 302 | 100% | 100% |
| requirement_complete | 1000 | 75% | 0% | 25% | 346 | 100% | 100% |
| requirement_complete | 2000 | 75% | 0% | 25% | 370 | 100% | 100% |
