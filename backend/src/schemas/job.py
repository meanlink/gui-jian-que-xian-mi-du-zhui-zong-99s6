from pydantic import BaseModel, Field
class JobInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    dataset_id: int
    params: dict = Field(default_factory=dict)
class RevokeInput(BaseModel):
    reason: str = Field(min_length=1, max_length=1000)
