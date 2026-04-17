"""termsheet-extraction-eval — reference eval harness for LLM term-sheet extraction."""
from termsheet_eval.compare.result import ComparisonResult
from termsheet_eval.pipeline import Pipeline, PipelineConfig

__version__ = "0.1.0"
__all__ = ["ComparisonResult", "Pipeline", "PipelineConfig"]
