import flet as ft
from typing import Callable
from icecream import ic
import math

PALETA = {
    'Azul Principal': '#1e3799', # El color dominante del logo, que puede ser utilizado para la barra de título y botones principales
    'Verde Secundario': '#149937', # Un acento del logo, ideal para resaltar elementos interactivos o importantes
    'Azul Claro': '#87cefa', # Para fondos de campos de texto y otras áreas de entrada de datos.
    'Gris Oscuro': '#4d4d4d', # Para textos y elementos de la consola para asegurar una buena legibilidad sobre fondos claros y oscuros.
    'Blanco': '#ffffff', # Para textos sobre fondos oscuros o colores intensos, asegurando una alta legibilidad
    'Gris Claro': '#c8c8c8', # Para fondos de listas y paneles donde no se requiere tanto énfasis
    'Azul Oscuro Logo': '#000922', # Degradado mas oscuro
    'Azul menos oscuro Logo': '#003857', # Degradado mas claro
}

PALETA_TALSA = {
    'AZUL TALSA': "#005092",
    'ROJO TALSA': "#c54933",
    'LIGHT PRIMARY COLOR': '#FFCDD2',
    'TEXT ICONS': '#FFFFFF',
    'ACCENT COLOR': '#536DFE',
    'PRIMARY TEXT': '#212121',
    'SECONDARY TEXT': '#757575',
    'DIVIDER COLOR': '#7F9172'
}

PORCENTAJE_COLOR_MAP = {
    range(0, 71): PALETA['Verde Secundario'],
    range(71, 91): ft.colors.ORANGE_500,
    range(91, 101): ft.colors.RED_500,
}

class PopUpBorrarCheckpoint(ft.UserControl):
    def __init__(self, func_si:Callable, func_no:Callable) -> None:
        self.sector = ""
        self.func_si = func_si
        self.func_no = func_no
        super().__init__()

    def build(self) -> ft.AlertDialog:
        return ft.AlertDialog(
        modal=True,
        title=ft.Text("Borrar Checkpoint"),
        content=ft.Text(f"¿ Estás seguro de querer borrar {self.sector} para siempre ?"),
        actions=[
            ft.TextButton("Sí", on_click=self.func_si),
            ft.TextButton("No", on_click=self.func_no),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        on_dismiss=lambda e: print("Modal dialog dismissed!"),
    )

    
class TextoConsola(ft.UserControl):
    def __init__(self,
                 msg:str,
                 color:ft.colors=ft.colors.WHITE,
                 font_family:str="vt323") -> None:
        super().__init__()
        self.msg = msg
        self.color = color
        self.font_family = font_family

    def build(self) -> ft.Text:
        return ft.Text(
            value=self.msg,
            color=self.color,
            font_family=self.font_family,
            size=18
        )


class LineaBusqueda(ft.UserControl):
    def __init__(self,
                sector:str,
                borrar_busqueda_func:Callable[[None], None]
                ) -> None:
        self.sector = sector
        self.borrar_busqueda = borrar_busqueda_func
        super().__init__()
        
    def build(self) -> ft.Container:
        return ft.Container(
            ft.Row([
                ft.Text(self.sector, color=ft.colors.BLACK87, size=16),
                ft.IconButton(key=self.sector, icon=ft.icons.DELETE, icon_color=ft.colors.RED_400, on_click=self.borrar_busqueda)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            border_radius=8, 
            bgcolor=ft.colors.WHITE,
            border=ft.border.all(1, PALETA_TALSA['PRIMARY TEXT']),
            padding=5,
            alignment=ft.alignment.center
        )


class LineaCheckpoint(ft.UserControl):
    def __init__(self, 
                sector:str, 
                pagina:int, 
                lista:int, 
                elemento:int,
                paginas_totales:int,
                listas_totales:int,
                elementos_totales:int,
                fecha:str,
                num_empresas:int,
                agregar_func:Callable[[None], None],
                borrar_func:Callable[[None], None],
                ) -> None:
        super().__init__()        
        self.sector = sector
        self.fecha = fecha
        self.num_empresas = num_empresas
        self.avance = [(pagina, paginas_totales), (lista, listas_totales), (elemento, elementos_totales)]
        self.agregar_func = agregar_func
        self.borrar_func = borrar_func
        self.icono_rastrear = ft.IconButton(key=self.sector, 
                                            icon=ft.icons.FIND_IN_PAGE,
                                            icon_color=PALETA_TALSA["AZUL TALSA"],
                                            tooltip=f"Rastrea y comprueba si hay actualizaciones para {self.sector}",
                                            on_click=self.agregar_func
                                            )        
        self.icono_agregar = ft.IconButton(key=self.sector, 
                                            icon=ft.icons.ARROW_BACK, 
                                            icon_color=PALETA_TALSA["AZUL TALSA"],
                                            tooltip=f"Reanuda la caza de '{self.sector}'",
                                            on_click=self.agregar_func
                                            )
        self.icono_eliminar = ft.IconButton(key=(self.sector, self.porcentaje_avance), 
                                            icon=ft.icons.DELETE, 
                                            icon_color=PALETA_TALSA['ROJO TALSA'], # 400 originalmente
                                            tooltip="Elimina el checkpoint. La búsqueda se reanudará desde 0.",
                                            on_click=self.borrar_func
                                            )
        self.progress_bar = ft.ProgressBar(height=4,
                                        color=PALETA['Verde Secundario'], # se deja color verde siempre. 
                                        value=self.porcentaje_avance,
                                        bgcolor=ft.colors.BLACK87,
                                        tooltip=f"{round(self.porcentaje_avance * 100, 1)}%"
                                        )

    @property
    def fila_iconos(self) -> None:
        if int(self.porcentaje_avance) == 1:
            return ft.Container(ft.Row([
                self.icono_rastrear,
                self.icono_eliminar,
            ],
            alignment=ft.MainAxisAlignment.END),
            width=120
            )
        else:
            return ft.Container(ft.Row([
                self.icono_agregar,
                self.icono_eliminar
            ],
            alignment=ft.MainAxisAlignment.END),
            width=120
            )

    def build(self) -> ft.Container:
        return ft.Container(
            ft.Column([
                self.progress_bar,
                ft.Row([
                    #ft.Container(ft.Text(f"{self.porcentaje_avance:.1%}", color=PALETA['Blanco']), width=60 , bgcolor=self.color_porcentaje, border_radius=5, padding=5), #Porcentaje
                    ft.Container(width=3),
                    ft.Container(
                        ft.Row([
                            ft.Text(self.num_empresas, color=PALETA_TALSA['AZUL TALSA'], size=9),
                            ft.Text(f"{self.sector}", color=ft.colors.BLACK87, size=18),                            
                        ],
                        alignment=ft.MainAxisAlignment.NONE),
                    width=200,
                    padding=2),
                    ft.Container(ft.Text(self.fecha, color=PALETA_TALSA['DIVIDER COLOR'], size=11), width=110),             
                    ft.Container(self.fila_iconos)                    
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            ],
            alignment=ft.MainAxisAlignment.START
            ),
            height=60,
            border_radius=8, 
            bgcolor=ft.colors.WHITE,
            padding=0,
            border=ft.border.all(1, PALETA_TALSA['PRIMARY TEXT']),
            alignment=ft.alignment.center,
        )
    
    @property
    def porcentaje_avance(self) -> float:
        # Desempaquetamos los valores de la lista
        (pagina_actual, paginas_totales), (lista_actual, listas_totales), (elemento_actual, elementos_totales) = self.avance

        # Calculamos el total de elementos
        total_elementos = paginas_totales * listas_totales * elementos_totales

        # Calculamos los elementos procesados hasta el momento
        elementos_procesados = ((pagina_actual - 1) * listas_totales * elementos_totales) + \
                            ((lista_actual - 1) * elementos_totales) + \
                            elemento_actual
        # Calculamos el porcentaje
        porcentaje = elementos_procesados / total_elementos
        return porcentaje
    
    @property # Esta función ya no se usa
    def color_porcentaje(self) -> str:
        porcentaje = math.ceil(self.porcentaje_avance * 100)
        for rango in PORCENTAJE_COLOR_MAP:
            if porcentaje in rango:
                return PORCENTAJE_COLOR_MAP[rango] 
