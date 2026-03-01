from pydantic import BaseModel, Field

class AnalyseRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=2000, description="Text to analyse")

class SummariseRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=2000, description="Text to summarise")