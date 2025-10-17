from itertools import zip_longest

class Nodo():
    def __init__(self):
        self.id = int()
        self.nombre = str()
        self.hijos: list[Nodo] = []
        self.padres: list[Nodo] = []  
        self.restricciones_propias = set()
        self.restricciones_heredadas: list[set] = []
        self.homologos = set()
        self.contenido = str()
        self.gitURL = str()
    
    @property
    def restricciones(self):
        restric = self.restricciones_heredadas.copy()
        restric.append(self.restricciones_propias)
        return restric
    
    def obtenerDiagrama(self):
        """Retorna las conexiones de este nodo con sus hijos"""
        diagrama = []
        for hijo in self.hijos:
            # Formato Mermaid: ID_PADRE --> ID_HIJO[Nombre]
            diagrama.append(f'{self.id}[{self.nombre}] --> {hijo.id}[{hijo.nombre}]')
        return diagrama
    
    def to_dict(self):
        """Serializa el nodo a diccionario para enviar por HTTP"""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'hijos': [h.id for h in self.hijos],
            'padres': [p.id for p in self.padres],
            'restricciones_propias': list(self.restricciones_propias),
            'restricciones_heredadas': [list(s) for s in self.restricciones_heredadas],
            'homologos': list(self.homologos),
            'contenido': self.contenido,
            'gitURL': self.gitURL
        }


class Diagrama():
    def __init__(self, nombre="Diagrama sin nombre"):
        self.nombre = nombre
        self.nodos: dict[int, Nodo] = {}
        self.nodos_visibles: dict[int, Nodo] = {}
        self._siguiente_id = 1
        self.nodo_raiz_id = None
        
        # Crear nodo raíz automáticamente
        self._crear_nodo_raiz()
    
    def _crear_nodo_raiz(self):
        """Crea el nodo raíz con el nombre del diagrama"""
        nodo = Nodo()
        nodo.id = self._siguiente_id
        self._siguiente_id += 1
        nodo.nombre = self.nombre
        self.nodos[nodo.id] = nodo
        self.nodo_raiz_id = nodo.id
    
    def actualizarHomologos(self, id: int, nombre: str) -> None:
        """Encuentra y actualiza nodos con el mismo nombre"""
        if id not in self.nodos:
            return
            
        homologos = set()
        
        for nodo in self.nodos.values():
            if nodo.nombre == nombre and nodo.id != id:
                homologos.add(nodo.id)
                nodo.homologos.add(id)
        
        self.nodos[id].homologos = homologos
    
    def añadirNodo(self, nombre: str, id_padre: int = None, num_hijo: int = None) -> int:
        """Crea y añade un nodo al diagrama. Retorna el ID del nodo creado"""
        
        # Crear nodo
        nodo = Nodo()
        nodo.id = self._siguiente_id
        self._siguiente_id += 1
        nodo.nombre = nombre
        
        # Si tiene padre, configurar relaciones
        if id_padre is not None and id_padre in self.nodos:
            padre = self.nodos[id_padre]
            
            # Añadir padre
            nodo.padres.append(padre)
            
            # Heredar restricciones
            nodo.restricciones_heredadas = padre.restricciones.copy()
            
            # Anexar a la lista de hijos del padre
            if num_hijo is not None and 0 <= num_hijo <= len(padre.hijos):
                padre.hijos.insert(num_hijo, nodo)
            else:
                padre.hijos.append(nodo)
        
        # Añadir al diagrama
        self.nodos[nodo.id] = nodo
        
        # Actualizar homólogos
        self.actualizarHomologos(nodo.id, nombre)
        
        return nodo.id
    
    def eliminarNodo(self, id: int) -> bool:
        """Elimina un nodo y todos sus hijos recursivamente"""
        if id not in self.nodos:
            return False
        
        nodo = self.nodos[id]
        
        # Eliminar recursivamente todos los hijos
        hijos_copia = nodo.hijos.copy()
        for hijo in hijos_copia:
            self.eliminarNodo(hijo.id)
        
        # Guardar info antes de eliminar
        homologos = nodo.homologos.copy()
        nombre = nodo.nombre
        
        # Eliminar referencias en padres
        for padre in nodo.padres:
            if padre.id in self.nodos:
                padre.hijos = [h for h in padre.hijos if h.id != id]
        
        # Eliminar del diccionario
        del self.nodos[id]
        
        # Actualizar homólogos restantes
        for homologo_id in homologos:
            if homologo_id in self.nodos:
                self.nodos[homologo_id].homologos.discard(id)
        
        return True
    
    def enlazarNodos(self, id_padre: int, id_hijo: int) -> bool:
        """Crea una conexión padre-hijo entre nodos existentes"""
        if id_padre not in self.nodos or id_hijo not in self.nodos:
            return False
        
        padre = self.nodos[id_padre]
        hijo = self.nodos[id_hijo]
        
        # Verificar que no exista ya la conexión
        if hijo in padre.hijos:
            return False
        
        # Verificar que no se cree un ciclo
        if self._creaCiclo(id_padre, id_hijo):
            return False
        
        # Crear enlace
        padre.hijos.append(hijo)
        hijo.padres.append(padre)
        
        # Actualizar restricciones heredadas
        nuevas_restricciones = padre.restricciones
        restricciones_actuales = hijo.restricciones_heredadas
        
        restricciones_combinadas = [
            a | b for a, b in zip_longest(
                nuevas_restricciones, 
                restricciones_actuales, 
                fillvalue=set()
            )
        ]
        hijo.restricciones_heredadas = restricciones_combinadas
        
        # Propagar restricciones a descendientes
        self._propagarRestricciones(hijo.id)
        
        return True
    
    def _creaCiclo(self, id_padre: int, id_hijo: int) -> bool:
        """Verifica si enlazar estos nodos crearía un ciclo"""
        visitados = set()
        
        def tiene_descendiente(nodo_id: int, objetivo: int) -> bool:
            if nodo_id == objetivo:
                return True
            if nodo_id in visitados:
                return False
            
            visitados.add(nodo_id)
            
            if nodo_id in self.nodos:
                for hijo in self.nodos[nodo_id].hijos:
                    if tiene_descendiente(hijo.id, objetivo):
                        return True
            return False
        
        return tiene_descendiente(id_hijo, id_padre)
    
    def _propagarRestricciones(self, id_nodo: int) -> None:
        """Propaga restricciones a todos los descendientes"""
        if id_nodo not in self.nodos:
            return
        
        nodo = self.nodos[id_nodo]
        
        for hijo in nodo.hijos:
            nuevas_restricciones = nodo.restricciones
            restricciones_actuales = hijo.restricciones_heredadas
            
            restricciones_combinadas = [
                a | b for a, b in zip_longest(
                    nuevas_restricciones,
                    restricciones_actuales,
                    fillvalue=set()
                )
            ]
            hijo.restricciones_heredadas = restricciones_combinadas
            
            # Recursión
            self._propagarRestricciones(hijo.id)
    
    def _construirDiagrama(self) -> str:
        """
        Construye el código Mermaid del diagrama completo.
        Retorna un string listo para enviar al cliente.
        """
        if not self.nodos:
            return "graph TD\n    empty[Sin nodos]"
        
        lineas = ["graph TD"]
        
        # Obtener todas las conexiones
        for nodo in self.nodos.values():
            conexiones = nodo.obtenerDiagrama()
            lineas.extend([f"    {conexion}" for conexion in conexiones])
        
        # Agregar nodos sin hijos (hojas)
        nodos_con_conexiones = set()
        for nodo in self.nodos.values():
            if nodo.hijos:
                nodos_con_conexiones.add(nodo.id)
                for hijo in nodo.hijos:
                    nodos_con_conexiones.add(hijo.id)
        
        # Nodos raíz o aislados
        for nodo in self.nodos.values():
            if nodo.id not in nodos_con_conexiones:
                lineas.append(f"    {nodo.id}[{nodo.nombre}]")
        
        return "\n".join(lineas)
    
    def to_dict(self) -> dict:
        """Serializa el diagrama completo para enviar por HTTP"""
        return {
            'nombre': self.nombre,
            'nodo_raiz_id': self.nodo_raiz_id,
            'nodos': {id: nodo.to_dict() for id, nodo in self.nodos.items()},
            'mermaid': self._construirDiagrama()
        }
    
    def obtenerNodo(self, id: int) -> dict | None:
        """Obtiene información de un nodo específico"""
        if id not in self.nodos:
            return None
        return self.nodos[id].to_dict()

    def ocultarRama(self, id: int) -> None:
        pass



if __name__ == "__main__":
    # Crear diagrama
    diag = Diagrama("Proyecto Software")
    
    # Crear nodos
    root = diag.añadirNodo("Inicio")
    req1 = diag.añadirNodo("Análisis", root)
    req2 = diag.añadirNodo("Diseño", root)
    req3 = diag.añadirNodo("Implementación", req2)
    req4 = diag.añadirNodo("Pruebas", req3)
    
    # Ver diagrama
    print(diag.construirDiagrama())
    print("\n" + "="*50 + "\n")
    print(diag.to_dict())