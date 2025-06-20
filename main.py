# David Alonso Escobedo Cerrón - 20210850
import requests
import yaml
from prettytable import PrettyTable

controller_ip = '10.20.12.65'

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


# Función que obtiene el punto de conexión (DPID y puerto) para una MAC o IP dada
def get_attachment_points(mac_or_ip, controller_ip):
    target_api = '/wm/device/'
    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
    url = f'http://{controller_ip}:8080{target_api}'
    response = requests.get(url=url, headers=headers)

    if response.status_code != 200:
        print("Error en la consulta")
        return None, None
    
    dispositivos = response.json()
    for dispositivo in dispositivos:
        # Buscar por MAC
        if dispositivo.get('mac') and dispositivo['mac'][0].lower() == mac_or_ip.lower():
            puntos = dispositivo.get('attachmentPoint', [])
            if puntos:
                punto = puntos[0] # Tomamos el primero si hay varios
                return punto['switchDPID'], punto['port']
        # Buscar por IP
        if dispositivo.get('ipv4') and dispositivo['ipv4'][0] == mac_or_ip:
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




def insertar_flows(mac_src, ip_dst, protocolo, puerto, handler, controller_ip):
    dpid, port = get_attachment_points(mac_src, controller_ip)
    if not dpid:
        print("No se pudo determinar el punto de conexión.")
        return False

    flow = {
        "switch": dpid,
        "name": handler,
        "priority": "32768",
        "eth_type": "0x0800",
        "ipv4_dst": ip_dst,
        "eth_src": mac_src,
        "ip_proto": "0x06" if protocolo.lower() == "tcp" else "0x11",
        "tp_dst": str(puerto),
        "active": "true",
        "actions": f"output={port}"  
    }
    response = requests.post(f"http://{controller_ip}:8080/wm/staticflowpusher/json", json=flow)
    return response.status_code == 200



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
    
    try:
        with open(ruta, 'r') as archivo:
            datos = yaml.safe_load(archivo)
        print("Archivo cargado correctamente")
    except:
        print("Error al cargar el archivo")
    
    
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
        print("3) Borrar conexión")
        print("4) Regresar")
        print("\n>>> ", end="")        

        opcion = input()
        
        if opcion == "4":
            print("Volviendo al menú principal...")
            break
        
        if opcion == "1":
            print("Opción 1 seleccionada: Crear conexión")
            crear_conexion()
        
        elif opcion == "2":
            print("Opción 2 seleccionada: Listar conexiones")
            listar_conexiones()
        
        elif opcion == "3":
            print("Opción 3 seleccionada: Borrar conexión")
            borrar_conexion()

        else:
            print("Opción no válida.")


def crear_conexion():
    global conexiones
    cod_alumno = input("Ingrese el código del alumno: ")
    nombre_servidor = input("Ingrese el servidor: ")
    nombre_servicio = input("Ingrese el servicio: ").lower()

    alumno = next((a for a in alumnos if str(a.codigo) == cod_alumno), None)
    servidor = next((s for s in servidores if s.nombre == nombre_servidor), None)

    if not alumno or not servidor:
        print("Alumno o servidor no encontrado.")
        return

    # Verificar autorización
    autorizado = False
    for curso in cursos:
        if curso.estado == "DICTANDO" and alumno in curso.alumnos:
            for srv in curso.servidores:
                if srv.nombre == nombre_servidor:
                    for servicio_srv in srv.servicios:
                        if servicio_srv.nombre == nombre_servicio:
                            autorizado = True
                            break
                    if autorizado:
                        break
            if autorizado:
                break

    if not autorizado:
        print("ERROR")
        print("El alumno no pertenece a un CURSO válido con estado DICTANDO")
        return

    servicio_obj = next((x for x in servidor.servicios if x.nombre == nombre_servicio), None)

    if servicio_obj:
        mac_src = alumno.mac
        ip_dst = servidor.direccion_ip
        protocolo = servicio_obj.protocolo
        puerto = servicio_obj.puerto
        handler = f"{alumno.codigo}-{servidor.nombre}-{servicio_obj.nombre}"
        
        success = insertar_flows(mac_src, ip_dst, protocolo, puerto, handler, controller_ip)

        if success:
            conexiones.append(Conexion(handler, alumno, servidor, servicio_obj))
            print(f"Conexión creada con handler: {handler}")
        else:
            print("Error al insertar flow.")
    else:
        print("Servicio no encontrado.")


def listar_conexiones():
    global conexiones
    if not conexiones:
        print("No hay conexiones registradas.")
    else:
        table = PrettyTable()
        table.field_names = ["Handler", "Alumno", "Servidor", "Servicio"]
        for c in conexiones:
            table.add_row([c.handler, c.alumno.nombre, c.servidor.nombre, c.servicio.nombre])
        print(table)

def borrar_conexion():
    global conexiones
    handler = input("Ingrese el handler de la conexión a eliminar: ")
    conexion = next((c for c in conexiones if c.handler == handler), None)
    if conexion:
        requests.delete(f"http://{controller_ip}:8080/wm/staticflowpusher/json", json={"name": handler})
        conexiones.remove(conexion)
        print(f"Conexión con handler '{handler}' eliminada correctamente.")
    else:
        print("No se encontró una conexión con ese handler.")


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
    main()