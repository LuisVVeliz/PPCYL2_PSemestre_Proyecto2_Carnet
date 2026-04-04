class MatrizDispersa:

    def __init__(self):
        self.nodos = []

    def insertar(self, fila, columna, valor):

        nuevo = {
            "fila": fila,
            "columna": columna,
            "valor": valor
        }

        self.nodos.append(nuevo)

    def mostrar(self):
        return self.nodos