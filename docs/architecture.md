# Architecture

Frontend (`React + Vite`) calls FastAPI backend using REST.

Flow:
1. Upload Python file in UI.
2. `POST /api/pipeline/analyze` parses AST and builds `PipelineIR`.
3. UI renders code + graph + issue list.
4. `POST /api/pipeline/optimize` rewrites code and returns diff and before/after metrics.
5. User accepts or rejects optimization.
