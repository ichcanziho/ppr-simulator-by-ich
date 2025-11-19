import streamlit as st
import plotly.graph_objects as go
import numpy as np
import pandas as pd

# Importamos las tablas reales
from tablas import (
    generar_aportes,
    simular_saldo_inicial_excel,
    simular_saldo_comprometido_excel,
    simular_bono_excel
)

from allianz_functions import (
    calcular_bono_fidelidad,
    simular_retiro_simple,
    simular_retiro_ppr,
    buscar_retiro_optimo,
    serie_vp,
    generar_aportes_con_offset,
    generar_aportes_early_stop
)

from allianz_functions_indexadas import (
    simular_retiro_ppr_indexado,
    simular_retiro_simple_indexado,
    buscar_retiro_optimo_indexado,
    tabla_retiro_completa
)

st.set_page_config(page_title="Simulador Allianz", layout="wide")
st.title("📘 Simulador Allianz — Versión Real 100% Excel")

# ================================================================
#                    📌 TABS
# ================================================================
tab1, tab2, tab3 = st.tabs([
    "1️⃣ Inputs + Acumulación",
    "2️⃣ Simulación de Retiro",
    "3️⃣ Tablas reales mes a mes"
])


# ================================================================
#                        TAB 1 — INPUTS + GRÁFICA
# ================================================================
with tab1:
    st.header("📥 Datos del simulador Allianz")

    # ----------------------- DATOS GENERALES -----------------------
    col1, col2 = st.columns(2)

    with col1:
        nombre = st.text_input("Nombre", "Gabriel")

    with col2:
        edad = st.number_input("Edad", min_value=18, max_value=80, value=28)

    # ----------------------- APORTACIONES -----------------------
    st.markdown("### Aportaciones")
    colA, colB = st.columns(2)

    with colA:
        aportacion = st.number_input("Aportación mensual", 0, 1_000_000, 5000, step=500)
        plazo_comprometido = st.number_input("Plazo (años)", 1, 60, 25)

    with colB:
        incremento_inflacion = st.selectbox("Aumentar con inflación cada año", ["Sí", "No"])

    st.markdown("### ⏹️ Early Stop (Opcional)")

    usar_early_stop = st.checkbox("Detener aportaciones después de cierto año", value=False)

    if usar_early_stop:
        años_aportando = st.number_input(
            "¿Cuántos años vas a aportar realmente?",
            min_value=1,
            max_value=plazo_comprometido,
            value=10
        )
    else:
        años_aportando = plazo_comprometido

    # ================================================================
    #     🚀 Estrategia optimizada (cambiar aportes desde mes 19)
    # ================================================================
    st.markdown("### 🧠 Estrategia Inteligente (Opcional)")

    modo_estrategia = st.checkbox(
        "Activar estrategia optimizada (aportes reducidos primeros 18 meses)",
        value=False
    )

    if modo_estrategia:
        colX, colY = st.columns(2)

        with colX:
            aporte_temporal = st.number_input(
                "Aportación SOLO durante los primeros 18 meses",
                min_value=0,
                max_value=aportacion,
                value=2000,
                step=500
            )

        with colY:
            offset_manual = st.number_input(
                "Depósito único adicional en el mes 19 (manual)",
                min_value=0,
                max_value=10_000_000,
                value=0,
                step=1000
            )

        # Calculamos automáticamente cuánto dejaste de meter
        offset_auto = (aportacion - aporte_temporal) * 18

    else:
        aporte_temporal = aportacion
        offset_manual = 0
        offset_auto = 0

    # ----------------------- RENDIMIENTO & INFLA -----------------------
    st.markdown("### Parámetros Económicos")
    colE, colF = st.columns(2)

    with colE:
        rendimiento_anual = st.number_input("Rendimiento anual (%)", 0.0, 20.0, 10.0) / 100

    with colF:
        inflacion_anual = st.number_input("Inflación anual (%)", 0.0, 20.0, 4.99) / 100

    # ----------------------- UDI y UMA -----------------------
    st.markdown("### Valores Bases (UDIs y UMA)")

    colU, colM = st.columns(2)

    with colU:
        udi_inicial = st.number_input(
            "Valor de la UDI actual",
            min_value=4.0, max_value=20.0,
            value=6.84, step=0.01
        )

    with colM:
        uma_inicial = st.number_input(
            "Valor UMA diario",
            min_value=50.0, max_value=500.0,
            value=108.57, step=0.1
        )

    # ----------------------- FISCAL (SAT) -----------------------
    st.markdown("### Parámetros fiscales (SAT)")

    colG, colH = st.columns(2)
    with colG:
        salario_anual = st.number_input(
            "Salario anual (antes de impuestos)",
            min_value=0,
            max_value=10_000_000,
            value=600_000,
            step=50_000
        )
    with colH:
        tasa_marginal_isr = st.number_input(
            "Tasa marginal de ISR (%)",
            min_value=0.0,
            max_value=50.0,
            value=32.0
        ) / 100

    reinvertir_sat = st.checkbox("Reinvertir devolución del SAT", value=True)

    # ----------------------- BONO -----------------------
    st.subheader("🎁 Bono de Fidelidad Allianz")
    usar_bono = st.checkbox("Usar Bono de Fidelidad", value=True)

    porcentaje_bono, bono = calcular_bono_fidelidad(
        aporte_mensual=aportacion if usar_bono else 0,
        plazo=plazo_comprometido,
        usar_bono=usar_bono
    )

    col1, col2 = st.columns(2)
    col1.metric("% Bono", f"{porcentaje_bono * 100:.0f}%")
    col2.metric("Bono Mensual", f"${bono:,.0f}")

    # ================================================================
    # RUN SIMULACIONES REALES
    # ================================================================
    meses = plazo_comprometido * 12

    # ================================================================
    # GENERACIÓN REAL DE APORTES — CON O SIN ESTRATEGIA
    # ================================================================

    aportes = []

    if modo_estrategia:
        # estrategia + early stop
        aportes = generar_aportes_con_offset(
            aporte_inicial=aporte_temporal,
            meses=meses,
            inflacion_anual=inflacion_anual,
            incrementar=(incremento_inflacion == "Sí"),
            offset=18,
            nuevo_aporte=aportacion
        )

        aportes[18] += offset_manual

    else:
        # aquí detectamos early stop
        aportes = generar_aportes_early_stop(
            aporte_inicial=aportacion,
            meses=meses,
            inflacion_anual=inflacion_anual,
            incrementar=(incremento_inflacion == "Sí"),
            meses_aportando=años_aportando * 12
        )
    print("#"*100)
    print("aportes ")
    print(aportes[0:30])
    print("#"*100)
    # 2) SALDO INICIAL (todo el plazo, aportando solo 18 meses)
    ap_inicial_real = aportes[0]  # primera mensualidad REAL

    df_inicial = simular_saldo_inicial_excel(
        aporte_inicial=ap_inicial_real,
        meses_totales=meses,
        meses_aportando=18,
        tasa_anual=rendimiento_anual,
        cargo_fijo_inicial=-500,
        incrementar=(incremento_inflacion == "Sí"),
        inflacion_anual=inflacion_anual
    )

    # 3) SAT: DEVOLUCIÓN ANUAL (REGLAS REALES) Y SERIE MENSUAL
    # ======================================================
    # 3.1) Aportes por año (con inflación)
    aportes_por_anio = []
    for year in range(plazo_comprometido):
        inicio = year * 12
        fin = min((year + 1) * 12, len(aportes))
        aportes_por_anio.append(sum(aportes[inicio:fin]))

    # 3.2) Salario que crece con la inflación
    salarios_por_anio = []
    salario_actual = salario_anual
    for _ in range(plazo_comprometido):
        salarios_por_anio.append(salario_actual)
        salario_actual *= (1 + inflacion_anual)

    # 3.3) SAT devuelto por año
    sat_por_anio = []
    for year, a_anual in enumerate(aportes_por_anio):
        salario_base_anual = salarios_por_anio[year]
        UMA = uma_inicial  # input editable

        # Límite 1: 10% del salario anual
        limite_salario = salario_base_anual * 0.10

        # Límite 2: 5 UMA * 365 días
        limite_uma = UMA * 365 * 5

        # Límite 3: tus aportes del año
        limite_aporte = a_anual

        deducible = min(limite_aporte, limite_salario, limite_uma)
        sat_anual = deducible * tasa_marginal_isr
        sat_por_anio.append(sat_anual)

    # 3.4) Serie mensual de inyecciones SAT (mes 13, 25, 37, ...)
    sat_inyectado = [0.0] * meses
    for year, sat in enumerate(sat_por_anio):
        mes_inyeccion = year * 12 + 13  # 13, 25, 37, ...
        if 1 <= mes_inyeccion <= meses:
            sat_inyectado[mes_inyeccion - 1] = sat

    # ================================================================
    # 4) SALDO COMPROMETIDO SIN SAT y CON SAT DENTRO DEL PPR
    # ================================================================
    # Lista de ceros para la simulación "sin SAT"
    sat_ceros = [0.0] * meses

    # 4.1) Allianz "real" SIN SAT (solo tus aportes normales)
    df_comp_sin_sat = simular_saldo_comprometido_excel(
        aportes_lista=aportes,
        sat_inyectado_lista=sat_ceros,
        inflacion=inflacion_anual,
        udi_inicial=udi_inicial,
        tasa_anual=rendimiento_anual,
        meses=meses,
        offset=18
    )

    # 4.2) Allianz CON SAT dentro del mismo PPR
    df_comp_con_sat = simular_saldo_comprometido_excel(
        aportes_lista=aportes,
        sat_inyectado_lista=sat_inyectado,
        inflacion=inflacion_anual,
        udi_inicial=udi_inicial,
        tasa_anual=rendimiento_anual,
        meses=meses,
        offset=18
    )

    # 5) BONO DE FIDELIDAD REAL
    df_bono = simular_bono_excel(
        aporte_mensual=aportacion if usar_bono else 0,
        plazo_anios=plazo_comprometido,
        tasa_anual_bono=0.09
    )

    # 6) TABLA TOTAL (sin SAT y con SAT)
    df_total = pd.DataFrame({
        "Mes": np.arange(1, meses + 1),
        "Inicial": df_inicial["Saldo Final"].tolist(),
        "Comprometido_sin_SAT": df_comp_sin_sat["Saldo Final"].tolist(),
        "Comprometido_con_SAT": df_comp_con_sat["Saldo Final"].tolist(),
        "Bono": df_bono["Saldo Final"].tolist(),
        "SAT_inyectado": sat_inyectado,
    })

    # SAT acumulado aportado (solo la suma de depósitos)
    df_total["SAT_Acumulado"] = np.cumsum(df_total["SAT_inyectado"])

    # 7) TOTALES ALLIANZ
    df_total["Total Allianz sin SAT"] = (
            df_total["Inicial"] + df_total["Comprometido_sin_SAT"] + df_total["Bono"]
    )

    df_total["Allianz + SAT"] = (
            df_total["Inicial"] + df_total["Comprometido_con_SAT"] + df_total["Bono"]
    )

    saldo_allianz_sin_sat = df_total["Total Allianz sin SAT"].iloc[-1]
    saldo_allianz_con_sat = df_total["Allianz + SAT"].iloc[-1]

    sat_total_aportado = df_total["SAT_Acumulado"].iloc[-1]
    sat_valor_actual = saldo_allianz_con_sat - saldo_allianz_sin_sat

    # ----------------------- BENCHMARK (ETF y Colchón) -----------------------
    r_m = (1 + rendimiento_anual) ** (1 / 12) - 1

    saldo_benchmark = []
    s = 0
    for a in aportes:
        s += a
        s *= (1 + r_m)
        saldo_benchmark.append(s)

    colchon = np.cumsum(aportes)

    # ================================================================
    # COMPARATIVA FINAL
    # ================================================================
    total_aportado = sum(aportes)
    etf_bruto = saldo_benchmark[-1]

    ganancia = etf_bruto - total_aportado
    impuesto = ganancia * 0.10  # ISR 10%
    etf_neto = etf_bruto - impuesto
    saldo_etf_neto = etf_neto

    rend_allianz = saldo_allianz_con_sat

    if rend_allianz >= etf_neto:
        faltante = 0
        excedente = rend_allianz - etf_neto
    else:
        excedente = 0
        faltante = etf_neto - rend_allianz

    diferencia_final = rend_allianz - etf_neto

    st.markdown("---")
    st.header("💰 Comparación de aportaciones y rendimientos")

    total_aportado = sum(aportes)
    rendimiento_etf = saldo_benchmark[-1]

    colA, colB, colC, colD = st.columns(4)

    colA.metric("Total aportado por ti", f"${total_aportado:,.2f}")
    colB.metric("Saldo ETF ideal", f"${rendimiento_etf:,.2f}")
    colC.metric("Allianz real (sin SAT)", f"${saldo_allianz_sin_sat:,.2f}")
    colD.metric("Allianz + SAT reinvertido", f"${saldo_allianz_con_sat:,.2f}")

    colE, colE2, colF, colF2 = st.columns(4)
    colE.metric("SAT recibido total (aportado)", f"${sat_total_aportado:,.2f}")

    colE2.metric("Saldo ETF Neto (libre)", f"${etf_neto:,.2f}")

    colF.metric("Valor actual del SAT reinvertido", f"${sat_valor_actual:,.2f}")

    colF2.metric("Diferencia entre Allianz Sat y ETF NETO", f"${diferencia_final:,.2f}")




    # ================================================================
    # GRÁFICA 1 — EVOLUCIÓN EN EL TIEMPO
    # ================================================================
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_total["Mes"], y=colchon,
        name="Colchón", line=dict(color="gray", dash="dash")
    ))

    fig.add_trace(go.Scatter(
        x=df_total["Mes"], y=saldo_benchmark,
        name="ETF ideal", line=dict(color="green")
    ))

    fig.add_trace(go.Scatter(
        x=df_total["Mes"], y=df_total["Total Allianz sin SAT"],
        name="Allianz Real (sin SAT)", line=dict(color="red", width=3)
    ))

    fig.add_trace(go.Scatter(
        x=df_total["Mes"], y=df_total["Allianz + SAT"],
        name="Allianz + SAT reinvertido",
        line=dict(color="orange", width=3, dash="dot")
    ))

    fig.update_layout(
        title="Comparación: Colchón vs ETF ideal vs Allianz Real (+SAT)",
        xaxis_title="Mes",
        yaxis_title="Saldo",
        height=480
    )

    # ================================================================
    # GRÁFICA 2 — BARRA APILADA ETF vs Allianz + SAT
    # ================================================================
    st.markdown("---")
    st.header("📊 ETF ideal vs Allianz + SAT — Rendimiento Comparado")

    rendimiento_allianz_sat = saldo_allianz_con_sat
    dif_etf_allianz = rendimiento_etf - rendimiento_allianz_sat

    #if rendimiento_allianz_sat >= rendimiento_etf:
    fig3 = go.Figure()

    fig3.add_trace(go.Bar(
        name='Allianz sin SAT',
        x=['Comparación Final'],
        y=[saldo_allianz_sin_sat],
        marker_color='blue'
    ))

    fig3.add_trace(go.Bar(
        name='SAT reinvertido',
        x=['Comparación Final'],
        y=[sat_valor_actual],
        marker_color='gray'
    ))

    if faltante > 0:
        fig3.add_trace(go.Bar(
            name='Faltante vs ETF Neto',
            x=['Comparación Final'],
            y=[faltante],
            marker_color='red'
        ))
    else:
        fig3.add_trace(go.Bar(
            name='Excedente sobre ETF Neto',
            x=['Comparación Final'],
            y=[excedente],
            marker_color='green'
        ))

    fig3.update_layout(
        barmode='stack',
        title='Allianz vs SAT vs Faltante/Excedente frente a ETF Neto',
        yaxis_title='Pesos'
    )

    # --------- MOSTRAR LAS DOS GRÁFICAS LADO A LADO ----------
    col_g1, col_g2 = st.columns(2)
    col_g1.plotly_chart(fig, use_container_width=True)
    col_g2.plotly_chart(fig3, use_container_width=True)


# ================================================================
#                        TAB 2 — RETIRO
# ================================================================
with tab2:
    st.header("🧓 Simulación completa del retiro")

    # ------------ Inputs del escenario de retiro ------------
    años_retiro = st.number_input(
        "Años estimados de retiro",
        min_value=5, max_value=50, value=20
    )
    meses_retiro = años_retiro * 12

    tasa_cetes_anual = st.number_input(
        "Tasa anual alternativa (CETES / renta fija fuera del PPR) (%)",
        min_value=0.0, max_value=20.0, value=7.5
    ) / 100

    st.markdown(
        "Usaremos como capital base el **Allianz + SAT reinvertido** "
        "para comparar dos caminos:"
        "\n\n1. Dejar el dinero **dentro del PPR**.\n"
        "2. Sacar todo y meterlo a **CETES / renta fija** con la tasa indicada."
    )

    capital_base = saldo_allianz_con_sat  # VF al final de la etapa laboral

    # ===============================================================
    #                     SECCIÓN EN DOS COLUMNAS
    # ===============================================================
    col_nom, col_ind = st.columns(2)

    # ===============================================================
    #                        ⬅️ NOMINAL
    # ===============================================================

    factor_descuento = (1 + inflacion_anual) ** plazo_comprometido

    def vp(vf):
        return vf / factor_descuento


    with col_nom:
        st.subheader("📉 Simulación NOMINAL — Retiro fijo")

        # buscar retiro óptimo (NOMINAL)
        ret_nom_ppr, saldos_nom_ppr_vf, mes_nom_ppr = buscar_retiro_optimo(
            capital_inicial=capital_base,
            meses=meses_retiro,
            simulador=lambda cap, m, r: simular_retiro_ppr(
                capital_inicial=cap,
                tasa_anual=rendimiento_anual,
                inflacion_anual=inflacion_anual,
                udi_inicial=udi_inicial,
                meses=m,
                retiro_mensual=r,
            )
        )

        ret_nom_cet, saldos_nom_cet_vf, mes_nom_cet = buscar_retiro_optimo(
            capital_inicial=capital_base,
            meses=meses_retiro,
            simulador=lambda cap, m, r: simular_retiro_simple(
                capital_inicial=cap,
                tasa_anual=tasa_cetes_anual,
                meses=m,
                retiro_mensual=r,
            )
        )

        # Convertir ambas curvas a VP
        saldos_nom_ppr_vp = serie_vp(saldos_nom_ppr_vf, inflacion_anual, plazo_comprometido)
        saldos_nom_cet_vp = serie_vp(saldos_nom_cet_vf, inflacion_anual, plazo_comprometido)

        st.markdown("### 🔴 PPR (Nominal)")
        st.metric("Pensión inicial (VP)", f"${vp(ret_nom_ppr):,.2f}")
        st.metric("Años de duración", f"{mes_nom_ppr/12:.2f}")

        st.markdown("### 🔵 CETES (Nominal)")
        st.metric("Pensión inicial (VP)", f"${vp(ret_nom_cet):,.2f}")
        st.metric("Años de duración", f"{mes_nom_cet/12:.2f}")

        # Gráfica NOMINAL en VP
        fig_nom = go.Figure()
        fig_nom.add_trace(go.Scatter(
            x=list(range(1, meses_retiro+1)),
            y=saldos_nom_ppr_vp,
            name="PPR nominal (VP)",
            line=dict(color="purple")
        ))
        fig_nom.add_trace(go.Scatter(
            x=list(range(1, meses_retiro+1)),
            y=saldos_nom_cet_vp,
            name="CETES nominal (VP)",
            line=dict(color="teal")
        ))
        fig_nom.update_layout(
            title="Evolución NOMINAL del saldo (VP)",
            xaxis_title="Mes",
            yaxis_title="Saldo (VP)",
            height=380
        )
        st.plotly_chart(fig_nom, use_container_width=True)

        # Tabla NOMINAL VP
        df_nom = tabla_retiro_completa(
            saldos_ppr_vf=saldos_nom_ppr_vf,
            saldos_cet_vf=saldos_nom_cet_vf,
            mensualidades_ppr=ret_nom_ppr,
            mensualidades_cet=ret_nom_cet,
            inflacion_anual=inflacion_anual,
            plazo=plazo_comprometido,
            indexado=False
        )

        st.subheader("📄 Tabla NOMINAL (VP)")
        st.dataframe(df_nom, use_container_width=True)

    # ===============================================================
    #                        ➡️ INDEXADO
    # ===============================================================
    with col_ind:
        st.subheader("📈 Simulación INDEXADA — Retiro que sube con inflación")

        # buscar retiro óptimo (INDEXADO)
        ret_ind_ppr, saldos_ind_ppr_vf, mensualidades_ppr, tot_ppr = buscar_retiro_optimo_indexado(
            capital_inicial=capital_base,
            meses=meses_retiro,
            inflacion_anual=inflacion_anual,
            tasa_anual=rendimiento_anual,
            udi_inicial=udi_inicial,
        )

        ret_ind_cet, saldos_ind_cet_vf, mensualidades_cet, tot_cet = buscar_retiro_optimo_indexado(
            capital_inicial=capital_base,
            meses=meses_retiro,
            inflacion_anual=inflacion_anual,
            tasa_anual=tasa_cetes_anual,
            udi_inicial=udi_inicial,  # no se usa en CETES, pero no pasa nada
            cetes=True
        )

        saldos_ind_ppr_vp = serie_vp(saldos_ind_ppr_vf, inflacion_anual, plazo_comprometido)
        saldos_ind_cet_vp = serie_vp(saldos_ind_cet_vf, inflacion_anual, plazo_comprometido)

        st.markdown("### 🔴 PPR (Indexado)")
        st.metric("Pensión inicial (VP)", f"${vp(ret_ind_ppr):,.2f}")
        st.metric("Años de duración", "20.00")

        st.markdown("### 🔵 CETES (Indexado)")
        st.metric("Pensión inicial (VP)", f"${vp(ret_ind_cet):,.2f}")
        st.metric("Años de duración", "20.00")

        # Gráfica INDEXADA VP
        fig_ind = go.Figure()
        fig_ind.add_trace(go.Scatter(
            x=list(range(1, meses_retiro+1)),
            y=saldos_ind_ppr_vp,
            name="PPR indexado (VP)",
            line=dict(color="purple")
        ))
        fig_ind.add_trace(go.Scatter(
            x=list(range(1, meses_retiro+1)),
            y=saldos_ind_cet_vp,
            name="CETES indexado (VP)",
            line=dict(color="teal")
        ))
        fig_ind.update_layout(
            title="Evolución INDEXADA del saldo (VP)",
            xaxis_title="Mes",
            yaxis_title="Saldo (VP)",
            height=380
        )
        st.plotly_chart(fig_ind, use_container_width=True)

        df_ind = tabla_retiro_completa(
            saldos_ppr_vf=saldos_ind_ppr_vf,
            saldos_cet_vf=saldos_ind_cet_vf,
            mensualidades_ppr=mensualidades_ppr,
            mensualidades_cet=mensualidades_cet,
            inflacion_anual=inflacion_anual,
            plazo=plazo_comprometido,
            indexado=True
        )
        st.subheader("📄 Tabla INDEXADA (VP)")
        st.dataframe(df_ind, use_container_width=True)

# ================================================================
#                     TAB 3 — TABLAS COMPLETAS
# ================================================================

with tab3:
    st.header("📑 Tablas reales tal cual Excel")

    st.subheader("📄 Saldo Inicial (0–18 meses, pero simulado todo el plazo)")
    st.dataframe(df_inicial, use_container_width=True)

    st.subheader("📄 Saldo Comprometido (19 → final) — SIN SAT")
    st.dataframe(df_comp_sin_sat, use_container_width=True)

    st.subheader("📄 Saldo Comprometido (19 → final) — CON SAT dentro del PPR")
    st.dataframe(df_comp_con_sat, use_container_width=True)

    st.subheader("📄 Bono de Fidelidad")
    st.dataframe(df_bono, use_container_width=True)

    st.subheader("📄 Total Allianz + SAT (vista resumen)")
    st.dataframe(df_total, use_container_width=True)