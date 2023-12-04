import flet as ft

from scrape_europages_boost import scrape_europages_boost, NOMBRE_TABLA
from aux_func import (fecha_string, 
                    formato_dia, 
                    formato_dia_hora,
                    )
from db import SQLContext
from flet_models import (
    LineaCheckpoint, 
    LineaBusqueda, 
    TextoConsola, 
    PALETA,
    PALETA_TALSA
    )
from rutas import (
    FILE_TO_DOWNLOAD,
    URL_GECKO_WIN64_ZIP,
    RUTA_RAIZ,
    RUTA_GECKODRIVER,
    RUTA_DB,
    CONFIG_FILE,
    save_path_file_db,
    NOMBRE_DB_SQLITE)

import os
import winreg as reg
import requests
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

# Constantes #
opciones_busqueda = ['Europages']
WIN_HEIGHT:int = 880
WIN_WIDTH:int = 970
TITLE_APP = 'Profile Hunter 1.0'

color_border_contenedor = PALETA_TALSA["ROJO TALSA"]
grosor_borde_contenedor = 2
radio_bordes = 8
TEXTS_SIZE = 16
TITLE_STYLE = ft.TextThemeStyle.HEADLINE_MEDIUM
DICT_BORDES = {
    "color": color_border_contenedor,
    "width": grosor_borde_contenedor,
}
PARAMETROS_INPUTS = {
    'color': PALETA['Azul menos oscuro Logo'],
    'height': 45,
    'border_radius':radio_bordes,
    'width':200,
    'bgcolor': PALETA_TALSA['DIVIDER COLOR'],
    'text_size': TEXTS_SIZE,
    'content_padding': 5,    
}
db_busquedas:SQLContext = SQLContext(nombre_tabla=NOMBRE_TABLA)

# Función principal #
def main(page:ft.Page):

    page.fonts = {
        "Kanit": "https://raw.githubusercontent.com/google/fonts/master/ofl/kanit/Kanit-Bold.ttf",
        "vt323": "fonts/vt323-latin-400-normal.ttf",
        "RobotoSlab": "https://github.com/google/fonts/raw/main/apache/robotoslab/RobotoSlab%5Bwght%5D.ttf",
    }
    page.title = TITLE_APP
    page.theme = ft.Theme(font_family="Arial") # Consolas
    page.bgcolor = PALETA_TALSA['TEXT ICONS']
    page.window_width = WIN_WIDTH
    page.window_height = WIN_HEIGHT
    page.window_resizable = False
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.START

    # Funciones #
    def firefox_instalado_windows() -> bool:
        """Devuelve True si Firefox está instalado en registro False en caso contrario

        Returns
        -------
        bool
            _description_
        """
        try:
            clave = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe")
            ruta, _ = reg.QueryValueEx(clave, None)
            reg.CloseKey(clave)
            return os.path.exists(ruta)
        except FileNotFoundError:
            return False

    def descargar_geckodriver(e:ft.ControlEvent) -> None:
        """Descarga el geckodriver

        Parameters
        ----------
        e : ft.ControlEvent
            _description_

        Returns
        -------
        str
            _description_
        """
        if not RUTA_GECKODRIVER.exists():
            RUTA_GECKODRIVER.mkdir(parents=True)
        try:
            respuesta = requests.get(URL_GECKO_WIN64_ZIP)
            if respuesta.status_code == 200:
                with open(RUTA_GECKODRIVER / FILE_TO_DOWNLOAD, "wb") as f:
                    f.write(respuesta.content)
                pintar_en_consola(f"Se ha descargado geckodriver win64 en\n{RUTA_GECKODRIVER} correctamente.", color="#00ff00")
                pintar_en_consola(f"Descomprime el archivo en esa misma ruta", color="#00ff00")
                # TODO Agregar a PATH esta ruta ?
            else:
                pintar_en_consola(f"Se ha producido un error al descargar geckodriver. Código: {respuesta.status_code}")
        except Exception as e:
            pintar_en_consola(e, color="#ff0000")
        page.update()

    def descargar_log(e:ft.ControlEvent) -> None:
        # Verificamos que exista valor en path
        if (path:=path_input_text.value):
            true_path = RUTA_RAIZ / Path(path)
            if not true_path.exists():
                try:
                    true_path.mkdir()
                    pintar_en_consola(f"Se ha creado la ruta {true_path}", "#00ff00")
                except Exception as e:
                    pintar_en_consola(f"Error al crear la ruta raíz {true_path}: {e}", "#ff0000")
            file_path = true_path / f"LOG [{fecha_string(formato_dia)}].txt"
            with open(file_path, "a", encoding="utf-8") as f:
                data = "\n".join([ line.msg for line in listview_consola.controls])
                f.write(data)
        else:
            pintar_en_consola("El 'directorio excels' no puede estar vacío", color="#ff0000")

    def guardar_excels_path(e: ft.ControlEvent) -> None:
        if (new_path:=path_input_text.value):
            path_input_text.error_text = ""
            ruta_completa = RUTA_RAIZ / new_path
            with open(save_path_file_db, 'w') as f:
                f.write(new_path)
            pintar_en_consola(f"Se ha guardado correctamente el directorio '{ruta_completa}'", color="#00ff00")
        else:
            path_input_text.error_text = "No puede estar vacío"
        page.update()

    def cargar_excels_path() -> str:
        """Lee el archivo txt donde se guarda el path de los excels
        y lo devuelve para visualizar en el input tex

        Returns
        -------
        str
            _description_
        """
        try:
            with open(save_path_file_db, 'r') as f:
                data = f.read()        
            return data
        except FileNotFoundError:
            return "data"

    def ruta_en_PATH(ruta:str|Path) -> bool:
        """Comprueba si una determinada ruta está en el PATH de Windows

        Parameters
        ----------
        ruta : str | Path
            _description_

        Returns
        -------
        bool
            _description_
        """
        if isinstance(ruta, Path):
            ruta = ruta.as_posix()
        if not isinstance(ruta, str):
            raise TypeError(f"Se ha producir un error con la ruta {ruta}. Debe ser de tipo str")
        
        # Normalizamos la ruta para evitar problemas con los slashes
        ruta = os.path.normpath(ruta)
        # Ubicación de la clave del PATH en las variables de entorno del usuario
        path_actual = os.environ['PATH']
        # Normalizamos las rutas del path también
        rutas_en_path = [os.path.normpath(p) for p in path_actual.split(os.pathsep)]
        return ruta in rutas_en_path            

    def hunt(e: ft.ControlEvent) -> None:
        # Hay que comprobar que Mozilla Firefox esté instalado
        if not firefox_instalado_windows():
            pintar_en_consola("No tienes instalado Mozilla Firefox. Ve al menú de arriba a la derecha, descárgalo e instalalo.", color="#ff0000")
            return        
        # Comprobamos que geckodriver esté en la ruta establecida
        if Path(RUTA_GECKODRIVER / 'geckodriver.exe') not in RUTA_GECKODRIVER.iterdir():
            pintar_en_consola(f"No se ha encontrado el archivo 'geckodriver.exe' en la ruta\n {RUTA_GECKODRIVER}. Descárgalo desde el menú superior derecho", color="#ff0000")
            return
        # Comprobar que la ruta de geckodriver esté en el PATH de windows
        if not ruta_en_PATH(RUTA_GECKODRIVER):
            pintar_en_consola(f"La ruta {RUTA_GECKODRIVER} no se encuentra en el PATH. Agrégala manualmente", color="#ff0000")
        
        if (num_cazas:=maximas_cazas.value):
            if listview_busquedas.controls:
                # Validamos que el path exista, si no lo creamos?
                if (excels_path_str:=path_input_text.value):
                    # Usamos el directorio de usuario
                    excels_path = RUTA_RAIZ / Path(excels_path_str)
                    if not excels_path.exists():
                        excels_path.mkdir(parents=True)
                        pintar_en_consola(f"Directorio {excels_path} creado", color="#00ff00")
                    try:
                        num_cazas = int(num_cazas)
                        maximas_cazas.error_text = ""
                        busqueda_texto.error_text = ""
                        path_input_text.error_text = ""
                        busquedas = sacar_lista_busquedas()
                        # Empezamos el contador
                        start = time.perf_counter()
                        pintar_en_consola(f"{fecha_string(formato_dia_hora)} *** COMIENZA LA CAZA ***", color="#CF3476")
                        with ThreadPoolExecutor(max_workers=8) as executor:
                            executor.map(
                                scrape_europages_boost, 
                                busquedas, 
                                [10] * len(busquedas), # segundos de espera
                                [num_cazas] * len(busquedas),
                                [excels_path] * len(busquedas),
                                [{"log_func": listview_consola.controls.append,
                                "text_class": TextoConsola,
                                "page": page,
                                }] * len(busquedas),
                                )
                        # Mostramos por consola el tiempo total
                        end = time.perf_counter()
                        diferencia = end - start
                        horas = diferencia // 3600
                        minutos = (diferencia // 60) % 60
                        segundos = diferencia % 60
                        msg = f"""\n{fecha_string(formato_dia_hora)}  *** CAZA TERMINADA ***.\nDuración total: {horas:.0f} h {minutos:.0f} min {segundos:.0f} s\n"""
                        pintar_en_consola(msg, color="#CF3476")
                        # Al terminar hay que actualizar la carga de la base de datos
                        # Limpiamos los datos de la listview
                        listview_checkpoints.controls.clear()
                        # Volvemos a cargar los datos
                        cargar_checkpoints()
                        # Actualizamos la página
                        page.update()
                    except ValueError:
                        maximas_cazas.error_text = "El número debe ser un entero"
                        maximas_cazas.value = ""
                    except Exception as e:
                        listview_consola.controls.append(TextoConsola(msg=e))
                        print(e)
                        page.update()
                else:
                    path_input_text.error_text = "El path no puede estar vacío"
            else:
                busqueda_texto.error_text = "Al menos 1 sector necesario."
                
        else:
            maximas_cazas.error_text = "El número no puede estar vacío"
            maximas_cazas.value = ""                
        page.update()

    def agregar_busqueda(e:ft.ControlEvent) -> None:
        busqueda_texto.error_text = ""
        sector = busqueda_texto.value
        # Comprobamos que no haya ya 5
        if len(listview_busquedas.controls) == 5:
            busqueda_texto.error_text = "Se han alcanzado el máximo de búsquedas simultáneas"
        elif ya_existe_sector_en_lista(sector):
            busqueda_texto.error_text = f"Ya se ha agregado el sector {sector}"
        else:
            if sector:
                listview_busquedas.controls.append(LineaBusqueda(sector, borrar_busqueda))
                busqueda_texto.value = ""
                pintar_en_consola(f"Se ha agregado el sector '{sector}' a la búsqueda", '#00ff00')
        page.update()

    def sacar_indice_elemento(elemento_a_borrar:str) -> int:
        for idx, elemento in enumerate(listview_busquedas.controls):
            if elemento.sector == elemento_a_borrar:
                return idx

    def sacar_lista_busquedas() -> list[str]:
        """Devuelve una lista con los strings de las búsquedas

        Returns
        -------
        list[str]
            _description_
        """
        return [elemento.sector for elemento in listview_busquedas.controls]

    def borrar_busqueda(e:ft.ControlEvent) -> None:
        # Sacamos el elementos a borrar
        sector = e.control.key
        # Hallamos el índice en el que se encuentra en la listview
        indice_borrar = sacar_indice_elemento(sector)
        # Borramos el elemento y actualizamos
        listview_busquedas.controls.pop(indice_borrar)
        pintar_en_consola(f"Se ha quitado el sector '{sector}' de la búsqueda", '#00ff00')
        page.update()

    def agregar_a_busqueda_checkpoint(e: ft.ControlEvent) -> None:
        sector = e.control.key
        busqueda_texto.error_text = ""
        # Comprobamos que no haya ya 5
        if len(listview_busquedas.controls) == 5:
            busqueda_texto.error_text = "Se han alcanzado el máximo de búsquedas simultáneas"
        elif ya_existe_sector_en_lista(sector):
            busqueda_texto.error_text = f"Ya se ha agregado el sector {sector}"
        else:
            listview_busquedas.controls.append(LineaBusqueda(sector, borrar_busqueda))
            quitar_icono_flecha(sector)
            busqueda_texto.value = ""
            pintar_en_consola(f"Se ha agregado el sector '{sector}' a la búsqueda", '#00ff00')
        page.update()

    def ya_existe_sector_en_lista(sector:str) -> bool:
        if sector in sacar_lista_busquedas():
            return True
        else:
            return False

    def cargar_checkpoints() -> None:
        lista_checkpoints = db_busquedas.get_table()
        if lista_checkpoints:
            for check in lista_checkpoints:
                _, sector, pagina, lista, elemento, paginas_totales, listas_totales, elementos_totales, fecha, _ = check
                fila_checkpoint = LineaCheckpoint(
                    sector,
                    pagina,
                    lista,
                    elemento,
                    paginas_totales,
                    listas_totales,
                    elementos_totales,
                    fecha,
                    agregar_a_busqueda_checkpoint,
                    abrir_dialogo_modal,
                )
                # Verificamos si está al 100%
                listview_checkpoints.controls.append(fila_checkpoint)
        # Actualizamos el numero de checkpoints
        actualizar_num_checkpoints()    
        page.update()

    def quitar_icono_flecha(sector:str) -> None: #! A revisar o quitar
        # Iteramos sobre la listview hasta encontrar el elemento
        for elemento in listview_checkpoints.controls:
            if elemento.sector == sector:
                elemento.fila_iconos.content.controls.pop()
                page.update()

    def limpiar_consola(e:ft.ControlEvent) -> None:
        listview_consola.controls.clear()
        #listview_consola.controls.append(TextoConsola(msg="Hola amigos"))
        page.update()

    def abrir_dialogo_modal(e:ft.ControlEvent) -> None:
        sector = e.control.key[0]
        porcentaje_avance = e.control.key[1]
        page.dialog = dlg_modal
        dlg_modal.title.value = f"Borrar Checkpoint '{sector}'"
        dlg_modal.content.value = f"""¿ Estás seguro de querer borrar el sector para siempre ?\nAvance : {porcentaje_avance:.1%}"""
        dlg_modal.actions[0].key = sector
        dlg_modal.open = True
        page.update()

    def cerrar_dialogo_modal(e:ft.ControlEvent) -> None:
        dlg_modal.open = False
        page.update()

    def pintar_en_consola(texto:str, color:str="#ffffff") -> None:
        listview_consola.controls.append(TextoConsola(texto, color))
        page.update()

    def borrar_checkpoint(e:ft.ControlEvent) -> None:
        # Cerramos el dialog box
        dlg_modal.open = False
        # Borramos el registro en base de datos
        sector = e.control.key
        try:
            db_busquedas.delete_one(campo_buscado="sector", valor_buscado=sector)
            pintar_en_consola(f"Se ha borrado definitivamente el checkpoint '{sector}'", '#00ff00')
        except Exception as e:
            pintar_en_consola(f"Se ha producir un error al borrar '{sector}: {e}'", '#ff0000')
        # Limpiamos la listview
        listview_checkpoints.controls.clear()
        # Cargamos de nuevo los checkpoints
        cargar_checkpoints()
        # Actualizamos la página
        page.update()

    def actualizar_num_checkpoints() -> None:
        num = db_busquedas.get_number_of_records()
        texto_numero_de_checkpoints.value = f"({num})"

    def abrir_mensaje_bienvenida_instrucciones() -> None:
        with open("instrucciones.txt", "r", encoding="utf-8") as f:
            instrucciones = f.read()
            pintar_en_consola(instrucciones, '#ffffff')
            # Quitamos el autoscroll de la listview
            listview_consola.auto_scroll = False
        page.update()
        # Volvemos a poner el autoscroll
        listview_consola.auto_scroll = True

    def check_first_run() -> None:
        if not (RUTA_RAIZ / CONFIG_FILE).exists():
            # Mostrar instrucciones aquí
            abrir_mensaje_bienvenida_instrucciones()
            # Crear el archivo de configuración
            with open(RUTA_RAIZ / CONFIG_FILE, 'w') as f:
                f.write('first_run_completed')

    def iniciar_rutas() -> None:
        # Creamos la carpeta si no existe
        if not RUTA_RAIZ.exists():
            try:
                (RUTA_DB).mkdir(parents=True)
                pintar_en_consola(f"Se ha creado la ruta {RUTA_RAIZ}", "#00ff00")
                # Creamos Base de Datos con tabla
                db_busquedas.create_table(
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
                )
                pintar_en_consola(f"Se ha creado la base de datos en\n {RUTA_DB}", "#00ff00")
            except Exception as e:
                pintar_en_consola(f"Error al crear la ruta raíz\n {RUTA_RAIZ}: {e}", "#ff0000")
            # Si no existe la ruta de geckodriver la creamos
            if not RUTA_GECKODRIVER.exists():
                RUTA_GECKODRIVER.mkdir(parents=True)
                pintar_en_consola(f"Se ha creado la ruta\n {RUTA_GECKODRIVER}", "#00ff00")
                #TODO Agregamos la ruta al PATH de windwos

    # Widgets #
    page.appbar = ft.AppBar(
        leading=ft.Container(ft.Image(src="img/logo_Talsa.png", height=120), width=500, alignment=ft.alignment.center_right),
        leading_width=180,
        title=ft.Text(TITLE_APP, style=ft.TextThemeStyle.HEADLINE_LARGE, weight=ft.FontWeight.BOLD, color=PALETA_TALSA["AZUL TALSA"]),
        bgcolor=ft.colors.WHITE,
        toolbar_height=60,
        center_title=True,
        actions=[
            ft.PopupMenuButton(
                items=[
                    ft.PopupMenuItem(text="Descargar Mozilla Firefox", on_click=lambda _:page.launch_url('https://www.mozilla.org/es-ES/firefox/download/thanks/')), # TODO On click
                    ft.PopupMenuItem(text="Descargar Geckodriver para win64", on_click=descargar_geckodriver),
                ]
            )
        ]
    )
    dlg_modal = ft.AlertDialog(
        modal=True,
        title=ft.Text(),
        content=ft.Text(),
        actions=[
            ft.TextButton("Sí", on_click=borrar_checkpoint),
            ft.TextButton("No", on_click=cerrar_dialogo_modal),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=lambda e: print("Modal dialog dismissed!"),
    )
    path_input_text = ft.TextField(
        label="Directorio excels",
        value=cargar_excels_path(),
        label_style=ft.TextStyle(size=16),
        text_align=ft.TextAlign.CENTER,
        tooltip=RUTA_RAIZ,
        **PARAMETROS_INPUTS,
    )
    boton_guardar_path = ft.IconButton(
        icon=ft.icons.SAVE, 
        tooltip="Guarda el Path", 
        bgcolor=PALETA_TALSA['ROJO TALSA'], 
        icon_color=PALETA_TALSA['PRIMARY TEXT'],
        on_click=guardar_excels_path,
        )
    dropdown_pagina_busqueda = ft.Dropdown(
        filled=True,
        alignment=ft.alignment.center,
        value=opciones_busqueda[0],
        options=[ft.dropdown.Option(opt) for opt in opciones_busqueda],
        **PARAMETROS_INPUTS,
    )
    maximas_cazas = ft.TextField(
        label="Máximo de cazas",
        value=10,
        label_style=ft.TextStyle(size=16),
        text_align=ft.TextAlign.CENTER,
        **PARAMETROS_INPUTS,
        tooltip="Número máximo de contactos a extraer en la caza"
        )
    busqueda_texto = ft.TextField(
        label="Nueva búsqueda",
        label_style=ft.TextStyle(size=16),
        text_align= ft.TextAlign.CENTER,
        **PARAMETROS_INPUTS,
    )
    listview_busquedas = ft.ListView(height=260, width=250, spacing=5)
    boton_agregar_busqueda = ft.IconButton(
        icon=ft.icons.ARROW_DOWNWARD, 
        tooltip="Agrega una búsqueda", 
        bgcolor=PALETA_TALSA['ROJO TALSA'], 
        icon_color=PALETA_TALSA['PRIMARY TEXT'],
        on_click=agregar_busqueda,
        )
    
    checkbox_log = ft.Checkbox(
        label="Loguear el progreso",
        value=True,
        fill_color=PALETA_TALSA['ROJO TALSA'],
    )
    
    boton_cazar = ft.ElevatedButton(        
        text="Cazar",
        icon=ft.icons.ARROW_FORWARD_IOS_ROUNDED,
        elevation=5,
        bgcolor=PALETA_TALSA["ROJO TALSA"],
        color=PALETA_TALSA['PRIMARY TEXT'],
        tooltip="Lanzar la caza",
        on_click=hunt,
    )

    listview_checkpoints = ft.ListView(
        height=260, 
        width=500, 
        spacing=5,
        )

    listview_consola = ft.ListView(
        height=listview_checkpoints.height,
        width=listview_checkpoints.width,
        spacing=listview_checkpoints.spacing,
        auto_scroll=True,
    )

    boton_limpiar_consola = ft.ElevatedButton(        
        text="Limpiar",
        icon=ft.icons.CLEAR,
        elevation=5,
        bgcolor=PALETA_TALSA["ROJO TALSA"],
        color=PALETA_TALSA['PRIMARY TEXT'],
        tooltip="Limpiar consola",
        on_click=limpiar_consola,
    )

    boton_descargar_log = ft.ElevatedButton(        
        text="Descargar log",
        icon=ft.icons.DOWNLOAD,
        elevation=5,
        bgcolor=PALETA_TALSA["ROJO TALSA"],
        color=PALETA_TALSA['PRIMARY TEXT'],
        tooltip="Descargar todo el Log en formato txt",
        on_click=descargar_log,
    )

    iniciar_rutas()
    texto_numero_de_checkpoints = ft.Text(color=PALETA['Blanco'], style=ft.TextThemeStyle.LABEL_MEDIUM)
    cargar_checkpoints() # puebla la listview
    
    # Contenedores principales #
    contenedor_arriba = ft.Container(
            ft.Row([
                ft.Container(
                    ft.Column([
                        ft.Text("Definir la caza", color=PALETA_TALSA['TEXT ICONS'], style=TITLE_STYLE),
                        ft.Row([
                            path_input_text,
                            boton_guardar_path,
                            ]),
                        dropdown_pagina_busqueda,
                        maximas_cazas,
                        ft.Row([
                            busqueda_texto,
                            boton_agregar_busqueda,                            
                        ]),
                        ft.Container(
                            listview_busquedas,
                            bgcolor=PALETA_TALSA['DIVIDER COLOR'],
                            padding=8,
                            border_radius=8,
                            border=ft.border.all(1, PALETA_TALSA['PRIMARY TEXT'])
                            ),
                        #ft.Container(
                        #    checkbox_log,
                        #    width=265,
                        #    bgcolor=PALETA_TALSA['DIVIDER COLOR'],
                        #    padding=8,
                        #    border_radius=8,
                        #    ),
                        ft.Row([boton_cazar], alignment=ft.MainAxisAlignment.END),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    bgcolor=PALETA_TALSA['AZUL TALSA'],
                    padding=20,
                    width=350,
                    border=ft.border.all(**DICT_BORDES),
                    border_radius=radio_bordes,
                    ), # Búsquedas
                ft.Container(
                    ft.Column([
                        ft.Row([ft.Text("Checkpoints guardados", color=PALETA['Blanco'], style=TITLE_STYLE), texto_numero_de_checkpoints]),
                        ft.Container(
                            listview_checkpoints,
                            bgcolor=PALETA_TALSA['DIVIDER COLOR'],
                            padding=8,
                            border_radius=8,
                            border=ft.border.all(1, PALETA_TALSA['PRIMARY TEXT']),
                        ),
                        ft.Text("Log", color=PALETA['Blanco'], style=TITLE_STYLE),
                        ft.Container(
                            listview_consola,
                            bgcolor=ft.colors.BLACK87,
                            padding=8,
                            border_radius=8,
                            border=ft.border.all(2, ft.colors.WHITE38)
                        ),
                        ft.Row([boton_descargar_log, boton_limpiar_consola], alignment=ft.MainAxisAlignment.END),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    bgcolor=PALETA_TALSA['AZUL TALSA'],
                    padding=20,
                    width=550,
                    border=ft.border.all(**DICT_BORDES),
                    border_radius=radio_bordes,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_AROUND),
        #border=ft.border.all(**DICT_BORDES),
        #border_radius=radio_bordes,
        height=760,
        padding=5,
    )

    contenedor_principal = ft.Container(
        ft.Column([
            contenedor_arriba,
        ])
    )

    page.add(
        contenedor_principal
    )            
    
    # Mostramos si es primer run para mostrar instrucciones
    check_first_run()

if __name__ == '__main__':
    ft.app(
        target=main,
        assets_dir="assets")