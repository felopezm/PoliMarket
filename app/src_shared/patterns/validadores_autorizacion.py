"""Patron Chain of Responsibility (GoF) aplicado a la autorizacion de un
vendedor antes de registrar un pedido.

Antes, `ComponenteVentas.crearPedido` solo llamaba a
`componente_rrhh.verificarAutorizacion(vendedor_id)`: una unica condicion.
Aqui se encadenan validadores independientes (zona asignada, credito,
autorizacion vigente en RRHH) para que agregar una regla nueva no
implique modificar las existentes.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod


class ResultadoValidacion:
    """Acumula el resultado de recorrer la cadena de validadores."""

    def __init__(self) -> None:
        self.aprobado = True
        self.motivo_rechazo = ""

    def rechazar(self, motivo: str) -> None:
        self.aprobado = False
        self.motivo_rechazo = motivo

    def es_valido(self) -> bool:
        return self.aprobado


class IValidadorAutorizacion(ABC):
    @abstractmethod
    def set_siguiente(self, validador: "IValidadorAutorizacion") -> "IValidadorAutorizacion":
        ...

    @abstractmethod
    def validar(self, vendedor: sqlite3.Row, resultado: ResultadoValidacion) -> None:
        ...


class ValidadorAutorizacionBase(IValidadorAutorizacion):
    """Estereotipo «ChainOfResponsibility» del diagrama UML."""

    def __init__(self) -> None:
        self._siguiente: IValidadorAutorizacion | None = None

    def set_siguiente(self, validador: IValidadorAutorizacion) -> IValidadorAutorizacion:
        self._siguiente = validador
        return validador

    def validar(self, vendedor: sqlite3.Row, resultado: ResultadoValidacion) -> None:
        if not resultado.es_valido():
            return
        if self._siguiente is not None:
            self._siguiente.validar(vendedor, resultado)


class ValidadorZonaAsignada(ValidadorAutorizacionBase):
    def validar(self, vendedor: sqlite3.Row, resultado: ResultadoValidacion) -> None:
        zona = vendedor["zona"] if "zona" in vendedor.keys() else None
        if not zona:
            resultado.rechazar("El vendedor no tiene zona asignada.")
            return
        super().validar(vendedor, resultado)


class ValidadorCredito(ValidadorAutorizacionBase):
    """En el esquema actual no existe un campo de credito por vendedor; se
    documenta como punto de extension y por ahora siempre aprueba, dejando
    la cadena lista para el dia que se agregue esa columna sin tocar los
    demas validadores.
    """

    def validar(self, vendedor: sqlite3.Row, resultado: ResultadoValidacion) -> None:
        super().validar(vendedor, resultado)


class ValidadorRRHH(ValidadorAutorizacionBase):
    def __init__(self, componente_rrhh) -> None:
        super().__init__()
        self._componente_rrhh = componente_rrhh

    def validar(self, vendedor: sqlite3.Row, resultado: ResultadoValidacion) -> None:
        if not self._componente_rrhh.verificarAutorizacion(int(vendedor["id"])):
            resultado.rechazar("El vendedor no tiene autorizacion activa de RRHH.")
            return
        super().validar(vendedor, resultado)


def construir_cadena_autorizacion(componente_rrhh) -> IValidadorAutorizacion:
    """Arma la cadena zona -> credito -> RRHH, tal como la describe el
    diagrama de clases."""
    zona = ValidadorZonaAsignada()
    credito = ValidadorCredito()
    rrhh = ValidadorRRHH(componente_rrhh)
    zona.set_siguiente(credito)
    credito.set_siguiente(rrhh)
    return zona
