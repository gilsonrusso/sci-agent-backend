from pydantic import BaseModel


class CompileRequest(BaseModel):
    content: str
