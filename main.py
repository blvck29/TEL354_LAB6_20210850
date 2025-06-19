import requests
import yaml
from prettytable import PrettyTable

# Clases
class Alumno:
    def __init__(self, nombre, codigo, mac):
        self.nombre = nombre
        self.codigo = codigo
        self.mac = mac

class Curso:
    def __init__(self, nombre, estado, codigo):
        self.nombre = nombre
        self.estado = estado
        self.codigo = codigo
        self.alumnos = []
        self.servidores = []

    def add_alumno(self, alumno):
        self.alumnos.append(alumno)

    def del_alumno(self, alumno):
        self.alumnos = [a for a in self.alumnos if a != alumno]

    def add_servidor(self, servidor):
        self.servidores.append(servidor)

class Servicio:
    def __init__(self, nombre, protocolo, puerto):
        self.nombre = nombre
        self.protocolo = protocolo
        self.puerto = puerto

class Servidor:
    def __init__(self, nombre, direccion_ip, servicios=None):
        self.nombre = nombre
        self.direccion_ip = direccion_ip
        self.servicios = servicios if servicios is not None else []

    def add_servicio(self, servicio):
        self.servicios.append(servicio)

    def del_servicio(self, servicio):
        self.servicios = [s for s in self.servicios if s != servicio]

class Conexion:
    def __init__(self, handler, alumno, servidor, servicio):
        self.handler = handler
        self.alumno = alumno
        self.servidor = servidor
        self.servicio = servicio
        self.ruta = None

    def calcular_ruta(self, controller_ip):
        src_dpid, src_port = get_attachment_points(self.alumno.mac, controller_ip)
        dst_dpid, dst_port = get_attachment_points(self.servidor.direccion_ip, controller_ip)

        if not src_dpid or not dst_dpid:
            print("Error: No se encontró la ruta de uno de los puntos de conexión.")
            return None

        # Obtener la ruta entre los switches
        self.ruta = get_route(src_dpid, src_port, dst_dpid, dst_port, controller_ip)
        if not self.ruta:
            print("Error: No se pudo obtener la ruta entre los switches.")
            return None

        return self.ruta

    def crear_flows(self, controller_ip):
        if not self.ruta:
            print("Error: Ruta no calculada.")
            return

        # Crear flows para permitir la conexión entre el alumno y el servidor
        for step in self.ruta:
            crear_flow(self.handler, step, controller_ip)


# Definir las listas globales
alumnos = []
cursos = []
servidores = []
conexiones = []


def get_list_devices(controller_ip):
    target_api = '/wm/device/'
    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
    url = f'http://{controller_ip}:8080{target_api}'
    response = requests.get(url=url, headers=headers)

    if response.status_code == 200:
        print('SUCCESSFUL REQUEST | STATUS: 200')
        data = response.json()
        if not data:
            print("No se encontraron dispositivos.")
            return
        
        table = PrettyTable(["MAC", "IPv4", "Switch DPID", "Puerto"])
        for device in data:
            if device.get("attachmentPoint"):
                mac = device["mac"][0] if device.get("mac") else "-"
                ipv4 = device["ipv4"][0] if device.get("ipv4") else "-"
                ap = device["attachmentPoint"][0]
                dpid = ap.get("switchDPID", "-")
                port = ap.get("port", "-")
                if ap.get("port", -2) >= 0: # No muestra switches
                    table.add_row([mac, ipv4, dpid, port])
        print(table)
    else:
        print(f'FAILED REQUEST | STATUS: {response.status_code}')


# Función que obtiene el punto de conexión (DPID y puerto) para una MAC dada
def get_attachment_points(mac, controller_ip):
    target_api = '/wm/device/'
    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
    url = f'http://{controller_ip}:8080{target_api}'
    response = requests.get(url=url, headers=headers)

    if response.status_code != 200:
        print("Error en la consulta")
        return None, None
    
    dispositivos = response.json()
    for dispositivo in dispositivos:
        if dispositivo['mac'][0].lower() == mac.lower():
            puntos = dispositivo.get('attachmentPoint', [])
            if puntos:
                punto = puntos[0] # Tomamos el primero si hay varios
                return punto['switchDPID'], punto['port']
    return None, None

# Función que obtiene la ruta entre dos puntos de conexión (switch y puerto)
def get_route(src_dpid, src_port, dst_dpid, dst_port, controller_ip):
    target_api = f'/wm/topology/route/{src_dpid}/{src_port}/{dst_dpid}/{dst_port}/json'
    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
    url = f'http://{controller_ip}:8080{target_api}'
    response = requests.get(url=url, headers=headers)
    if response.status_code != 200:
        print("Error al consultar ruta")
        return None
    
    return response.json()


def build_route(ruta, handler, controller_ip):
    if not ruta:
        print("Error: No hay ruta calculada.")
        return
    
    for step in ruta:
        crear_flow(handler, step, controller_ip)  # Crear el flow para cada paso de la ruta

    print(f"Conexión {handler} establecida exitosamente con los flows generados.")


def crear_flow(handler, step, controller_ip):
    flow_data = {
        "dpid": step["switch"],
        "match": {
            "in_port": step["port"],
            "eth_type": 0x0800,  # IPv4, puedes ajustar esto si usas otros protocolos
            "ipv4_src": step.get("src_ip", "-"),
            "ipv4_dst": step.get("dst_ip", "-")
        },
        "actions": {
            "output": "NORMAL"  # Permitir el flujo normal
        }
    }

    url = f"http://{controller_ip}:8080/wm/v2/flows/{step['switch']}"
    response = requests.post(url, json=flow_data)

    if response.status_code == 200:
        print(f"Flow creado exitosamente: {flow_data}")
    else:
        print(f"Error al crear flow: {response.status_code}, {response.text}")


def main():
    global alumnos, cursos, servidores

    while True:
        menu()
        opcion = input()
        
        if opcion == "8":
            print("Saliendo...")
            break
        
        execute(opcion)

def menu():
    print("\n")
    print("#" * 70)
    print("Network Policy manager de la UPSM")
    print("#" * 70)
    print("\nSelecciona una opción:")
    print("1) Importar")
    print("2) Exportar")
    print("3) Cursos")
    print("4) Alumnos")
    print("5) Servidores")
    print("6) Políticas")
    print("7) Conexiones")
    print("8) Salir")
    print("\n>>> ", end="")

def execute(opcion):
    if opcion == "1":
        print("Opción 1 seleccionada: Importar")
        importar_datos()
    elif opcion == "2":
        print("Opción 2 seleccionada: Exportar")
    elif opcion == "3":
        print("Opción 3 seleccionada: Cursos")
        opcion_cursos()
    elif opcion == "4":
        print("Opción 4 seleccionada: Alumnos")
        opcion_alumnos()
    elif opcion == "5":
        print("Opción 5 seleccionada: Servidores")
        opcion_servidores()
    elif opcion == "6":
        print("Opción 6 seleccionada: Políticas")
    elif opcion == "7":
        print("Opción 7 seleccionada: Conexiones")
        opcion_conexiones()
    elif opcion == "8":
        print("Opción 8 seleccionada: Salir")
    else:
        print("Opción no válida.")


def importar_datos():
    global alumnos, cursos, servidores

    nombre_archivo = input("\nIngrese el nombre del archivo (sin extensión): ")
    ruta = nombre_archivo + '.yaml'
    
    with open(ruta, 'r') as archivo:
        datos = yaml.safe_load(archivo)
    
    alumnos_dict = {alumno['codigo']: Alumno(alumno['nombre'], alumno['codigo'], alumno['mac']) for alumno in datos['alumnos']}
    
    cursos = []
    for curso_data in datos.get('cursos', []):
        curso = Curso(curso_data['nombre'], curso_data['estado'], curso_data['codigo'])
        
        for alumno_codigo in curso_data.get('alumnos', []):
            alumno = alumnos_dict.get(alumno_codigo)
            if alumno:
                curso.add_alumno(alumno)
            else:
                print(f"Alumno con código {alumno_codigo} no encontrado.")
        
        for servidor_data in datos.get('servidores', []):
            servidor = Servidor(servidor_data['nombre'], servidor_data['ip'])
            for servicio_data in servidor_data.get('servicios', []):
                servicio = Servicio(servicio_data['nombre'], servicio_data['protocolo'], servicio_data['puerto'])
                servidor.add_servicio(servicio)
            
            curso.add_servidor(servidor)
        
        cursos.append(curso)
    
    alumnos = list(alumnos_dict.values())

    servidores = []
    for servidor_data in datos.get('servidores', []):
        servidor = Servidor(servidor_data['nombre'], servidor_data['ip'])
        for servicio_data in servidor_data.get('servicios', []):
            servicio = Servicio(servicio_data['nombre'], servicio_data['protocolo'], servicio_data['puerto'])
            servidor.add_servicio(servicio)
        servidores.append(servidor)


def opcion_cursos():

    while True:
        print("\n")
        print("\nSelecciona una opción:")
        print("1) Listar")
        print("2) Mostrar propiedades")
        print("3) Actualizar")
        print("4) Regresar")
        print("\n>>> ", end="")        
        
        opcion = input()
        
        if opcion == "4":
            print("Volviendo al menú principal...")
            break
        
        if opcion == "1":
            print("Opción 1 seleccionada: Listar")
            mostrar_cursos()
        elif opcion == "2":
            print("Opción 2 seleccionada: Mostrar propiedades")
            mostrar_detalles_cursos()
        elif opcion == "3":
            print("Opción 3 seleccionada: Actualizar")
            actualizar_alumnos_curso()
        elif opcion == "4":
            print("Opción 4 seleccionada: Regresar")
        else:
            print("Opción no válida.")

    
def opcion_alumnos():

    while True:
        print("\n")
        print("\nSelecciona una opción:")
        print("1) Listar")
        print("2) Mostrar detalles")
        print("3) Regresar")
        print("\n>>> ", end="")        
        
        opcion = input()
        
        if opcion == "3":
            print("Volviendo al menú principal...")
            break
        
        if opcion == "1":
            print("Opción 1 seleccionada: Listar")
            listar_alumnos()
        elif opcion == "2":
            print("Opción 2 seleccionada: Mostrar detalles")
            mostrar_alumnos()
        elif opcion == "3":
            print("Opción 3 seleccionada: Regresar")
        else:
            print("Opción no válida.")


def opcion_servidores():

    while True:
        print("\n")
        print("\nSelecciona una opción:")
        print("1) Listar")
        print("2) Mostrar detalles")
        print("3) Regresar")
        print("\n>>> ", end="")        
        
        opcion = input()
        
        if opcion == "3":
            print("Volviendo al menú principal...")
            break
        
        if opcion == "1":
            print("Opción 1 seleccionada: Listar")
            listar_servidores()
        elif opcion == "2":
            print("Opción 2 seleccionada: Mostrar detalles")
            mostrar_servidores()
        elif opcion == "3":
            print("Opción 3 seleccionada: Regresar")
        else:
            print("Opción no válida.")


def opcion_conexiones():
    global conexiones 
    while True:
        print("\nSelecciona una opción:")
        print("1) Crear conexión")
        print("2) Listar conexiones")
        print("3) Mostrar detalles de una conexión")
        print("4) Borrar conexión")
        print("5) Regresar")
        print("\n>>> ", end="")        

        opcion = input()
        
        if opcion == "5":
            print("Volviendo al menú principal...")
            break
        
        if opcion == "1":
            print("Opción 1 seleccionada: Crear conexión")
            handler = input("Ingrese el handler de la conexión: ")
            alumno_codigo = input("Ingrese el código del alumno: ")
            servidor_nombre = input("Ingrese el nombre del servidor: ")
            servicio_nombre = input("Ingrese el nombre del servicio: ")

            # Buscar el alumno y el servidor
            alumno = next((a for a in alumnos if str(a.codigo) == str(alumno_codigo)), None)
            servidor = next((s for s in servidores if s.nombre == servidor_nombre), None)
            servicio = None
            if servidor:
                servicio = next((s for s in servidor.servicios if s.nombre == servicio_nombre), None)

            if not alumno or not servidor or not servicio:
                print("Alumno, servidor o servicio no encontrado.")
                continue

            conexion = crear_conexion(handler, alumno, servidor, servicio, controller_ip)
            if conexion:
                conexiones.append(conexion)
                print(f"Conexión {handler} creada exitosamente.")
        
        elif opcion == "2":
            print("Opción 2 seleccionada: Listar conexiones")
            listar_conexiones(conexiones)

        elif opcion == "3":
            print("Opción 3 seleccionada: Mostrar detalles")
            handler = input("Ingrese el handler de la conexión: ")
            conexion = next((c for c in conexiones if c.handler == handler), None)
            if conexion:
                mostrar_detalle(conexion)
            else:
                print(f"No se encontró una conexión con el handler {handler}.")
        
        elif opcion == "4":
            print("Opción 4 seleccionada: Borrar conexión")
            handler = input("Ingrese el handler de la conexión: ")
            borrar_conexion(conexiones, handler)

        else:
            print("Opción no válida.")


# Crear una nueva conexión
def crear_conexion(handler, alumno, servidor, servicio, controller_ip):
    conexion = Conexion(handler, alumno, servidor, servicio)
    ruta = conexion.calcular_ruta(controller_ip)
    if ruta:
        conexion.crear_flows(controller_ip)
        return conexion
    return None

# Listar todas las conexiones
def listar_conexiones(conexiones):
    table = PrettyTable()
    table.field_names = ["Handler", "Alumno", "Servidor", "Servicio"]
    
    for conexion in conexiones:
        table.add_row([conexion.handler, conexion.alumno.nombre, conexion.servidor.nombre, conexion.servicio.nombre])
    
    print(table)

# Mostrar detalles de una conexión
def mostrar_detalle(conexion):
    print(f"\nDetalles de la conexión {conexion.handler}:")
    print(f"Alumno: {conexion.alumno.nombre} (MAC: {conexion.alumno.mac})")
    print(f"Servidor: {conexion.servidor.nombre} (IP: {conexion.servidor.direccion_ip})")
    print(f"Servicio: {conexion.servicio.nombre} (Protocolo: {conexion.servicio.protocolo}, Puerto: {conexion.servicio.puerto})")
    print(f"Ruta: {conexion.ruta}")

# Borrar una conexión
def borrar_conexion(conexiones, handler):
    conexion = next((c for c in conexiones if c.handler == handler), None)
    if conexion:
        conexiones.remove(conexion)
        print(f"Conexión {handler} eliminada.")
    else:
        print(f"No se encontró una conexión con el handler {handler}.")


def mostrar_detalles_cursos():
    global cursos

    codigo_curso = input("\nIngrese el código del curso para ver los detalles: ")

    curso_encontrado = None
    for curso in cursos:
        if curso.codigo == codigo_curso:
            curso_encontrado = curso
            break

    if not curso_encontrado:
        print(f"No se encontró un curso con el código {codigo_curso}.")
        return

    print(f"\nDetalles del curso: {curso_encontrado.nombre} (Código: {curso_encontrado.codigo})")

    table_alumnos = PrettyTable()
    table_alumnos.field_names = ["Nombre", "Código", "MAC"]

    for alumno in curso_encontrado.alumnos:
        table_alumnos.add_row([alumno.nombre, alumno.codigo, alumno.mac])

    print("\nAlumnos en este curso:")
    print(table_alumnos)

    table_servidores = PrettyTable()
    table_servidores.field_names = ["Nombre del Servidor", "IP"]

    for servidor in curso_encontrado.servidores:
        table_servidores.add_row([servidor.nombre, servidor.direccion_ip])
        for servicio in servidor.servicios:
            table_servidores.add_row([f"  Servicio: {servicio.nombre}", f"Protocolo: {servicio.protocolo} - Puerto: {servicio.puerto}"])

    print("\nServidores en este curso:")
    print(table_servidores)


def actualizar_alumnos_curso():

    while True:
        print("\n")
        print("\nSelecciona una opción:")
        print("1) Añadir alumno a curso")
        print("2) Eliminar alumno de curso")
        print("3) Regresar")
        print("\n>>> ", end="")        
        
        opcion = input()
        
        if opcion == "3":
            print("Volviendo al menú principal...")
            break
        
        if opcion == "1":
            print("Opción 1 seleccionada: Añadir alumno")
            añadir_alumno_a_curso()
        elif opcion == "2":
            print("Opción 2 seleccionada: Eliminar alumno")
            eliminar_alumno_de_curso()
        elif opcion == "3":
            print("Opción 3 seleccionada: Regresar")
        else:
            print("Opción no válida.")


def añadir_alumno_a_curso():
    global cursos, alumnos
    mostrar_cursos()
    codigo_curso = input("Ingrese el código del curso: ")

    mostrar_alumnos()
    codigo_alumno = input("Ingrese el código del alumno que desea añadir: ")

    curso_encontrado = None
    for curso in cursos:
        if curso.codigo == codigo_curso:
            curso_encontrado = curso
            break

    if not curso_encontrado:
        print(f"No se encontró un curso con el código {codigo_curso}.")
        return

    alumno_encontrado = None
    for alumno in alumnos:
        if alumno.codigo == int(codigo_alumno):
            alumno_encontrado = alumno
            break

    if not alumno_encontrado:
        print(f"No se encontró un alumno con el código {codigo_alumno}.")
        return

    if alumno_encontrado in curso_encontrado.alumnos:
        print(f"El alumno {alumno_encontrado.nombre} ya está registrado en el curso {curso_encontrado.nombre}.")
        return

    curso_encontrado.add_alumno(alumno_encontrado)
    print(f"Alumno {alumno_encontrado.nombre} añadido al curso {curso_encontrado.nombre}.")


def eliminar_alumno_de_curso():
    global cursos
    mostrar_cursos()
    codigo_curso = input("Ingrese el código del curso: ")

    mostrar_alumnos()
    codigo_alumno = input("Ingrese el código del alumno que desea eliminar: ")

    curso_encontrado = None
    for curso in cursos:
        if curso.codigo == codigo_curso:
            curso_encontrado = curso
            break

    if not curso_encontrado:
        print(f"No se encontró un curso con el código {codigo_curso}.")
        return

    alumno_a_eliminar = None
    for alumno in curso_encontrado.alumnos:
        if str(alumno.codigo) == str(codigo_alumno):
            alumno_a_eliminar = alumno
            break

    if not alumno_a_eliminar:
        print(f"No se encontró un alumno con el código {codigo_alumno} en el curso {curso_encontrado.nombre}.")
        return

    curso_encontrado.del_alumno(alumno_a_eliminar)
    print(f"Alumno {alumno_a_eliminar.nombre} eliminado del curso {curso_encontrado.nombre}.")


def listar_servidores():
    global servidores
    table_servidores = PrettyTable()
    table_servidores.field_names = ["Nombre del Servidor", "IP"]

    for servidor in servidores:
        table_servidores.add_row([servidor.nombre, servidor.direccion_ip])            

    print("\nLista de Servidores:")
    print(table_servidores)


def mostrar_servidores():
    global servidores
    nombre_servidor = input("\nIngrese el nombre del servidor para ver sus servicios: ")

    servidor_encontrado = None
    for servidor in servidores:
        if servidor.nombre.lower() == nombre_servidor.lower():
            servidor_encontrado = servidor
            break

    if not servidor_encontrado:
        print(f"No se encontró un servidor con el nombre {nombre_servidor}.")
        return

    table_servidores = PrettyTable()
    table_servidores.field_names = ["Nombre del Servidor", "IP", "Servicio", "Protocolo", "Puerto"]

    for servicio in servidor_encontrado.servicios:
        table_servidores.add_row([servidor_encontrado.nombre, servidor_encontrado.direccion_ip, servicio.nombre, servicio.protocolo, servicio.puerto])

    print(f"\nServicios del servidor {servidor_encontrado.nombre} (IP: {servidor_encontrado.direccion_ip}):")
    print(table_servidores)


def listar_alumnos():
    while True:
        print("\n")
        print("\nSelecciona una opción:")
        print("1) Listar todos")
        print("2) Listar por curso")
        print("3) Regresar")
        print("\n>>> ", end="")        
        
        opcion = input()
        
        if opcion == "3":
            print("Volviendo al menú principal...")
            break
        
        if opcion == "1":
            print("Opción 1 seleccionada: Listar todos")
            mostrar_alumnos()
        elif opcion == "2":
            print("Opción 2 seleccionada: Listar por curso")
            mostrar_alumnos_curso()
        elif opcion == "3":
            print("Opción 3 seleccionada: Regresar")
        else:
            print("Opción no válida.")


def mostrar_alumnos():
    global alumnos
    table = PrettyTable()
    table.field_names = ["Código", "Nombre", "MAC"]
    
    for alumno in alumnos:
        table.add_row([alumno.codigo, alumno.nombre, alumno.mac])
    
    print("\nLista de Alumnos:")
    print(table)


def mostrar_alumnos_curso():
    global cursos

    mostrar_cursos()
    codigo_curso = input("\nIngrese el código del curso para ver los alumnos: ")

    curso_encontrado = None
    for curso in cursos:
        if curso.codigo == codigo_curso:
            curso_encontrado = curso
            break

    if not curso_encontrado:
        print(f"No se encontró un curso con el código {codigo_curso}.")
        return

    table = PrettyTable()
    table.field_names = ["Código", "Nombre", "MAC"]

    for alumno in curso_encontrado.alumnos:
        table.add_row([alumno.codigo, alumno.nombre, alumno.mac])

    print(f"\nAlumnos en el curso {curso_encontrado.nombre} (Código: {curso_encontrado.codigo}):")
    print(table)


def mostrar_cursos():
    global cursos
    table = PrettyTable()
    table.field_names = ["Código", "Nombre", "Estado"]
    
    for curso in cursos:
        table.add_row([curso.codigo, curso.nombre, curso.estado])
    
    print("\nLista de Cursos:")
    print(table)


if __name__ == "__main__":
    controller_ip = "10.20.12.65"
    # Mostrar lista de dispositivos detectados
    # get_list_devices(controller_ip)
    main()