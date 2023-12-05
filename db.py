import sqlite3
from threading import Lock
from rutas import NOMBRE_DB_SQLITE
## SQLITE ##

# NOMBRE_DB_SQLITE = "db/hunts.db"


class SQLManager:
    """Gestiona la conexion con la db y adquiere y libera el Lock
    """
    def __init__(self, db_filename):
        self.db_filename = db_filename
        self.lock = Lock() # Si están varios hilos abiertos

    def __enter__(self):
        self.lock.acquire()
        self.conn = sqlite3.connect(self.db_filename)        
        return self.conn.cursor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()
        self.lock.release()

class SQLContext:
    def __init__(self, *, nombre_tabla:str, db_filename=NOMBRE_DB_SQLITE) -> None:
        self.db_filename = db_filename
        self.tabla = nombre_tabla

    def get_table(self) -> list[tuple]:
        """Devuelve una lista de tuplas conteniendo cada tupla los campos de cada columna \
            para cada registro de la tabla dada"""
        with SQLManager(self.db_filename) as c:
            results = c.execute(f"""SELECT * from {self.tabla}""")
            return results.fetchall()
    
    def get_number_of_records(self) -> int:
        """Devuelve el número de registros

        Returns
        -------
        int
            _description_
        """
        return len(self.get_table())
        
    def show_table_columns(self) -> list[str]:
        """Devuelve una lista con el nombre de las columnas

        Returns
        -------
        list[str]
            _description_
        """
        with SQLManager(self.db_filename) as c:
            c.execute(f"PRAGMA table_info({self.tabla})")
            info = c.fetchall()
            column_names = [column[1] for column in info]
            return column_names
        
    def add_column(self, *, nombre_columna: str, tipo_dato: str) -> None:
        with SQLManager(self.db_filename) as c:
            c.execute(f"ALTER TABLE {self.tabla} ADD COLUMN {nombre_columna} {tipo_dato}")

    def add_column_nullable(self, *, nombre_columna: str, tipo_dato: str) -> None:
        with SQLManager(self.db_filename) as c:
            c.execute(f"ALTER TABLE {self.tabla} ADD COLUMN {nombre_columna} {tipo_dato} NULL")
    
    def insert_one(self, columnas:dict) -> None:
        """inserta un registro en la tabla dada."""
        with SQLManager(self.db_filename) as c:
            query = f"""INSERT INTO {self.tabla} ({", ".join(columnas.keys())}) VALUES ({", ".join('?' * len(columnas))})"""
            c.execute(query, tuple(columnas.values()))

    def find_one(self, *, campo_buscado:str, valor_buscado:str) -> list:
        """Devuelve todos los campos de la fila cuyo campo coincide con el valor buscado

        Parameters
        ----------
        campo_buscado : str
            _description_
        valor_buscado : str
            _description_

        Returns
        -------
        _type_
            _description_
        """
        with SQLManager(self.db_filename) as c:
            consulta = f"SELECT * FROM {self.tabla} WHERE {campo_buscado} = ?"
            results = c.execute(consulta, (valor_buscado,))
            return results.fetchone()
        
    def find_one_field(self, *, campo_buscado:str, valor_buscado:str, campo_a_retornar:str):
        """Devuelve todos el campo especificado de la fila cuyo campo coincide con el valor buscado

        Parameters
        ----------
        campo_buscado : str
            _description_
        valor_buscado : str
            _description_

        Returns
        -------
        _type_
            _description_
        """
        with SQLManager(self.db_filename) as c:
            consulta = f"SELECT {campo_a_retornar} FROM {self.tabla} WHERE {campo_buscado} = ?"
            results = c.execute(consulta, (valor_buscado,))            
            if (output:=results.fetchone()) is not None:
                return output[0]
            else:
                return output
    
    @classmethod
    def create_table(cls, *, db_filename:str, nombre_tabla:str, columnas:tuple[str]) -> None:
        with SQLManager(db_filename) as c:
            c.execute(f"""
                    CREATE TABLE IF NOT EXISTS {nombre_tabla} ({", ".join(columnas)})""") ## He quitado el IF NOT EXISTS
        return cls
    
    def delete_table(self) -> None:
        with SQLManager(self.db_filename) as c:
            c.execute(f"DELETE from {self.tabla}")
            c.execute(f"DELETE FROM sqlite_sequence WHERE name = '{self.tabla}'") # Para reiniciar el autoincremental

    def delete_one(self, *, campo_buscado:str, valor_buscado:str) -> None:
        with SQLManager(self.db_filename) as c:
            consulta = f"DELETE FROM {self.tabla} WHERE {campo_buscado} = ?"
            c.execute(consulta, (valor_buscado,))

    def update_one(self, *, columna_a_actualizar:str, nuevo_valor: str, campo_buscado:str, valor_buscado:str) -> None:
        with SQLManager(self.db_filename) as c:
            consulta = f"""UPDATE {self.tabla} SET {columna_a_actualizar} = ? WHERE {campo_buscado} = ?"""
            c.execute(consulta, (nuevo_valor, valor_buscado))

    def update_many(self, *, campo_buscado:str, valor_campo_buscado:str, columnas_a_actualizar:list[str], nuevos_valores:list[str|int]) -> None:
        assert len(columnas_a_actualizar) == len(nuevos_valores), "Las dos listas deben tener el mismo tamaño"
        # Comprobamos que las columnas a actualizar estén en la base de datos
        columnas = self.show_table_columns()
        for col in columnas_a_actualizar:
            if col not in columnas:
                raise ValueError(f"La columna {col} no existe en la base de datos")
        with SQLManager(self.db_filename) as c:
            consulta = f"""
            UPDATE {self.tabla} 
            SET {", ".join(col + ' = ?' for col in columnas_a_actualizar)}
            WHERE {campo_buscado} = ?;
            """
            c.execute(consulta, (*nuevos_valores, valor_campo_buscado))

if __name__ == '__main__':
    """ SQLContext.create_table(
        db_filename=NOMBRE_DB_SQLITE,
        nombre_tabla='busquedas',
        columnas=(
            'id INTEGER PRIMARY KEY AUTOINCREMENT',
            'sector TEXT',
            'pagina INTEGER',
            'lista INTEGER',
            'elemento INTEGER',
            'paginas_totales INTEGER',
            'listas_totales INTEGER',
            'elementos_totales INTEGER',
            'fecha TEXT',
        )
    ) """
    db_busquedas = SQLContext(nombre_tabla='busquedas')
    #db_busquedas.delete_table()
    """  db_busquedas.add_column_nullable(
        nombre_columna="empresas_totales",
        tipo_dato="INTEGER"
    ) """
    print(db_busquedas.show_table_columns())
    print(db_busquedas.get_table())
    print(db_busquedas.get_number_of_records())
    