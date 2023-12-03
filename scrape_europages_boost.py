from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from aux_func import (
    extraer_correos, 
    convertir_a_excel, 
    handle_insert_db, 
    handle_log_print,
    quitar_tildes
)
from models import Lead
from db import SQLContext

from pathlib import Path
from icecream import ic
from colorama import Style
import time

KWARGS_ALLOWED = ['log_func', 'text_class', 'color', 'color_text', 'page']
NOMBRE_TABLA = 'busquedas'

class WrongKWArgForLogging(Exception):
    pass

def hacer_control_clic(
        driver:webdriver.Chrome|webdriver.Firefox, 
        elemento:WebElement, 
        segundos_espera:int
        ) -> None:
    ActionChains(driver) \
    .key_down(Keys.CONTROL) \
    .click(elemento) \
    .key_up(Keys.CONTROL) \
    .perform()         
    # Cambiamos el DOM a la ultima ventana
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(segundos_espera)
    return

def esperar_cookies(
        driver:webdriver.Firefox|webdriver.Chrome,
        sector_busqueda:str,
        **kwargs
        ) -> None:
    try:
        msg = f"[{sector_busqueda}] || Esperando a las cookies"
        handle_log_print(msg, color="magenta", **kwargs)
        boton_aceptar_cookies = WebDriverWait(driver, 25).until(
        EC.element_to_be_clickable((By.ID, "cookiescript_accept"))
        )
        #boton_aceptar_cookies = driver.find_element(By.ID, "cookiescript_accept")
        if boton_aceptar_cookies:
            msg = f"[{sector_busqueda}] || Se ha encontrado el boton de las cookies"
            handle_log_print(msg, color="magenta", **kwargs)
            boton_aceptar_cookies.click()
    except NoSuchElementException:
        msg = f"[{sector_busqueda}] || No han salido las cookies, seguimos con el código"
        handle_log_print(msg, color="verde", **kwargs)
    except TimeoutException:
        msg = f"[{sector_busqueda}] || No han salido las cookies, seguimos con el código"
        handle_log_print(msg, color="verde", **kwargs)

def retornar_busqueda_lenguaje(idioma_pag:str) -> str:
    """Retorna un string de búsqueda para screapear el idioma en la página

    Parameters
    ----------
    idioma_pag : str
        _description_

    Returns
    -------
    str
        _description_
    """
    if idioma_pag is not None:
        if idioma_pag.strip() == 'English':
            return 'Main site'
        elif idioma_pag.strip() == 'Español':
            return 'principal'
        else:
            return 'principal'
    else:
        return 'principal'
    
def paginar(
        driver:webdriver.Firefox|webdriver.Chrome,
        sector_busqueda:str,
        num_pagina:int,
        segundos_espera:int=7,
        ) -> webdriver.Firefox|webdriver.Chrome:
    """Va hasta el boton siguiente y lo pulsa

    Parameters
    ----------
    driver : webdriver.Firefox
        _description_
    pagina : int
        _description_    """
                  
    # Buscamos los elementos de paginación
    """ pagination_elements:list[WebElement] = driver.find_elements(By.XPATH, "//ul[@class='ep-server-side-pagination__list text-center pl-0 pt-5']/li")
    ic(pagination_elements) #! DEBUG
    if pagination_elements:
        # El último elemento es el siguiente
        elemento_siguiente = pagination_elements[-1]
        # Vamos hasta este elemento
        driver.execute_script("arguments[0].scrollIntoView(true);", elemento_siguiente)
        # Hacemos clic
        elemento_siguiente.click()
        # Esperamos a que cargue
        time.sleep(segundos_espera)
    else:
        print(Fore.LIGHTRED_EX +f"[{sector_busqueda}] || No se han encontrado los elementos de PAGINACiÖN. SALIENDO....")
        print(Fore.LIGHTMAGENTA_EX + f"[{sector_busqueda}] || Contactos recopilados: {len(contactos)}")
        driver.quit() """
    
    # Probamos otra cosa:
    # Cerramos el driver:
    try: # por si el driver no está ni abierto
        driver.quit()
    except:
        pass
    # Lo abrimos usando url
    driver = webdriver.Firefox()
    driver.get(f"https://www.europages.es/empresas/pg-{num_pagina}/{sector_busqueda}.html")
    # Manejar las cookies
    esperar_cookies(driver, sector_busqueda)
    time.sleep(segundos_espera)
    # Devolvemos el driver nuevo creado
    return driver

def scrape_europages_boost(
        sector_busqueda:str,
        segundos_espera:int=10,
        max_extracciones:int|None=None,
        excel_folder:Path=Path.home() / Path('data'),
        kwargs={},
) -> None:
    # Validamos aqui los kwargs antes de lanzar los bucles    
    for key in kwargs.keys():
            if key not in KWARGS_ALLOWED:
                raise WrongKWArgForLogging(f"{key} no es un 'keyword argument' válido")    
    sector_busqueda = quitar_tildes(sector_busqueda.strip().lower()) # pasamos a minusculas y quitamos espacios en blanco y quitamos tildes
    contactos = []
    search_page = 'https://www.europages.es/'
    # Instanciamos el hanlder de db
    db_busquedas:SQLContext = SQLContext(nombre_tabla=NOMBRE_TABLA)
    resume = False # Flag para saber si hemos continuado con la búsqueda

    # Verificamos con DB si existe ya esa búsqueda y restauramos el punto en el que nos encontramos:
    if (campos:=db_busquedas.find_one(campo_buscado='sector', valor_buscado=sector_busqueda)):
        resume = True
        _, sector, pag_resume, lista_resume, elemento_resume, *resto = campos
        pag_totales, listas_totales, elementos_totales, _ = resto
        if sector != sector_busqueda:
            msg = f"[{sector_busqueda}] || Los nombres de los sectores no coinciden"
            handle_log_print(msg, color='rojo_fuerte', **kwargs)

        # Verificamos si ya hemos alcanzado el final de búsqueda
        if (pag_resume == pag_totales) and (lista_resume == listas_totales) and (elemento_resume == elementos_totales):
            # Se han realizado todas las búsquedas
            msg = f"[{sector_busqueda}] || Se han realizado todas las búsquedas. Elimina los checkpoints para comenzar de nuevo las búsquedas para este sector."
            handle_log_print(msg, color='magenta', **kwargs)
            print(Style.RESET_ALL)
            return

        msg = f"[{sector_busqueda}] || Reanudando la búsqueda a partir de página {pag_resume}, lista {lista_resume}, elemento {elemento_resume}"
        handle_log_print(msg, color='amarillo', **kwargs)
    
    else:
        msg = f"[{sector_busqueda}] || Nueva búsqueda."
        handle_log_print(msg, color='amarillo', **kwargs)
        pag_resume, lista_resume, elemento_resume = 1, 1, 1
    
    # Instanciamos el driver
    driver = webdriver.Firefox()    
    # Tiempo de espera para las búsquedas de elementos
    driver.implicitly_wait(10)
    # Cargamos la página principal
    driver.get(search_page)
    time.sleep(segundos_espera)
    # Esperamos a las cookies
    esperar_cookies(driver, sector_busqueda, **kwargs)   
    
    # Buscamos el input text
    try:
        input_text_busqueda = driver.find_element(By.TAG_NAME, 'input') 
    except Exception as e:
        msg = f"[{sector_busqueda}] || No se ha encontrado el input, saliendo. Error: {e}"
        handle_log_print(msg, color='rojo_fuerte', **kwargs)
        driver.quit()

    # Limpiamos el input y realizamos la búsqueda
    input_text_busqueda.clear()
    input_text_busqueda.send_keys(sector_busqueda)
    input_text_busqueda.send_keys(Keys.RETURN)
    time.sleep(segundos_espera)
    # Saca el número de empresas resultado de la búsqueda
    try:
        num_empresas = driver.find_element(By.XPATH, "//span[@class='ep-big-tab-button__count']")
        msg = f"[{sector_busqueda}] || Número de empresas encontradas: {num_empresas.text}"
        handle_log_print(msg, color='amarillo', **kwargs)
    except Exception as e:
        msg = f"[{sector_busqueda}] || Ha fallado la búsqueda del número de empresas: {e}"
        handle_log_print(msg, color='rojo_fuerte', **kwargs)
        driver.quit()
        print(Style.RESET_ALL)
        return
    
    # Buscamos el número de páginas de resultados
    pagination_elements:list[WebElement] = driver.find_elements(By.XPATH, "//ul[@class='ep-server-side-pagination__list text-center pl-0 pt-5']/li")
    if pagination_elements:
        numero_paginas = int(pagination_elements[-2].text) # El último es el botón de página siguiente
    else:
        numero_paginas = 1

    msg = f"[{sector_busqueda}] || Número total de páginas: {numero_paginas}"
    handle_log_print(msg, color='amarillo', **kwargs)
    
    # Loopeamos cada página
    for pag in range(pag_resume, numero_paginas + 1):
        if pag > pag_resume:
            # Comprobamos si se ha superado el número max de resultados
            if (max_extracciones is not None) and (len(contactos) >= max_extracciones):
                break
            # Pasamos a la página siguiente:
            try:
                driver = paginar(
                    driver=driver,
                    sector_busqueda=sector_busqueda,
                    num_pagina=pag
                    )
                msg = f"[{sector_busqueda}] || Acceso a página {pag}"
                handle_log_print(msg, color='magenta', **kwargs)
            except Exception as e:
                msg = f"[{sector_busqueda}] || No se ha podido pasar a la siguiente página. Saliendo..."
                handle_log_print(msg, color="rojo_fuerte", **kwargs)
                msg = f"[{sector_busqueda}] || Error: {e}"
                handle_log_print(msg, color="rojo_fuerte", **kwargs)
                msg = f"[{sector_busqueda}] || Contactos recopilados: {len(contactos)}"
                handle_log_print(msg, color="magenta", **kwargs)
                driver.quit()
                break
                
        try:
            # Encuentra todos los elementos 'li' en la página. Válido para Europages.es de momento
            contacts_found:list[WebElement] = driver.find_elements(By.XPATH, "//ol[@class='ep-page-serp-companies__epages-list ps-0']/li/a[@class='ep-ecard-serp__epage-link']")
            # Buscar la cantidad de ol y cuantos li tiene cada ol.
            elements_ol:list[WebElement] = driver.find_elements(By.XPATH, "//ol[@class='ep-page-serp-companies__epages-list ps-0']")
            # Calculamos cuantos li tiene cada ol
        except Exception as e:
            msg = f"[{sector_busqueda}] || Ha habido un error buscando las listas de resultados. Cerrando..."
            handle_log_print(msg, color="rojo_fuerte", **kwargs)
            msg = f"[{sector_busqueda}] || Error: {e}"
            handle_log_print(msg, color="rojo_fuerte", **kwargs)
            msg = f"[{sector_busqueda}] || Contactos recopilados: {len(contactos)}"
            handle_log_print(msg, color="magenta", **kwargs)
            driver.quit()
            break
        
        ols = []
        for num in range(1, len(elements_ol) + 1):
                ols.append(len(driver.find_elements(By.XPATH, f'//ol[{num}]/li')))
        # Esto se tiene que cumplir siempre
        if not sum(ols) == len(contacts_found):
            msg= f"[{sector_busqueda}] || No coinciden {ols=} y {contacts_found=}. Ha habido un problema..."
            handle_log_print(msg, color='rojo_fuerte', **kwargs)
            driver.quit()
            print(Style.RESET_ALL)
            return
        
        if not contacts_found:
            # Si no se han encontrado resultados salimos
            msg = f"[{sector_busqueda}] || No se ha encontrado ningún resultado para la búsqueda: {sector_busqueda}"
            handle_log_print(msg, color='rojo_fuerte', **kwargs )
            driver.quit()            
            handle_log_print(msg, color='magenta', **kwargs )
            print(Style.RESET_ALL)
            return   

        listas_totales_fly =  len(ols)        
        # Comprobaciones si reanuda
        if resume and (listas_totales != listas_totales_fly):
            msg = f"[{sector_busqueda}] || Atención: las listas totales guardadas no coinciden con las listas totales calculadas"
            handle_log_print(msg, color="rojo", **kwargs)
        # Loopeamos sobre las LISTAS
        for i in range(lista_resume, listas_totales_fly + 1):
            # Comprobamos si se ha alcanzado límite máximo
            if (max_extracciones is not None) and (len(contactos) >= max_extracciones):
                break
            elementos_totales_fly = ols[i-1]
            # Loopeamos sobre los ELEMENTOS
            for li in range(elemento_resume, elementos_totales_fly + 1):
                msg = f"\n\n[{sector_busqueda}] || Página [{pag}/{numero_paginas}], Lista [{i}/{len(ols)}], Elemento [{li}/{ols[i - 1]}]"
                handle_log_print(msg, color='cian', **kwargs )
                try:
                    # Sacamos el elemento siguiente               
                    elemento = driver.find_element(By.XPATH, f'//div[@class="ep-serp-wrapper__content pt-1"]/div[1]/ol[{i}]/li[{li}]/a')
                    # Lo metemos en viewport
                    driver.execute_script("arguments[0].scrollIntoView(true);", elemento)
                except NoSuchElementException as exc:
                    msg = f'[{sector_busqueda}] || No se ha encontrado el enlace para pinchar: {exc}'
                    handle_log_print(msg, color='rojo_fuerte', **kwargs)
                    print(Style.RESET_ALL)
                    break
                
                try:
                    # En lugar de hacer clic, buscamos hacer control + clic para que se abra en otra pestaña
                    hacer_control_clic(driver, elemento, segundos_espera)

                except Exception as exc:
                    msg = f"[{sector_busqueda}] || No se ha podido hacer clic: {exc}"
                    handle_log_print(msg, color='rojo_fuerte', **kwargs)
                    print(Style.RESET_ALL)
                    break
                
                # Averigüamos en qué idioma está la página
                try:
                    idioma_pagina = driver.find_element(By.XPATH, '//div[@class="ep-navigation-languages"]/button/span/small').text
                    msg = f"[{sector_busqueda}] || Idioma de la página de búsqueda: {idioma_pagina}."
                    handle_log_print(msg, color='verde', **kwargs)
                except:
                    idioma_pagina = None
                    msg = f"[{sector_busqueda}] || No se ha encontrado el idioma."
                    handle_log_print(msg, color='rojo_fuerte', **kwargs)
                # Buscamos el header con el nombre de la empresa
                try:
                    elemento_empresa = driver.find_element(By.TAG_NAME, 'h1')
                    nombre_empresa = elemento_empresa.text
                except NoSuchElementException as exc:
                    msg = f"[{sector_busqueda}] || No se ha encontrado el nombre de la empresa: {exc}"
                    handle_log_print(msg, color='rojo_fuerte', **kwargs)
                    nombre_empresa = ""
                # Buscamos el pais
                try:
                    elemento_pais = driver.find_element(By.CLASS_NAME, 'ep-country-flag-wrapper__flag-name')
                    pais = elemento_pais.text
                except NoSuchElementException as exc:
                    msg = f"[{sector_busqueda}] || No se ha encontrado el pais de la empresa: {exc}"
                    handle_log_print(msg, color='rojo_fuerte', **kwargs)
                    pais = ""

                # Buscamos el enlace a la web de la empresa
                first_search = retornar_busqueda_lenguaje(idioma_pagina)
                try:
                    enlace_pagina_principal = driver.find_element(By.PARTIAL_LINK_TEXT, first_search)                
                    enlace_pagina_principal.click()
                    msg = f"[{sector_busqueda}] || Haciendo click en la web de la empresa."
                    handle_log_print(msg, color='verde', **kwargs)
                except:
                    try:
                        msg = f"[{sector_busqueda}] || No se ha podido hacer click en la empresa, buscando otro enlace..."
                        handle_log_print(msg, color='rojo', **kwargs)
                        enlace_pagina_web = driver.find_element(By.XPATH, '//div/div[2]/section[2]/div[2]/a[1]')
                        enlace_pagina_web.click()
                        msg = f"[{sector_busqueda}] || Se ha conseguido hacer click en la web de la empresa."
                        handle_log_print(msg, color='verde', **kwargs)
                    except Exception as exc:
                        msg = f"[{sector_busqueda}] || No se ha encontrado el enlace correcto de la empresa: {exc}"
                        handle_log_print(msg, color='rojo', **kwargs)
                        # Instanciamos el lead en el caso de que no haya enlace a la web
                        lead = Lead(
                            sector_busqueda=sector_busqueda,
                            nombre=nombre_empresa,
                            pais=pais
                            )                    
                        contactos.append(lead)
                        msg = f"[{sector_busqueda}] || Lead({lead}) agregado || {len(contactos)} contactos hasta ahora."
                        handle_log_print(msg, color='verde', **kwargs )
                        # Tenemos que volver a la principal
                        # En lugar de cerrar el driver, cerramos 1 pestaña
                        driver.close()
                        driver.switch_to.window(driver.window_handles[-1])
                        time.sleep(5)
                        # Continuamos el bucle
                        continue            

                try:
                    # Se abre otra ventana, hay que cambiar el driver de ventana
                    driver.switch_to.window(driver.window_handles[-1]) # Le pasamos la última ventana, que es la que se acaba de abrir
                    time.sleep(segundos_espera+5)
                    # Sacamos la información
                    web = driver.current_url
                    email:set = extraer_correos(driver.page_source)
                    # Si no tiene ningún mail extraido buscar una sección Contacto
                    if not email:
                        # Buscamos el elemento Contacto
                        try:
                            msg = f"[{sector_busqueda}] || No se ha encontrado ningún email, Buscando el apartado 'Contacto'..."
                            handle_log_print(msg, color='rojo', **kwargs)                            
                            elemento_contacto = driver.find_element(By.PARTIAL_LINK_TEXT, 'Contact')
                            elemento_contacto.click()
                            time.sleep(segundos_espera)
                            # Si nos lleva a una pagina donde sale el email intentamos capturarlo
                            # TODO que pasa si nos abre nueva página.. hay que gestionar este caso
                            email:set = extraer_correos(driver.page_source)
                        except NoSuchElementException as exc:
                            msg = f"[{sector_busqueda}] || No se ha encontrado un elemento de Contacto: {str(exc)[:100]}"
                            handle_log_print(msg, color='rojo', **kwargs)                            
                    
                    # Instanciamos el lead
                    lead = Lead(
                            email=email,
                            sector_busqueda=sector_busqueda,
                            nombre=nombre_empresa,
                            web=web,
                            pais=pais
                        )
                    contactos.append(lead)
                    msg = f"[{sector_busqueda}] || Lead({lead}) agregado || {len(contactos)} contactos hasta ahora."
                    handle_log_print(msg, color='verde', **kwargs )
                    # En lugar de cerrar el driver, cerramos las pestañas
                    # A veces se abre en la misma ventana, hay que calcular el número de pestañas abiertas
                    pest_abiertas = driver.window_handles
                    for _ in range(len(pest_abiertas) - 1): 
                        driver.close()
                        driver.switch_to.window(driver.window_handles[-1])

                    time.sleep(4)
                    # Aqui deberiamos estar de vuelta en la página con todos los resultados


                except Exception as exc:
                    msg = f"[{sector_busqueda}] || Ha habido algun error sacando la información: {exc}"
                    handle_log_print(msg, color='rojo_fuerte', **kwargs )
                    #En lugar de cerrar el driver, cerramos las pestañas
                    pest_abiertas = driver.window_handles
                    for _ in range(len(pest_abiertas) - 1): 
                        driver.close()
                        driver.switch_to.window(driver.window_handles[-1])
                    continue
                
                finally:
                    #Comprobamos si se ha alcanzado el número máximo de contactos
                    finish_pag, finish_lista, finish_elemento = pag, i, li
                    if (max_extracciones is not None) and (len(contactos) >= max_extracciones):
                        msg = f"[{sector_busqueda}] || Se ha alcanzado el límite máximo de resultados de: {max_extracciones}. Finalizando..."
                        handle_log_print(msg, color='verde', **kwargs)                        
                        break
            
            elemento_resume = 1
            # Si hay más contactos que el máximo pasado salimos del bucle
            if (max_extracciones is not None) and (len(contactos) > max_extracciones):
                break
        # Volvemos a poner en 1 para la siguiente iteración.
        lista_resume = 1
        complete_or_not = 'incompleta' if (i < listas_totales_fly) and (li < elementos_totales_fly) else ""
        msg = f"[{sector_busqueda}] || Fin página {pag} {complete_or_not}"
        handle_log_print(msg, color='magenta', **kwargs)
        
    # Fuera de todo bucle
    # Si se ha reanudado actualizamos en DB si es nueva búsqueda insertamos en db
    try:
        handle_insert_db(
            db_busquedas,
            resume,
            sector_busqueda,
            finish_pag=finish_pag,
            finish_lista=finish_lista,
            finish_elemento=finish_elemento,
            paginas_totales=numero_paginas,
            listas_totales=listas_totales_fly,
            elementos_totales=elementos_totales_fly,
        )
        msg = f"[{sector_busqueda}] || Se ha guardado correctamente en base de datos el checkpoint."
        handle_log_print(msg, color='verde_fuerte', **kwargs)
    except Exception as e:
        msg = f"[{sector_busqueda}] || No se ha podido insertar en base de datos.: {e}"
        handle_log_print(msg, color='rojo_fuerte', **kwargs)

    try:
        archivo_excel = convertir_a_excel(
            contactos,
            sector_busqueda,
            search_page,
            excel_folder,
            resume_flag=resume
        )
        estado_excel = 'ACTUALIZADO' if resume else 'REALIZADO'
        msg = f"[{sector_busqueda}] || Excel {estado_excel} con éxito: {archivo_excel}"
        handle_log_print(msg, color='verde_fuerte', **kwargs)
    except Exception as e:
        msg = f"[{sector_busqueda}] || No se ha podido realizar el excel: {e}"
        handle_log_print(msg, color='rojo_fuerte', **kwargs)

    try:
        # Por si sigue abierto el driver
        driver.quit()
    except:
        pass
        
    print(Style.RESET_ALL)

    return None

if __name__ == '__main__':
    pass
