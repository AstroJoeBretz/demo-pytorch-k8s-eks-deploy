This directory needs `model.py` and `model_artifacts/model.pt` from
`../../model/` to run `torch-model-archiver` (see repo root README).
They were copied in directly during development; wire that as a real
build step instead of hand-copying, so there's one source of truth.
