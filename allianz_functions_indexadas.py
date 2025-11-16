import pandas as pd
from allianz_functions import serie_vp


def simular_retiro_ppr_indexado(
    capital_inicial,
    tasa_anual,
    inflacion_anual,
    udi_inicial,
    meses,
    retiro_mensual_inicial,
):
    """
    Simula retiro REAL (indexado), PPR:
    - Retiro inicial crece 1 vez por año a inflación
    - Comisiones iguales al simulador nominal
    """
    tasa_mensual = (1 + tasa_anual) ** (1/12) - 1
    saldo = capital_inicial
    udi_actual = udi_inicial

    retiro_actual = retiro_mensual_inicial

    saldos = []
    mensualidades = []
    mes_agotado = None

    for mes in range(1, meses + 1):

        # Rendimiento
        interes = saldo * tasa_mensual

        # Comisión fija 15 UDIS + IVA
        cargo_fijo = 15 * udi_actual * (1 + inflacion_anual) * 1.16

        # Nuevo saldo preliminar
        base = saldo + interes - cargo_fijo - retiro_actual

        # Cargo gestión (0.1% + IVA)
        cargo_gestion = base * 0.001 * 1.16
        saldo = base - cargo_gestion

        if saldo < 0:
            saldo = 0.0

        saldos.append(saldo)
        mensualidades.append(retiro_actual)

        # Actualizar cada año
        if mes % 12 == 0:
            udi_actual *= (1 + inflacion_anual)
            retiro_actual *= (1 + inflacion_anual)

        # detectar agotamiento
        if saldo <= 0 and mes_agotado is None:
            mes_agotado = mes

    if mes_agotado is None:
        mes_agotado = meses

    return saldos, mensualidades, mes_agotado

def simular_retiro_simple_indexado(
    capital_inicial,
    tasa_anual,
    inflacion_anual,
    meses,
    retiro_mensual_inicial,
):
    tasa_mensual = (1 + tasa_anual) ** (1/12) - 1
    saldo = capital_inicial
    retiro_actual = retiro_mensual_inicial

    saldos = []
    mensualidades = []
    mes_agotado = None

    for mes in range(1, meses + 1):

        saldo = saldo * (1 + tasa_mensual) - retiro_actual
        if saldo < 0:
            saldo = 0.0

        saldos.append(saldo)
        mensualidades.append(retiro_actual)

        if mes % 12 == 0:
            retiro_actual *= (1 + inflacion_anual)

        if saldo <= 0 and mes_agotado is None:
            mes_agotado = mes

    if mes_agotado is None:
        mes_agotado = meses

    return saldos, mensualidades, mes_agotado

def buscar_retiro_optimo_indexado(
    capital_inicial,
    meses,
    inflacion_anual,
    tasa_anual,
    udi_inicial,
    cetes=False
):
    """
    Encuentra el retiro mensual inicial máximo (indexado)
    que agota el capital en el último mes.

    Si cetes=True usa simular_retiro_simple_indexado
    Si cetes=False usa simular_retiro_ppr_indexado
    """

    # Elegir simulador correcto
    if cetes:
        simulador = lambda cap, months, r: simular_retiro_simple_indexado(
            capital_inicial=cap,
            tasa_anual=tasa_anual,
            inflacion_anual=inflacion_anual,
            meses=months,
            retiro_mensual_inicial=r
        )
    else:
        simulador = lambda cap, months, r: simular_retiro_ppr_indexado(
            capital_inicial=cap,
            tasa_anual=tasa_anual,
            inflacion_anual=inflacion_anual,
            udi_inicial=udi_inicial,
            meses=months,
            retiro_mensual_inicial=r
        )

    # búsqueda binaria
    low = 0.0
    high = capital_inicial / meses * 2

    mejor_r = 0
    mejor_saldos = None
    mejor_mens = None
    mejor_mes = None

    for _ in range(40):
        mid = (low + high) / 2
        saldos, mensualidades, mes_agotado = simulador(
            capital_inicial,
            meses,
            mid
        )

        saldo_final = saldos[-1]

        mejor_r = mid
        mejor_saldos = saldos
        mejor_mens = mensualidades
        mejor_mes = mes_agotado

        if saldo_final > 0:
            low = mid
        else:
            high = mid

    return mejor_r, mejor_saldos, mejor_mens, mejor_mes


def tabla_retiro_completa(
    saldos_ppr_vf,
    saldos_cet_vf,
    mensualidades_ppr=None,
    mensualidades_cet=None,
    inflacion_anual=0.0,
    plazo=0,
    indexado=False
):
    """
    Construye la tabla completa para el retiro NOMINAL o INDEXADO:
    - Recibe saldos finales PPR y CETES (series mensuales)
    - Recibe mensualidades (solo en INDEXADO)
    - Calcula VP para ambas curvas
    """

    # -----------------------------
    # Valor Presente
    # -----------------------------
    saldos_ppr_vp = serie_vp(saldos_ppr_vf, inflacion_anual, plazo)
    saldos_cet_vp = serie_vp(saldos_cet_vf, inflacion_anual, plazo)

    # -----------------------------
    # Mensualidades
    # -----------------------------
    if not indexado:
        # NOMINAL → retiro fijo
        mensualidades_ppr = [mensualidades_ppr] * len(saldos_ppr_vf)
        mensualidades_cet = [mensualidades_cet] * len(saldos_cet_vf)
    else:
        # INDEXADO → listas completas
        pass

    # -----------------------------
    # Total gastado
    # -----------------------------
    total_ppr = pd.Series(mensualidades_ppr).cumsum()
    total_cet = pd.Series(mensualidades_cet).cumsum()

    # -----------------------------
    # Tabla
    # -----------------------------
    df = pd.DataFrame({
        "Mes": list(range(1, len(saldos_ppr_vf)+1)),
        "Saldo PPR VF": saldos_ppr_vf,
        "Saldo PPR VP": saldos_ppr_vp,
        "Retiro PPR": mensualidades_ppr,
        "Total gastado PPR": total_ppr,
        "Saldo CETES VF": saldos_cet_vf,
        "Saldo CETES VP": saldos_cet_vp,
        "Retiro CETES": mensualidades_cet,
        "Total gastado CETES": total_cet,
    })

    return df
