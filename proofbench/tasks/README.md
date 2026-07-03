# Tasks

Tasks are retrieved from miniF2F at test time. ProofBench stores theorem IDs, not benchmark statements or proofs.

`minif2f.py` loads `lean/src/test.lean`, extracts the selected theorem header, replaces the proof with `sorry`, and optionally loads the informal statement. Informal proofs are not passed to agents.

