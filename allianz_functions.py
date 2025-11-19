import pandas as pd
import math

# ================================================================
#                    🔵 Funciones de Valor Presente
# ================================================================

def valor_presente(vf, inflacion_anual, años):
    """
    Trae un valor futuro a valor presente descontando inflación.
    """
    return vf / ((1 + inflacion_anual) ** años)


def serie_vp(lista_vf, inflacion_anual, años):
    """
    Convierte una serie de valores mensuales futuros en VP.
    Se descuenta TODO con el mismo factor (año del retiro).
    Esto es correcto porque la simulación completa está a valores futuros
    al final de la etapa laboral.
    """
    factor = (1 + inflacion_anual) ** años
    return [x / factor for x in lista_vf]


def df_convertir_columna_vp(df, col_name, inflacion_anual, años_retiro):
    """
    Agrega una columna VP a un DataFrame basado en otra columna de valores futuros.
    """
    factor = (1 + inflacion_anual) ** años_retiro
    df[col_name + "_VP"] = df[col_name] / factor
    return df

def simular_retiro_ppr(
    capital_inicial,
    tasa_anual,
    inflacion_anual,
    udi_inicial,
    meses,
    retiro_mensual,
):
    """
    Simula el retiro dejando el dinero dentro del PPR:
    - Cobra 15 UDIS/mes (ajustadas por inflación y IVA)
    - Cobra 0.1% mensual + IVA sobre el saldo
    - Genera rendimiento mensual tasa_anual
    - Retiro fijo 'retiro_mensual'
    """
    tasa_mensual = (1 + tasa_anual) ** (1/12) - 1
    saldo = capital_inicial
    udi_actual = udi_inicial

    saldos = []
    mes_agotado = None

    for mes in range(1, meses + 1):
        if saldo <= 0 and mes_agotado is None:
            mes_agotado = mes - 1
            saldos.append(0.0)
            continue

        # rendimiento del mes
        interes = saldo * tasa_mensual

        # cargo fijo 15 UDIS * (1+inflación) * IVA
        cargo_fijo = 15 * udi_actual * (1 + inflacion_anual) * 1.16

        # saldo después de rendimiento, cargos y retiro
        base = saldo + interes - cargo_fijo - retiro_mensual

        # cargo de gestión 0.1% + IVA
        cargo_gestion = base * 0.001 * 1.16
        saldo = base - cargo_gestion

        if saldo < 0:
            saldo = 0.0

        saldos.append(saldo)

        if mes % 12 == 0:
            udi_actual *= (1 + inflacion_anual)

        if saldo <= 0 and mes_agotado is None:
            mes_agotado = mes

    if mes_agotado is None:
        mes_agotado = meses

    return saldos, mes_agotado


def simular_retiro_simple(
    capital_inicial,
    tasa_anual,
    meses,
    retiro_mensual,
):
    """
    Simula el retiro si sacas TODO y lo metes a CETES / renta fija:
    - Sin comisiones
    - Rendimiento tasa_anual
    - Retiro fijo 'retiro_mensual'
    """
    tasa_mensual = (1 + tasa_anual) ** (1/12) - 1
    saldo = capital_inicial

    saldos = []
    mes_agotado = None

    for mes in range(1, meses + 1):
        if saldo <= 0 and mes_agotado is None:
            mes_agotado = mes - 1
            saldos.append(0.0)
            continue

        saldo = saldo * (1 + tasa_mensual) - retiro_mensual

        if saldo < 0:
            saldo = 0.0

        saldos.append(saldo)

        if saldo <= 0 and mes_agotado is None:
            mes_agotado = mes

    if mes_agotado is None:
        mes_agotado = meses

    return saldos, mes_agotado


def buscar_retiro_optimo(capital_inicial, meses, simulador):
    """
    Binary search para encontrar el retiro mensual máximo
    que deja el saldo ~0 al final de 'meses'.
    simulador(capital_inicial, meses, retiro_mensual) -> (saldos, mes_agotado)
    """
    low = 0.0
    high = capital_inicial / meses * 2  # cota superior burda
    mejor_retiro = 0.0
    mejor_saldos = None
    mejor_mes = None

    for _ in range(40):
        mid = (low + high) / 2
        saldos, mes_agotado = simulador(capital_inicial, meses, mid)
        saldo_final = saldos[-1]

        mejor_retiro = mid
        mejor_saldos = saldos
        mejor_mes = mes_agotado

        if saldo_final > 0:
            # sobró dinero → podemos retirar más
            low = mid
        else:
            # nos quedamos cortos / llegamos a 0 antes → hay que bajar el retiro
            high = mid

    return mejor_retiro, mejor_saldos, mejor_mes


def simular_allianz_simple(
    aportes: list,
    inflacion_anual: float,
    rendimiento_anual: float,
    valor_udi_inicial: float,
    usar_bono: bool,
    bono_monto: float
):
    """
    Versión simple MEJORADA de la simulación Allianz:

    ✔ Aportes mensuales (crecientes o no)
    ✔ Bono al inicio (opcional)
    ✔ Rendimiento mensual
    ✔ Comisión mensual fija: 15 UDIS
    ✔ Cargo de gestión: 0.1% mensual sobre el saldo
    ✔ Cargo administrativo: 0.9% cada 3 meses
    ✔ UDI aumenta con la inflación anual
    """

    meses = len(aportes)
    r_m = (1 + rendimiento_anual) ** (1/12) - 1

    saldo = bono_monto if usar_bono else 0.0
    valor_udi = valor_udi_inicial

    historial = []

    for m in range(meses):
        aporte = aportes[m]

        # 1) Aportación
        saldo += aporte

        # 2) Cargo de Gestión (0.1% mensual)
        saldo -= saldo * 0.001   # 0.1%

        # 3) Rendimiento mensual
        saldo *= (1 + r_m)

        # 4) Comisión mensual fija 15 UDIS
        saldo -= valor_udi * 15

        # 5) Cargo administrativo 0.9% trimestral
        if (m + 1) % 3 == 0:
            saldo -= saldo * 0.009  # 0.9%

        # Guardar registro
        historial.append({
            "Mes": m,
            "Aporte": aporte,
            "UDI": valor_udi,
            "Saldo": saldo
        })

        # 6) UDI crece anual
        if (m + 1) % 12 == 0:
            valor_udi *= (1 + inflacion_anual)

    df = pd.DataFrame(historial)
    return saldo, df

def generar_aportes(aporte_inicial, meses, inflacion_anual, incrementar):
    aportes = []
    aporte = aporte_inicial

    for m in range(meses):
        # agregar aporte actual
        aportes.append(aporte)

        # cada 12 meses (inicio de año) aumentar aporte
        if incrementar and (m > 0) and (m % 12 == 0):
            aporte *= (1 + inflacion_anual)

    return aportes

def generar_aportes_con_offset(aporte_inicial, meses, inflacion_anual, incrementar, offset, nuevo_aporte):
    aportes = []
    aporte = aporte_inicial

    for m in range(meses):
        if m == offset:
            aporte = nuevo_aporte * (1 + inflacion_anual)

        # agregar aporte actual
        aportes.append(aporte)

        # cada 12 meses (inicio de año) aumentar aporte
        if incrementar and (m > 0) and (m % 12 == 0):
            aporte *= (1 + inflacion_anual)

    return aportes

def generar_aportes_early_stop(
    aporte_inicial,
    meses,
    inflacion_anual,
    incrementar,
    meses_aportando
):
    aportes = []
    aporte = aporte_inicial

    for m in range(meses):
        if m < meses_aportando:
            # aportas normalmente
            aportes.append(aporte)
        else:
            # ya no aportas nada
            aportes.append(0)

        # cada año sube la aportación
        if incrementar and (m > 0) and (m % 12 == 0):
            aporte *= (1 + inflacion_anual)

    return aportes

def calcular_bono_fidelidad(aporte_mensual, plazo, usar_bono=True):
    if not usar_bono:
        return 0, 0  # (porcentaje, bono)

    if plazo > 25:
        plazo = 25

    porcentaje = obtener_bono_fidelidad_porcentaje(aporte_mensual, plazo)
    bono = aporte_mensual * 12 * porcentaje
    return porcentaje, bono

def obtener_bono_fidelidad_porcentaje(aporte_mensual, plazo):
    """
    Regresa el porcentaje de bono de fidelidad basado en:
    - aporte mensual
    - plazo comprometido
    Tabla oficial Allianz (2024)
    """

    # 1) Clasificar aporte anual
    aporte_anual = aporte_mensual * 12

    if 12000 <= aporte_anual <= 35999:
        col = 0
    elif 36000 <= aporte_anual <= 59999:
        col = 1
    elif 60000 <= aporte_anual <= 89999:
        col = 2
    else:  # 90,000+
        col = 3

    # 2) Clasificar plazo
    if 10 <= plazo <= 14:
        fila = 0
    elif 15 <= plazo <= 19:
        fila = 1
    elif 20 <= plazo <= 25:
        fila = 2
    else:
        return 0  # fuera del rango permitido por Allianz

    tabla = [
        [0.05, 0.15, 0.25, 0.35],  # 10-14 años
        [0.30, 0.40, 0.50, 0.60],  # 15-19 años
        [0.55, 0.65, 0.75, 1.00],  # 20-25 años
    ]

    return tabla[fila][col]
