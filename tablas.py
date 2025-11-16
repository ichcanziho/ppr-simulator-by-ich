import pandas as pd

def generar_aportes(aporte_inicial, meses, inflacion_anual, incrementar):
    aportes = []
    aporte = aporte_inicial
    for m in range(meses):
        aportes.append(aporte)
        if incrementar and (m > 0) and (m % 12 == 0):
            aporte *= (1 + inflacion_anual)
    return aportes

def simular_saldo_inicial_excel(
    aporte_inicial,
    meses_totales=25*12,
    meses_aportando=18,
    tasa_anual=0.10,
    cargo_fijo_inicial=-500,
    incrementar=False,
    inflacion_anual=0.0499
):
    """
    Simula el SALDO INICIAL exactamente como el Excel:
    - Recibe aportaciones SOLO por 18 meses
    - Sigue creciendo por 300 meses (rendimiento + cargos)
    """

    tasa_mensual = round((1 + tasa_anual) ** (1 / 12) - 1, 3)

    saldo = 0
    aporte = aporte_inicial

    rows = []

    for mes in range(1, meses_totales + 1):

        # Ajuste por inflación (si el usuario activa incrementar)
        if incrementar and mes > 1 and (mes - 1) % 12 == 0 and mes <= meses_aportando:
            aporte = round(aporte * (1 + inflacion_anual), 0)

        saldo_anterior = saldo

        # SOLO hay aportación los primeros 18 meses
        if mes <= meses_aportando:
            aportacion = aporte
        else:
            aportacion = 0

        # Cargo fijo SOLO el mes 1
        cargo_fijo = cargo_fijo_inicial if mes == 1 else 0

        # === INTERÉS ===
        base_interes = saldo_anterior + aportacion
        interes = round(base_interes * tasa_mensual, 0)

        # === CARGO ADMINISTRATIVO (trimestral) ===
        if mes % 3 == 0:
            cargo_admin = - round(base_interes * 0.009 * 1.16, 0)
        else:
            cargo_admin = 0

        # === CARGO GESTIÓN (mensual) ===
        base_gestion = saldo_anterior + aportacion + interes + cargo_fijo
        cargo_gestion = - round(base_gestion * 0.001 * 1.16, 0)

        # === SALDO FINAL ===
        saldo = base_gestion + cargo_admin + cargo_gestion

        rows.append({
            "Mes": mes,
            "Saldo Anterior": saldo_anterior,
            "Aportación": aportacion,
            "Interés": interes,
            "Cargo Fijo": cargo_fijo,
            "Cargo Administrativo": cargo_admin,
            "Cargo Gestión Inversión": cargo_gestion,
            "Saldo Final": saldo
        })

    return pd.DataFrame(rows)

def simular_saldo_comprometido_excel(
    aportes_lista,
    sat_inyectado_lista,
    inflacion,
    udi_inicial,
    tasa_anual,
    meses=25*12,
    offset=18
):
    """
    Simulación real del saldo comprometido Allianz,
    ahora incluyendo aportaciones SAT dentro del PPR.
    """

    tasa_mensual = round((1 + tasa_anual)**(1/12) - 1, 3)

    udi_actual = udi_inicial
    saldo = 0
    rows = []

    for mes in range(1, meses + 1):

        # ------------------------------------
        # 0) Meses sin aportación (igual al Excel)
        # ------------------------------------
        if mes <= offset:
            rows.append({
                "Mes": mes,
                "Saldo Anterior": 0,
                "Aportación": 0,
                "Aporte SAT": 0,
                "Aportación Total": 0,
                "Interés": 0,
                "Cargo Fijo": 0,
                "Cargo Administrativo": 0,
                "Cargo Gestión Inversión": 0,
                "Saldo Final": 0,
            })

            # Actualizar UDI una vez por año
            if mes % 12 == 0:
                udi_actual *= (1 + inflacion)
            continue

        # ------------------------------------
        # 1) Aportaciones normales + SAT
        # ------------------------------------
        idx = mes - 1

        aporte_normal = aportes_lista[idx]
        aporte_sat = sat_inyectado_lista[idx]  # 0 la mayoría de meses
        aporte_total = aporte_normal + aporte_sat

        # ------------------------------------
        # 2) Interés
        # ------------------------------------
        saldo_anterior = saldo
        base_interes = saldo_anterior + aporte_total
        interes = round(base_interes * tasa_mensual, 0)

        # ------------------------------------
        # 3) Cargo fijo de 15 UDIs (igual a Excel)
        # ------------------------------------
        cargo_fijo = - round(15 * udi_actual * (1 + inflacion) * 1.16, 0)

        # ------------------------------------
        # 4) Cargo administrativo (si lo quieres activar)
        # ------------------------------------
        cargo_admin = 0  # tu Excel lo tiene en 0

        # ------------------------------------
        # 5) Cargo por gestión (0.1% mensual * IVA)
        # ------------------------------------
        base_gestion = saldo_anterior + aporte_total + interes + cargo_fijo
        cargo_gestion = - round(base_gestion * 0.001 * 1.16, 0)

        # ------------------------------------
        # 6) Saldo final
        # ------------------------------------
        saldo = base_gestion + cargo_admin + cargo_gestion

        rows.append({
            "Mes": mes,
            "Saldo Anterior": saldo_anterior,
            "Aportación": aporte_normal,
            "Aporte SAT": aporte_sat,
            "Aportación Total": aporte_total,
            "Interés": interes,
            "Cargo Fijo": cargo_fijo,
            "Cargo Administrativo": cargo_admin,
            "Cargo Gestión Inversión": cargo_gestion,
            "Saldo Final": saldo,
        })

        # ------------------------------------
        # 7) Actualización anual de UDI
        # ------------------------------------
        if mes % 12 == 0:
            udi_actual *= (1 + inflacion)

    return pd.DataFrame(rows)


def simular_bono_excel(
        aporte_mensual,
        plazo_anios,
        tasa_anual_bono=0.09
):
    """
    Simula la tabla del BONO exactamente como el Excel de Allianz.
    """

    # 1) Calcular porcentaje del bono según tabla oficial
    from allianz_functions import obtener_bono_fidelidad_porcentaje

    porcentaje_bono = obtener_bono_fidelidad_porcentaje(aporte_mensual, plazo_anios)

    # 2) Bono mensual (SIEMPRE ES CONSTANTE)
    bono_mensual = round(aporte_mensual * porcentaje_bono, 0)

    # 3) Tasa mensual exacta
    tasa_mensual = round((1 + tasa_anual_bono) ** (1 / 12) - 1, 4)

    saldo = 0
    rows = []

    meses = plazo_anios * 12

    for mes in range(1, meses + 1):

        saldo_anterior = saldo

        # === INTERÉS ===
        base_interes = saldo_anterior + bono_mensual
        interes = round(base_interes * tasa_mensual, 0)
        # print(mes, base_interes, tasa_mensual, interes)

        # === CARGO ADMIN CADA 3 MESES ===
        if mes % 3 == 0:
            cargo_admin = - round((saldo_anterior + bono_mensual + interes) * 0.009, 0)
        else:
            cargo_admin = 0

        if mes > 12:
            bono_mensual = 0

        # === CARGO DE GESTIÓN (MENSUAL) ===
        cargo_gestion = - round((saldo_anterior + bono_mensual + interes) * 0.001, 0)

        # === SALDO FINAL ===
        saldo = saldo_anterior + bono_mensual + interes + cargo_admin + cargo_gestion

        rows.append({
            "Mes": mes,
            "Saldo Anterior": saldo_anterior,
            "Bono Mensual": bono_mensual,
            "Interés": interes,
            "Cargo Administrativo": cargo_admin,
            "Cargo Gestión Inversión": cargo_gestion,
            "Saldo Final": saldo,
        })

    return pd.DataFrame(rows)


# # --- Generate aportes ---
# aportes_lista = generar_aportes(5000, 25*12, 0.0499, True)
#
# # --- Run simulations ---
# df_inicial = simular_saldo_inicial_excel(
#     aporte_inicial=5000,
#     meses_totales=12*25,
#     meses_aportando=18,
#     tasa_anual=0.10,
#     cargo_fijo_inicial=-500,
#     incrementar=True,
#     inflacion_anual=0.0499
# )
#
# df_comp = simular_saldo_comprometido_excel(
#     aportes_lista,
#     inflacion=0.05,
#     udi_inicial=6.84,
#     tasa_anual=0.10,
#     meses=25*12,
#     offset=18
# )
#
# df_bono = simular_bono_excel(
#         aporte_mensual=5000,
#         plazo_anios=25,
#         tasa_anual_bono=0.09
# )
#
# # --- Save ---
# df_inicial.to_csv("simulacion_saldo_inicial.csv", index=False)
# df_comp.to_csv("simulacion_saldo_comprometido.csv", index=False)
# df_bono.to_csv("simulacion_bono.csv", index=False)
#
# print(df_inicial.head())
#
# print(df_comp.head())
#
# print(df_bono.head())
