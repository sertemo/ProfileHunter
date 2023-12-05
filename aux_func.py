
from models import Lead
from db import SQLContext

import unicodedata
from colorama import Fore
import re
from typing import Literal, Callable
import tldextract as tld
import pandas as pd
from pathlib import Path
from datetime import datetime
import pytz

formato_dia_hora = "%d-%m-%Y %H:%M:%S"
formato_dia = "%d-%m-%Y"
fecha_string:Callable = lambda formato:datetime.strftime(datetime.now(tz=pytz.timezone('Europe/Madrid')),format=formato)

def quitar_tildes(texto:str) -> str:
    """Quita tíldes y acentos especiales pero deja la ñ y la ü del castellano

    Parameters
    ----------
    texto : str
        _description_

    Returns
    -------
    str
        _description_
    """
    texto_normalizado = unicodedata.normalize('NFD', texto)
    texto_sin_tildes = ''.join(c for c in texto_normalizado if unicodedata.category(c) != 'Mn' or c in ['\u0303', '\u0308'])
    return unicodedata.normalize('NFC', texto_sin_tildes)

# Función para la lógica de insertar en db
def handle_insert_db(
        db_handler:SQLContext, 
        resume_flag:bool,
        sector:str,
        finish_pag:int,
        finish_lista:int,
        finish_elemento:int,
        paginas_totales:int,
        listas_totales:int,
        elementos_totales:int,
        empresas_totales:int) -> None:
    """Inserta o actualiza un registro en db en función de si su búsqueda ya se había empezado a realizar

    Parameters
    ----------
    db_handler : SQLContext
        _description_
    resume_flag : bool
        _description_
    sector : str
        _description_
    finish_pag : int
        _description_
    finish_lista : int
        _description_
    finish_elemento : int
        _description_
    paginas_totales : int
        _description_
    listas_totales : int
        _description_
    elementos_totales : int
        _description_
    """
    col_act = ['pagina', 'lista', 'elemento', 'paginas_totales', 'listas_totales', 'elementos_totales', 'fecha', "empresas_totales"]
    new_values = [finish_pag, finish_lista, finish_elemento, paginas_totales, listas_totales, elementos_totales, fecha_string(formato_dia_hora), empresas_totales]
    sector = sector.lower().strip() # Siempre en minúsculas y sin espacios
    
    if resume_flag:
        # Hay que actualizar los campos en db
        db_handler.update_many(
            campo_buscado='sector',
            valor_campo_buscado=sector, 
            columnas_a_actualizar=col_act,
            nuevos_valores=new_values,
        )
    else:
        # Hay que insertar nuevo registro
        insert_dict = {k: v for k,v in zip(col_act, new_values)}
        insert_dict['sector'] = sector
        db_handler.insert_one(insert_dict)

# Función que va a manejar los loggings o prints en función de si se le pasan kwargs
# Los kwargs serán funciones de Flet
def handle_log_print(msg:str, **kwargs) -> None:
    """Maneja la impresión en log o por pantalla haciendo print o llamando a una función de un front.\n
    color:\n 
        'verde': Fore.GREEN,\n
        'verde_fuerte': Fore.LIGHTGREEN_EX,\n
        'rojo': Fore.RED,\n
        'rojo_fuerte': Fore.LIGHTRED_EX,\n
        'amarillo': Fore.LIGHTYELLOW_EX,\n
        'magenta': Fore.LIGHTMAGENTA_EX,\n
        'cian': Fore.LIGHTCYAN_EX,\n

    Parameters
    ----------
    msg : str
        _description_
    """
    map_color_print = {
        'verde': (Fore.GREEN,'#008000'),
        'verde_fuerte': (Fore.LIGHTGREEN_EX, '#00ff00'),
        'rojo': (Fore.RED, '#8B0000'),
        'rojo_fuerte': (Fore.LIGHTRED_EX, '#ff0000'),
        'amarillo': (Fore.LIGHTYELLOW_EX, '#F7E940'),
        'magenta': (Fore.LIGHTMAGENTA_EX, '#CF3476'),
        'cian': (Fore.LIGHTCYAN_EX, '#00A6D6'),
        }
    color = kwargs.get('color', 'azul')
    funcion = kwargs.get('log_func', print)
    argumento = kwargs.get('text_class', "print")
    if isinstance(argumento, str):
        argumento = map_color_print[color][0] + f'{msg}'
        funcion(argumento)
    else:
        funcion(argumento(msg=msg, color=map_color_print[color][1]))
        kwargs.get("page").update()

def merge_excels(excels_path:Path) -> None:
    """Concatena todos los excels de la carpeta /data en uno solo
    """
    dataframes = []
    for archivo in excels_path.iterdir():
        if archivo.name.endswith('.xlsx') or archivo.name.endswith('.xls'):
            ruta_archivo = excels_path / archivo.name
            df = pd.read_excel(ruta_archivo)
            dataframes.append(df)

    df_global = pd.concat(dataframes, ignore_index=True)
    try:
        df_global.to_excel(f"todos_los_contactos [{fecha_string(formato_dia)}].xlsx", index=False)
        print(f"Excels en {excels_path.name} fusionados con éxito.")
    except:
        print("Se ha producido un problema al fusionar los excels.")

def delete_data(excels_path:Path) -> None:
    """Borra todos los excels de la carpeta /data
    """
    for archivo in excels_path.iterdir():
        if archivo.name.endswith('.xlsx') or archivo.name.endswith('.xls'):
            archivo.unlink()

def extraer_correos(texto:str, prohibidos:list[str]=['customer.service@visable.com']) -> set[str]:
    """Extrae una lista con todos los correos del texto.
    Realiza un filtrado apra excluir imágenes que hayan podido dar falsos positivos

    Parameters
    ----------
    texto : str
        _description_

    Returns
    -------
    set[str]
        _description_
    """
    EMAIL_REGEX = r'(?<![_\w.-])([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})(?![\w.-])'
    emails_encontrados:list[str] = re.findall(EMAIL_REGEX, texto)
    # Filtrar los falsos positivos que pueden haber coincidido con nombres de archivos de imagen
    emails_filtrados = {email for email in emails_encontrados if not email.lower().endswith(('.jpg', '.png', '.gif', '.webp'))} 
    # Filtramos los emails prohibidosd
    emails_filtrados = {email for email in emails_filtrados if email not in prohibidos}
    
    return emails_filtrados

def extraer_dominio(url:str) -> str:
    """Dada una URL devuelve solo el nombre de la página

    Parameters
    ----------
    url : str
        _description_

    Returns
    -------
    str
        _description_
    """

    extracted = tld.extract(url)
    page_name = extracted.domain
    return page_name

def asignar_idioma(pais:str) -> Literal['en', 'fr', 'es']:
    """Dado el pais, devuelve su denominación del idioma en 2 letras

    Returns
    -------
    _type_
        _description_
    """
    paises_hispanohablantes = ['España', 'México', 'Colombia', 'Argentina', 
                                'Perú', 'Venezuela', 'Chile', 'Guatemala', 
                                'Ecuador', 'Bolivia', 'Cuba', 'República Dominicana', 
                                'Honduras', 'Paraguay', 'El Salvador', 'Nicaragua', 
                                'Costa Rica', 'Puerto Rico', 'Panamá', 'Uruguay', 'Guinea Ecuatorial',
                                'Spain', 'Mexico', 'Colombia', 'Argentina', 'Peru', 'Venezuela', 'Chile', 
                                'Guatemala', 'Ecuador', 'Bolivia', 'Cuba', 'Dominican Republic', 'Honduras', 
                                'Paraguay', 'El Salvador', 'Nicaragua', 'Costa Rica', 'Puerto Rico', 'Panama', 
                                'Uruguay', 'Equatorial Guinea']
    paises_francofonos = ['Francia', 'Bélgica', 'Canadá', 'Suiza', 'Luxemburgo', 'Mónaco', 'Andorra',
                          'France', 'Belgium', 'Canada', 'Switzerland', 'Luxembourg', 'Monaco', 'Andorra']
    paises_anglofonos = ['Estados Unidos', 'Reino Unido', 
                            'Canadá', 'Australia', 
                            'Nueva Zelanda', 'Irlanda', 
                            'Sudáfrica', 'Singapur',
                            'United States', 'United Kingdom', 'Canada', 
                            'Australia', 'New Zealand', 'Ireland', 'South Africa', 
                            'Singapore']
    
    if pais in paises_hispanohablantes:
        return 'es'
    elif pais in paises_francofonos:
        return 'fr'
    else:
        return 'en'

def convertir_a_excel(
        contactos:list[Lead], 
        sector_busqueda:str, 
        pagina_busqueda:str,
        excel_folder:Path,
        resume_flag:bool=False) -> Path:
    """Dada una lista de Lead, cre un excel con los datos y devuelve su ruta

    Parameters
    ----------
    contactos : list[Lead]
        _description_
    sector_busqueda : str
        _description_
    """

    # Aplanamos los datos
    contactos_data = [
    {'email': " ".join(lead.email) if lead.email else "", 
    'pais': lead.pais,
    'sector': lead.sector_busqueda,
    'empresa': lead.nombre,
    'web': lead.web,
    'receptor': "",
    }
    for lead in contactos
    ]
    df = pd.DataFrame(contactos_data)
    # Creamos la columna idioma en función del pais
    df['idioma'] = df['pais'].apply(asignar_idioma)

    # Si se reanuda hay que buscar el excel en el path y cargarlo
    if resume_flag:
        for archivo in excel_folder.iterdir():
            if sector_busqueda in archivo.name:
                ruta_archivo = excel_folder / archivo.name
                df_existente = pd.read_excel(ruta_archivo)
                df = pd.concat((df_existente, df))
                break        
    # Quitamos duplicados
    df.drop_duplicates(inplace=True)
    ruta = excel_folder / f"Lista contactos - {extraer_dominio(pagina_busqueda)}-{sector_busqueda}.xlsx"
    df.to_excel(ruta, index=False)

    return ruta