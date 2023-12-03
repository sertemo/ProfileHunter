from pydantic import BaseModel

class Lead(BaseModel):
    email:set[str]|None = None
    sector_busqueda:str|None = None
    nombre:str|None = None
    web:str|None = None
    pais:str|None = None