
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
import uvicorn
import pickle
import os

from LogicaNodal import Diagrama, Nodo



# ==============================
# Clases base
# ==============================

class Usuario:
    """Representa un usuario del sistema, con sus diagramas personales."""

    def __init__(self, nombre: str, contrseña: str):
        self.nombre:str = nombre
        self.contraseña:str = contrseña
        self.rol:int = 0 #0 = solo ver, 1 = editar diagramas, 2 = crear y editar diagramas.
        self.diagramas: dict[int, Diagrama] = {}
        self.diagrama_actual: Optional[int] = None


class ServidorNodos:
    """Maneja todos los usuarios y sus diagramas en memoria."""

    def __init__(self):
        self.usuarios: dict[str, Usuario] = {}
        self.diagramas: dict[str, Diagrama] = {}
        self.inicio()
        
    def inicio(self):
        """Carga los datos de la base de datos y prepara al servidor para iniciar"""
        try:
            with open('data.pkl', 'rb') as usuarios:
                pass
        except:
            pass
        
            
    
    def apagar(self):
        """Este metodo es el protocolo de apagado del servidor, debe guardar todos los datos nuevos"""
        pass

    def obtener_usuario(self, nombre: str) -> Usuario:
        if nombre not in self.usuarios:
            raise HTTPException(status_code=404, detail=f"Usuario '{nombre}' no encontrado")
        return self.usuarios[nombre]

    def crear_usuario(self, nombre: str, contraseña: str) -> Usuario:
        """Este método registra usuarios nuevos"""
        if nombre in self.usuarios:
            raise HTTPException(status_code=400, detail=f"Usuario '{nombre}' ya existe")
        
        # Creamos el usuario
        else:
            usuario = Usuario(nombre, contraseña)
            self.usuarios[nombre] = usuario
        return usuario
    
    def crearDiagramas(self, usuario:Usuario, nombre_diagrama:str) -> Diagrama:
        """Este método permite a un usuario crear un diagrama nuevo"""
        if usuario.rol != 2:
            raise HTTPException(status_code=404, detail=f"Usuario '{usuario.nombre}' no tiene permitida esta acción.")
        
        # Creamos un diagrama y lo agregamos al diccionario.
        else:
            diagrama = Diagrama(nombre_diagrama)
            self.diagramas[nombre_diagrama] = diagrama
            return diagrama
    
     



# ==============================
# Inicialización del servidor
# ==============================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Código que se ejecuta al iniciar y detener el servidor"""
    global servidor
    servidor = ServidorNodos()
    servidor.crear_usuario("admin")  # usuario inicial de ejemplo
    print("✓ Servidor iniciado con usuario 'admin'")
    yield
    print("✓ Servidor detenido")


app = FastAPI(title="Servidor de Nodos", lifespan=lifespan)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: restringir dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================
# Modelos Pydantic (Validación)
# ==============================

class UsuarioCreate(BaseModel):
    nombre: str

class DiagramaCreate(BaseModel):
    nombre: str

class NodoCreate(BaseModel):
    nombre: str
    id_padre: Optional[int] = None
    num_hijo: Optional[int] = None

class NodoUpdate(BaseModel):
    nombre: Optional[str] = None
    contenido: Optional[str] = None
    gitURL: Optional[str] = None

class EnlaceCreate(BaseModel):
    id_padre: int
    id_hijo: int

class EnlaceDelete(BaseModel):
    id_padre: int
    id_hijo: int


# ==============================
# ENDPOINTS DE USUARIOS
# ==============================

@app.post("/api/usuarios", status_code=201)
def crear_usuario(datos: UsuarioCreate):
    usuario = servidor.crear_usuario(datos.nombre)
    return {"message": f"Usuario '{usuario.nombre}' creado"}

@app.get("/api/usuarios")
def listar_usuarios():
    return {"usuarios": list(servidor.usuarios.keys())}


# ==============================
# ENDPOINTS DE DIAGRAMAS
# ==============================

@app.post("/api/usuarios/{nombre}/diagramas", status_code=201)
def crear_diagrama(nombre: str, datos: DiagramaCreate):
    usuario = servidor.obtener_usuario(nombre)
    nuevo_id = usuario.crear_diagrama(datos.nombre)
    return {"id": nuevo_id, "nombre": datos.nombre, "message": "Diagrama creado"}

@app.get("/api/usuarios/{nombre}/diagramas")
def listar_diagramas(nombre: str):
    usuario = servidor.obtener_usuario(nombre)
    return {"diagramas": [
        {"id": id, "nombre": d.nombre, "num_nodos": len(d.nodos)}
        for id, d in usuario.diagramas.items()
    ]}

@app.get("/api/usuarios/{nombre}/diagramas/{diagrama_id}")
def obtener_diagrama(nombre: str, diagrama_id: int):
    usuario = servidor.obtener_usuario(nombre)
    diag = usuario.obtener_diagrama(diagrama_id)
    return diag.to_dict()

@app.get("/api/usuarios/{nombre}/diagramas/{diagrama_id}/mermaid")
def obtener_mermaid(nombre: str, diagrama_id: int):
    usuario = servidor.obtener_usuario(nombre)
    diag = usuario.obtener_diagrama(diagrama_id)
    return {"mermaid": diag.construirDiagrama(), "nombre": diag.nombre}

@app.delete("/api/usuarios/{nombre}/diagramas/{diagrama_id}")
def eliminar_diagrama(nombre: str, diagrama_id: int):
    usuario = servidor.obtener_usuario(nombre)
    if not usuario.eliminar_diagrama(diagrama_id):
        raise HTTPException(status_code=404, detail="Diagrama no encontrado")
    return {"message": "Diagrama eliminado"}


# ==============================
# ENDPOINTS DE NODOS
# ==============================

@app.post("/api/usuarios/{nombre}/diagramas/{diagrama_id}/nodos", status_code=201)
def crear_nodo(nombre: str, diagrama_id: int, nodo: NodoCreate):
    usuario = servidor.obtener_usuario(nombre)
    diag = usuario.obtener_diagrama(diagrama_id)

    if nodo.id_padre is not None and nodo.id_padre not in diag.nodos:
        raise HTTPException(status_code=404, detail="Nodo padre no encontrado")

    nuevo_id = diag.añadirNodo(nodo.nombre, nodo.id_padre, nodo.num_hijo)
    return {"id": nuevo_id, "message": "Nodo creado"}

@app.get("/api/usuarios/{nombre}/diagramas/{diagrama_id}/nodos")
def listar_nodos(nombre: str, diagrama_id: int):
    usuario = servidor.obtener_usuario(nombre)
    diag = usuario.obtener_diagrama(diagrama_id)
    return {"nodos": [n.to_dict() for n in diag.nodos.values()]}

@app.patch("/api/usuarios/{nombre}/diagramas/{diagrama_id}/nodos/{nodo_id}")
def actualizar_nodo(nombre: str, diagrama_id: int, nodo_id: int, datos: NodoUpdate):
    usuario = servidor.obtener_usuario(nombre)
    diag = usuario.obtener_diagrama(diagrama_id)

    if nodo_id not in diag.nodos:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")

    nodo = diag.nodos[nodo_id]
    if datos.nombre is not None:
        nodo.nombre = datos.nombre
        diag.actualizarHomologos(nodo_id, datos.nombre)
    if datos.contenido is not None:
        nodo.contenido = datos.contenido
    if datos.gitURL is not None:
        nodo.gitURL = datos.gitURL

    return {"message": "Nodo actualizado", "nodo": nodo.to_dict()}

@app.delete("/api/usuarios/{nombre}/diagramas/{diagrama_id}/nodos/{nodo_id}")
def eliminar_nodo(nombre: str, diagrama_id: int, nodo_id: int):
    usuario = servidor.obtener_usuario(nombre)
    diag = usuario.obtener_diagrama(diagrama_id)
    if not diag.eliminarNodo(nodo_id):
        raise HTTPException(status_code=404, detail="Nodo no encontrado")
    return {"message": "Nodo eliminado"}


# ==============================
# ENDPOINTS DE ENLACES
# ==============================

@app.post("/api/usuarios/{nombre}/diagramas/{diagrama_id}/enlaces", status_code=201)
def crear_enlace(nombre: str, diagrama_id: int, enlace: EnlaceCreate):
    usuario = servidor.obtener_usuario(nombre)
    diag = usuario.obtener_diagrama(diagrama_id)
    if not diag.enlazarNodos(enlace.id_padre, enlace.id_hijo):
        raise HTTPException(status_code=400, detail="No se pudo crear el enlace")
    return {"message": "Enlace creado"}

@app.delete("/api/usuarios/{nombre}/diagramas/{diagrama_id}/enlaces")
def eliminar_enlace(nombre: str, diagrama_id: int, enlace: EnlaceDelete):
    usuario = servidor.obtener_usuario(nombre)
    diag = usuario.obtener_diagrama(diagrama_id)
    if enlace.id_padre not in diag.nodos or enlace.id_hijo not in diag.nodos:
        raise HTTPException(status_code=404, detail="Nodo no encontrado")
    padre, hijo = diag.nodos[enlace.id_padre], diag.nodos[enlace.id_hijo]
    if hijo in padre.hijos:
        padre.hijos.remove(hijo)
    if padre in hijo.padres:
        hijo.padres.remove(padre)
    return {"message": "Enlace eliminado"}


# ==============================
# ENDPOINTS DE SALUD
# ==============================

@app.get("/")
def root():
    return {"message": "Servidor de Nodos API", "usuarios": len(servidor.usuarios)}

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ==============================
# EJECUCIÓN LOCAL
# ==============================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
