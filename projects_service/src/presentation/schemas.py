from pydantic import BaseModel

class ProjectCreateSchema(BaseModel):
    name: str
    about: str
    is_private: bool
