import streamlit as st
import numpy as np
import pandas as pd
import math
import plotly.graph_objects as go
import plotly.express as px
import altair as alt
import io
import json


# -----------------------
# Funciones financieras
# -----------------------

def export_excel_completo(
    df_acum=None,
    df_resumen=None,
    df_ret=None,
    df_sens=None,
    df_adv=None,
    df_retiro=None,
    params=None
):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:

        if df_acum is not None:
            df_acum.to_excel(writer, sheet_name="Acumulación", index=False)

        if df_resumen is not None:
            df_resumen.to_excel(writer, sheet_name="Valor Presente", index=False)

        if df_ret is not None:
            df_ret.to_excel(writer, sheet_name="Edades Retiro", index=False)

        if df_sens is not None:
            df_sens.to_excel(writer, sheet_name="Sensibilidad", index=False)

        if df_adv is not None:
            df_adv.to_excel(writer, sheet_name="Estrategia Avanzada", index=False)

        if df_retiro is not None:
            df_retiro.to_excel(writer, sheet_name="Retiro Mes a Mes", index=False)

        if params is not None:
            pd.DataFrame(params.items(), columns=["Parámetro", "Valor"]).to_excel(
                writer, sheet_name="Parámetros", index=False
            )

    return buffer.getvalue()


def export_df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")

def export_df_to_excel(df):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Hoja1")
    return buffer.getvalue()

def parametros_actuales_json(
        edad_actual, edad_retiro, edad_final,
        pension_hoy, inflacion, rendimiento,
        aporte_inicial, aportes_crecen
):
    return {
        "edad_actual": edad_actual,
        "edad_retiro": edad_retiro,
        "edad_final": edad_final,
        "pension_hoy": pension_hoy,
        "inflacion": inflacion,
        "rendimiento": rendimiento,
        "aporte_inicial": aporte_inicial,
        "aportes_crecen": aportes_crecen,
    }

def simula_retiro_mes_a_mes(capital_inicial, años_retiro, inflacion_anual, rendimiento_anual, pension_mensual_inicial):
    """
    Simula mes a mes el periodo de retiro:
    - saldo
    - pensión que sube con inflación
    - intereses mensuales
    """

    meses = años_retiro * 12
    infl_m = tasa_mensual(inflacion_anual)
    rend_m = tasa_mensual(rendimiento_anual)

    saldo = capital_inicial
    pension = pension_mensual_inicial

    registros = []

    for m in range(meses):
        saldo_inicial = saldo

        # Retiro del mes
        saldo -= pension

        # Si ya no queda saldo → límite
        if saldo <= 0:
            registros.append((m, saldo_inicial, pension, 0, 0))
            saldo = 0
            break

        # Rendimiento del mes
        interes = saldo * rend_m
        saldo += interes

        registros.append((m, saldo_inicial, pension, interes, saldo))

        # Aumenta la pensión según inflación mensual
        pension *= (1 + infl_m)

    df = pd.DataFrame(registros, columns=[
        "Mes", "Saldo inicial", "Pensión mensual", "Interés ganado", "Saldo final"
    ])

    return df


def aplica_crecimiento_inflacion_back(aportes, inflacion_anual, activar):
    """
    Toma una lista de aportes definidos en pesos de HOY y, si 'activar' es True,
    los ajusta por inflación acumulada mes a mes.
    Es decir: aporte_real[m] = aporte_base[m] * (1 + infl_m)^m
    """
    if not activar:
        return aportes

    infl_m = tasa_mensual(inflacion_anual)
    aportes_ajustados = [
        aporte * ((1 + infl_m) ** i)
        for i, aporte in enumerate(aportes)
    ]
    return aportes_ajustados

def aplica_crecimiento_inflacion(aportes, inflacion_anual, activar):
    if not activar:
        return aportes

    lista = []
    for m, aporte in enumerate(aportes):
        años_transcurridos = m // 12
        aporte_real = aporte * ((1 + inflacion_anual) ** años_transcurridos)
        lista.append(aporte_real)

    return lista

def estrategia_front_loaded(años_a_retiro, aporte_normal, aporte_alto, años_front):
    meses = años_a_retiro * 12
    lista = []
    for m in range(meses):
        if m < años_front * 12:
            lista.append(aporte_alto)
        else:
            lista.append(aporte_normal)
    return lista

def estrategia_back_loaded(años_a_retiro, aporte_bajo, aporte_alto, años_bajo):
    meses = años_a_retiro * 12
    lista = []
    for m in range(meses):
        if m < años_bajo * 12:
            lista.append(aporte_bajo)
        else:
            lista.append(aporte_alto)
    return lista

def estrategia_crecimiento_salarial(años_a_retiro, aporte_inicial, crecimiento_anual, inflacion_anual=None):
    meses = años_a_retiro * 12
    lista = []
    aporte = aporte_inicial
    g_m = tasa_mensual(crecimiento_anual)
    infl_m = tasa_mensual(inflacion_anual) if inflacion_anual else 0

    for m in range(meses):
        lista.append(aporte)
        aporte *= (1 + g_m + infl_m)

    return lista

def simula_aportes_personalizados(aportes, inflacion_anual, rendimiento_anual):
    saldo = 0
    r_m = tasa_mensual(rendimiento_anual)

    registros = []
    for m, aporte in enumerate(aportes):
        saldo += aporte
        saldo *= (1 + r_m)
        registros.append((m, saldo, aporte))

    return saldo, pd.DataFrame(registros, columns=["Mes", "Saldo", "Aporte"])


def calcula_pension_scenario(años_a, años_r, infl, rend, aporte_mensual, aportes_crecen):
    """
    Helper para calcular pensión alcanzable en un escenario dado.
    Regresa: saldo_al_retiro, pension_mensual_nominal, pension_mensual_valor_presente
    """
    if años_a <= 0 or años_r <= 0:
        return None, None, None

    saldo_s, _df_s = simula_acumulacion(años_a, infl, rend, aporte_mensual, aportes_crecen)
    pension_alc_s = pension_alcanzable_desde_capital(saldo_s, años_r, infl, rend)
    vp_alc_s = valor_presente(pension_alc_s, infl, años_a)
    return saldo_s, pension_alc_s, vp_alc_s

def valor_presente(valor_futuro, inflacion_anual, años):
    return valor_futuro / ((1 + inflacion_anual) ** años)

def pension_alcanzable_desde_capital(K, años_retiro, inflacion_anual, rendimiento_anual):
    r = rendimiento_anual
    g = inflacion_anual
    N = años_retiro

    if abs(r - g) < 1e-8:
        P0_anual = K * (r) / N
    else:
        P0_anual = K * (r - g) / (1 - ((1 + g) / (1 + r)) ** N)

    return P0_anual / 12

def tasa_mensual(tasa_anual):
    return (1 + tasa_anual) ** (1 / 12) - 1

def capital_necesario_para_pension(
        pension_mensual_hoy,
        años_a_retiro,
        años_retiro,
        inflacion_anual,
        rendimiento_anual
):
    pension_mensual_retiro = pension_mensual_hoy * (1 + inflacion_anual) ** años_a_retiro
    P0 = pension_mensual_retiro * 12
    g = inflacion_anual
    r = rendimiento_anual
    N = años_retiro

    if abs(r - g) < 1e-8:
        K = P0 * N / (1 + r)
    else:
        K = P0 * (1 - ((1 + g) / (1 + r)) ** N) / (r - g)

    return K, pension_mensual_retiro

def simula_acumulacion(años, inflacion_anual, rendimiento_anual, aporte_inicial, aportes_crecen):
    meses = años * 12
    r_m = tasa_mensual(rendimiento_anual)
    g_m = tasa_mensual(inflacion_anual)

    saldo = 0.0
    aporte = aporte_inicial
    registros = []

    for m in range(meses):
        saldo += aporte
        saldo *= (1 + r_m)

        registros.append((m, saldo, aporte))

        # Solo incrementar aportes una vez por AÑO, no por mes
        if aportes_crecen:
            # si estamos en el primer mes de cada año (m % 12 == 0 y m > 0)
            if m > 0 and m % 12 == 0:
                aporte *= (1 + inflacion_anual)

    df = pd.DataFrame(registros, columns=["Mes", "Saldo", "Aporte"])
    return saldo, df

def simula_acumulacion_allianz(años, inflacion_anual, rendimiento_anual, aporte_inicial, aportes_crecen, precio_actual_udi):
    meses = años * 12
    r_m = tasa_mensual(rendimiento_anual)
    g_m = tasa_mensual(inflacion_anual)

    saldo = 0.0
    aporte = aporte_inicial
    registros = []

    for m in range(meses):
        saldo += aporte
        saldo *= (1 + r_m)
        saldo = saldo - precio_actual_udi * 15  # costo mensual del seguro de vida
        registros.append((m, saldo, aporte))

        # Solo incrementar aportes una vez por AÑO, no por mes
        if aportes_crecen:
            # si estamos en el primer mes de cada año (m % 12 == 0 y m > 0)
            if m > 0 and m % 12 == 0:
                aporte *= (1 + inflacion_anual)
        if m > 0 and m % 12 == 0:
            precio_actual_udi  *= (1 + inflacion_anual)

    df = pd.DataFrame(registros, columns=["Mes", "Saldo", "Aporte"])
    return saldo, df


def simula_allianz_con_sat(
    años,
    inflacion_anual,
    rendimiento_anual,
    aporte_inicial,
    aportes_crecen,
    precio_actual_udi,
    tasa_marginal_isr,
    reinvertir_sat
):
    meses = años * 12
    r_m = tasa_mensual(rendimiento_anual)

    saldo = 0.0
    aporte = aporte_inicial
    precio_udi = precio_actual_udi
    devolucion_acumulada = 0.0  # solo para gráfica individual del SAT

    registros = []

    for m in range(meses):
        # ---- Aporte mensual ----
        saldo += aporte

        # ---- Rendimiento mensual ----
        saldo *= (1 + r_m)

        # ---- Comisión mensual de 15 UDIS ----
        saldo -= precio_udi * 15

        # ---- Cada año ocurre esto ----
        if (m + 1) % 12 == 0:
            # Aumento del aporte
            if aportes_crecen:
                aporte *= (1 + inflacion_anual)

            # Aumento del precio UDI
            precio_udi *= (1 + inflacion_anual)

            # Cálculo de devolución SAT anual
            devolucion_anual = aporte_inicial * 12 * tasa_marginal_isr
            devolucion_acumulada += devolucion_anual

            # Reinvertir o no la devolución
            if reinvertir_sat:
                saldo += devolucion_anual

        registros.append((m, saldo, devolucion_acumulada))

    df = pd.DataFrame(
        registros,
        columns=["Mes", "Saldo_Allianz_SAT", "SAT_Acumulado"]
    )

    return saldo, df


# -----------------------
# STREAMLIT UI
# -----------------------

st.title("🧮 Simulador de Retiro – PPR Interactivo")
st.markdown("### Flight Simulator Financiero para tu Futuro 🚀")

# Sidebar inputs
st.sidebar.header("Parámetros de entrada")

edad_actual = st.sidebar.number_input("Edad actual", 18, 80, 29)
edad_retiro = st.sidebar.number_input("Edad al retiro", edad_actual + 1, 90, 50)
edad_final = st.sidebar.number_input("Edad hasta vivir", edad_retiro + 1, 120, 85)

años_a_retiro = edad_retiro - edad_actual
años_retiro = edad_final - edad_retiro

pension_hoy = st.sidebar.number_input("Pensión mensual deseada (pesos de hoy)", 1000, 100000, 20000)
inflacion = st.sidebar.slider("Inflación anual (%)", 1.0, 10.0, 4.0) / 100
rendimiento = st.sidebar.slider("Rendimiento anual promedio (%)", 3.0, 20.0, 8.0) / 100

aporte_inicial = st.sidebar.number_input("Aporte mensual inicial (pesos de hoy)", 0, 100000, 5000)
aportes_crecen = st.sidebar.checkbox("Aumentar aportes cada año con inflación", True)

# Cálculo del capital objetivo
capital_obj, pension_retiro = capital_necesario_para_pension(
    pension_hoy, años_a_retiro, años_retiro, inflacion, rendimiento
)

# Cálculo de acumulación
saldo, df = simula_acumulacion(años_a_retiro, inflacion, rendimiento, aporte_inicial, aportes_crecen)
df["Aportes acumulados"] = df["Aporte"].cumsum()

# Cálculo de pensión alcanzada
pension_alcanzada = pension_alcanzable_desde_capital(saldo, años_retiro, inflacion, rendimiento)

# Cálculo de valor presente
vp_objetivo = valor_presente(pension_retiro, inflacion, años_a_retiro)
vp_alcanzado = valor_presente(pension_alcanzada, inflacion, años_a_retiro)

# -----------------------
# TABS
# -----------------------
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Acumulación",
    "Pensión vs Meta",
    "Edades de Retiro",
    "Sensibilidad",
    "Estrategias Avanzadas",
    "Simulación de Retiro",
    "Exportación",
    "Allianz PPR"
])

# ================
# TAB 1: Acumulación
# ================
with tab1:
    st.header("📈 Evolución del ahorro hasta el retiro")

    # Gráfica con dos líneas
    line_saldo = alt.Chart(df).mark_line(color="#1f77b4", strokeWidth=3).encode(
        x="Mes",
        y="Saldo",
        tooltip=["Mes", "Saldo", "Aportes acumulados"]
    )

    line_aportes = alt.Chart(df).mark_line(color="#ff7f0e", strokeWidth=2, strokeDash=[4, 4]).encode(
        x="Mes",
        y="Aportes acumulados",
        tooltip=["Mes", "Saldo", "Aportes acumulados"]
    )

    chart = (line_saldo + line_aportes).properties(
        width="container",
        height=350
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    st.markdown(f"**Saldo acumulado:** ${saldo:,.2f}")
    st.markdown(f"**Aportes totales:** ${df['Aportes acumulados'].iloc[-1]:,.2f}")
    st.markdown(f"**Interés compuesto generado:** ${saldo - df['Aportes acumulados'].iloc[-1]:,.2f}")

    with st.expander("📄 Ver tabla completa"):
        st.dataframe(df)


# ================
# TAB 2: Pensión vs Meta
# ================
with tab2:
    st.header("🎯 Comparación: Pensión objetivo vs pensión alcanzada (nominal)")

    col1, col2, col3 = st.columns(3)
    col1.metric("Objetivo mensual (nominal)", f"${pension_retiro:,.2f}")
    col2.metric("Alcanzada mensual", f"${pension_alcanzada:,.2f}")
    col3.metric("% del objetivo", f"{(pension_alcanzada / pension_retiro) * 100:.2f}%")

    st.header("💵 Valor presente de la pensión alcanzada")

    col1, col2, col3 = st.columns(3)
    col1.metric("Objetivo (hoy)", f"${vp_objetivo:,.2f}")
    col2.metric("Alcanzado (hoy)", f"${vp_alcanzado:,.2f}")
    col3.metric("% del objetivo (hoy)", f"{(vp_alcanzado / vp_objetivo) * 100:.2f}%")

    # Gráfica apilada
    objetivo = pension_retiro
    actual = pension_alcanzada

    if actual >= objetivo:
        fig = go.Figure(data=[
            go.Bar(name='Objetivo', x=['Pensión'], y=[objetivo], marker_color='lightblue'),
            go.Bar(name='Extra', x=['Pensión'], y=[actual - objetivo], marker_color='green')
        ])
    else:
        fig = go.Figure(data=[
            go.Bar(name='Alcanzado', x=['Pensión'], y=[actual], marker_color='lightblue'),
            go.Bar(name='Falta', x=['Pensión'], y=[objetivo - actual], marker_color='red')
        ])

    fig.update_layout(barmode='stack', yaxis_title="Pesos mensuales")
    st.plotly_chart(fig, use_container_width=True)

# ================
# TAB 4 a 8: Vacías (listas para FASE 3)
# ================
with tab3:
    st.header("🟩 Comparador de edades de retiro")

    st.markdown("""
    Explora cómo cambia tu pensión alcanzable si decides retirarte a distintas edades.
    Esta gráfica muestra el **% del objetivo cumplido** según la edad de retiro.
    """)

    # Rango de edades a analizar
    min_edad = st.slider("Edad mínima a simular", 40, edad_retiro, 45)
    max_edad = st.slider("Edad máxima a simular", edad_retiro, 75, 70)

    edades = list(range(min_edad, max_edad + 1))

    resultados = []

    for retiro_ed in edades:
        años_a = retiro_ed - edad_actual
        años_r = edad_final - retiro_ed

        if años_a <= 0:
            continue

        # Simular acumulación para esta edad
        saldo_temp, df_temp = simula_acumulacion(años_a, inflacion, rendimiento, aporte_inicial, aportes_crecen)

        # Pensión objetivo y alcanzada
        cap_obj_temp, pension_ret_temp = capital_necesario_para_pension(
            pension_hoy, años_a, años_r, inflacion, rendimiento
        )

        pension_alc_temp = pension_alcanzable_desde_capital(saldo_temp, años_r, inflacion, rendimiento)

        # Valor presente
        vp_obj_temp = valor_presente(pension_ret_temp, inflacion, años_a)
        vp_alc_temp = valor_presente(pension_alc_temp, inflacion, años_a)

        resultados.append({
            "Edad de retiro": retiro_ed,
            "% objetivo nominal": pension_alc_temp / pension_ret_temp * 100,
            "Pensión alcanzada (nominal)": pension_alc_temp,
            "Pensión objetivo (nominal)": pension_ret_temp,
            "Saldo acumulado": saldo_temp,
            "% objetivo en valor presente": vp_alc_temp / vp_obj_temp * 100,
            "Pensión alcanzada (hoy)": vp_alc_temp,
            "Pensión objetivo (hoy)": vp_obj_temp,
        })

    df_ret = pd.DataFrame(resultados)

    st.subheader("📊 Resultado comparativo")
    st.dataframe(df_ret)

    # Gráfica principal
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_ret["Edad de retiro"],
        y=df_ret["% objetivo nominal"],
        mode="lines+markers",
        name="% objetivo (nominal)",
        line=dict(color="blue", width=3),
        marker=dict(size=7)
    ))

    fig.add_trace(go.Scatter(
        x=df_ret["Edad de retiro"],
        y=df_ret["% objetivo en valor presente"],
        mode="lines+markers",
        name="% objetivo (hoy)",
        line=dict(color="green", width=3, dash="dash"),
        marker=dict(size=7)
    ))

    fig.update_layout(
        title="Cumplimiento del objetivo según edad de retiro",
        xaxis_title="Edad de retiro",
        yaxis_title="% del objetivo",
        yaxis=dict(range=[0, max(120, df_ret["% objetivo nominal"].max() + 10)]),
        legend=dict(orientation="h")
    )

    st.plotly_chart(fig, use_container_width=True)

    # Punto óptimo
    mejor = df_ret.loc[df_ret["% objetivo nominal"].idxmax()]
    st.success(
        f"💡 **La mejor edad de retiro según tu estrategia actual sería {int(mejor['Edad de retiro'])} años**, "
        f"ya que lograrías {mejor['% objetivo nominal']:.2f}% del objetivo."
    )

with tab4:
    st.header("🧪 Análisis de sensibilidad")

    st.markdown("""
    Aquí puedes ver cuánto impactan pequeños cambios en tu estrategia:

    - Aportar **+500** o **+1000** pesos al mes  
    - Trabajar **1 año más** antes de retirarte  
    - Obtener **+1% de rendimiento** anual  
    - Sufrir **+1% de inflación** anual  

    Comparamos cada escenario contra tu configuración **base**.
    """)

    escenarios = []

    # Escenario base (el actual)
    escenarios.append({
        "Escenario": "Base",
        "Aporte mensual": aporte_inicial,
        "Años a retiro": años_a_retiro,
        "Años de retiro": años_retiro,
        "Inflación anual": inflacion,
        "Rendimiento anual": rendimiento,
        "Pensión nominal": pension_alcanzada,
        "Pensión hoy": vp_alcanzado
    })

    # +500 al mes
    saldo_500, pens_500, vp_500 = calcula_pension_scenario(
        años_a_retiro, años_retiro, inflacion, rendimiento, aporte_inicial + 500, aportes_crecen
    )
    if pens_500 is not None:
        escenarios.append({
            "Escenario": "+500 al mes",
            "Aporte mensual": aporte_inicial + 500,
            "Años a retiro": años_a_retiro,
            "Años de retiro": años_retiro,
            "Inflación anual": inflacion,
            "Rendimiento anual": rendimiento,
            "Pensión nominal": pens_500,
            "Pensión hoy": vp_500
        })

    # +1000 al mes
    saldo_1000, pens_1000, vp_1000 = calcula_pension_scenario(
        años_a_retiro, años_retiro, inflacion, rendimiento, aporte_inicial + 1000, aportes_crecen
    )
    if pens_1000 is not None:
        escenarios.append({
            "Escenario": "+1000 al mes",
            "Aporte mensual": aporte_inicial + 1000,
            "Años a retiro": años_a_retiro,
            "Años de retiro": años_retiro,
            "Inflación anual": inflacion,
            "Rendimiento anual": rendimiento,
            "Pensión nominal": pens_1000,
            "Pensión hoy": vp_1000
        })

    # +1 año de trabajo (te retiras 1 año después)
    años_a_retiro_plus = años_a_retiro + 1
    años_retiro_minus = años_retiro - 1
    saldo_1y, pens_1y, vp_1y = calcula_pension_scenario(
        años_a_retiro_plus, años_retiro_minus, inflacion, rendimiento, aporte_inicial, aportes_crecen
    )
    if pens_1y is not None:
        escenarios.append({
            "Escenario": "+1 año de trabajo",
            "Aporte mensual": aporte_inicial,
            "Años a retiro": años_a_retiro_plus,
            "Años de retiro": años_retiro_minus,
            "Inflación anual": inflacion,
            "Rendimiento anual": rendimiento,
            "Pensión nominal": pens_1y,
            "Pensión hoy": vp_1y
        })

    # +1% rendimiento (piso de seguridad por si ya estás muy alto)
    rendimiento_up = rendimiento + 0.01
    saldo_rend, pens_rend, vp_rend = calcula_pension_scenario(
        años_a_retiro, años_retiro, inflacion, rendimiento_up, aporte_inicial, aportes_crecen
    )
    if pens_rend is not None:
        escenarios.append({
            "Escenario": "+1% rendimiento",
            "Aporte mensual": aporte_inicial,
            "Años a retiro": años_a_retiro,
            "Años de retiro": años_retiro,
            "Inflación anual": inflacion,
            "Rendimiento anual": rendimiento_up,
            "Pensión nominal": pens_rend,
            "Pensión hoy": vp_rend
        })

    # +1% inflación
    inflacion_up = inflacion + 0.01
    saldo_inf, pens_inf, vp_inf = calcula_pension_scenario(
        años_a_retiro, años_retiro, inflacion_up, rendimiento, aporte_inicial, aportes_crecen
    )
    if pens_inf is not None:
        escenarios.append({
            "Escenario": "+1% inflación",
            "Aporte mensual": aporte_inicial,
            "Años a retiro": años_a_retiro,
            "Años de retiro": años_retiro,
            "Inflación anual": inflacion_up,
            "Rendimiento anual": rendimiento,
            "Pensión nominal": pens_inf,
            "Pensión hoy": vp_inf
        })

    df_sens = pd.DataFrame(escenarios)

    # Tomamos la base como referencia
    pension_base_nom = df_sens.loc[df_sens["Escenario"] == "Base", "Pensión nominal"].iloc[0]
    pension_base_hoy = df_sens.loc[df_sens["Escenario"] == "Base", "Pensión hoy"].iloc[0]

    df_sens["Δ nominal vs base"] = df_sens["Pensión nominal"] - pension_base_nom
    df_sens["Δ nominal vs base (%)"] = (df_sens["Pensión nominal"] / pension_base_nom - 1) * 100
    df_sens["Δ hoy vs base"] = df_sens["Pensión hoy"] - pension_base_hoy
    df_sens["Δ hoy vs base (%)"] = (df_sens["Pensión hoy"] / pension_base_hoy - 1) * 100

    st.subheader("📊 Tabla de escenarios")
    st.dataframe(df_sens)

    st.subheader("📉 Impacto en la pensión (nominal) vs base")

    # Ordenamos por pensión nominal
    df_plot = df_sens.sort_values("Pensión nominal", ascending=True)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_plot["Escenario"],
        x=df_plot["Pensión nominal"],
        orientation='h',
        text=[f"${v:,.0f}" for v in df_plot["Pensión nominal"]],
        textposition="outside",
        marker_color=["#1f77b4" if esc == "Base" else "#ff7f0e" for esc in df_plot["Escenario"]]
    ))

    fig.update_layout(
        xaxis_title="Pensión mensual (nominal)",
        yaxis_title="Escenario",
        margin=dict(l=10, r=10, t=10, b=10),
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("💡 Interpretación rápida")

    for _, row in df_sens.iterrows():
        if row["Escenario"] == "Base":
            continue
        st.markdown(
            f"- **{row['Escenario']}**: cambia tu pensión nominal a "
            f"${row['Pensión nominal']:,.0f} ({row['Δ nominal vs base']:+,.0f} vs base, "
            f"{row['Δ nominal vs base (%)']:+.2f}%)"
        )

with tab5:
    st.header("🟪 Estrategias avanzadas de aportación")

    st.markdown("Simula patrones de ahorro más realistas:")

    estrategia = st.selectbox(
        "Selecciona la estrategia",
        ["Front-loaded", "Back-loaded", "Crecimiento por sueldo", "Aportes manuales"]
    )

    meses_totales = años_a_retiro * 12

    # Simulación base para comparar (línea fantasma)
    saldo_base, df_base = simula_acumulacion(años_a_retiro, inflacion, rendimiento, aporte_inicial, aportes_crecen)
    df_base["Aportes acumulados"] = df_base["Aporte"].cumsum()

    aportes = None  # se define luego

    # ---------------------------------------------------
    # FRONT-LOADED
    # ---------------------------------------------------
    if estrategia == "Front-loaded":
        st.subheader("📌 Front-loaded (aportas mucho al inicio)")
        aporte_alto = st.number_input("Aporte alto (primeros años)", 0, 100000, 10000)
        años_front = st.number_input("Años con aporte alto", 1, años_a_retiro, 3)
        aporte_normal = st.number_input("Aporte normal después", 0, 100000, aporte_inicial)

        aportes = estrategia_front_loaded(años_a_retiro, aporte_normal, aporte_alto, años_front)
        aportes = aplica_crecimiento_inflacion(aportes, inflacion, aportes_crecen)

    # ---------------------------------------------------
    # BACK-LOADED
    # ---------------------------------------------------
    if estrategia == "Back-loaded":
        st.subheader("📌 Back-loaded (aportas más en el futuro)")
        aporte_bajo = st.number_input("Aporte bajo (primeros años)", 0, 100000, aporte_inicial)
        años_bajo = st.number_input("Años con aporte bajo", 1, años_a_retiro, 5)
        aporte_alto = st.number_input("Aporte alto después", 0, 100000, 12000)

        aportes = estrategia_back_loaded(años_a_retiro, aporte_bajo, aporte_alto, años_bajo)
        aportes = aplica_crecimiento_inflacion_back(aportes, inflacion, aportes_crecen)

    # ---------------------------------------------------
    # CRECIMIENTO SALARIAL
    # ---------------------------------------------------
    if estrategia == "Crecimiento por sueldo":
        st.subheader("📌 Crecimiento anual por sueldo")
        aporte_ini_s = st.number_input("Aporte inicial mensual", 0, 100000, aporte_inicial)
        crecimiento = st.slider("Crecimiento anual (%)", 0.0, 20.0, 7.0) / 100
        incluir_inflacion = st.checkbox("Agregar inflación además del crecimiento salarial")

        infl = inflacion if incluir_inflacion else None
        # aportes = estrategia_crecimiento_salarial(años_a_retiro, aporte_ini_s, crecimiento, infl)

        aportes = estrategia_crecimiento_salarial(años_a_retiro, aporte_ini_s, crecimiento, infl)

        # Si inflación NO estaba incluida, pero aportes_crecen=True → aplicarla
        if infl is None and aportes_crecen:
            aportes = aplica_crecimiento_inflacion(aportes, inflacion, True)

    # ---------------------------------------------------
    # APORTES MANUALES
    # ---------------------------------------------------
    if estrategia == "Aportes manuales":
        st.subheader("📌 Aportes manuales (editables mes a mes)")
        df_manual = pd.DataFrame({
            "Mes": range(meses_totales),
            "Aporte": [aporte_inicial] * meses_totales
        })

        df_edit = st.data_editor(df_manual, key="editor_aportes", use_container_width=True)

        if st.button("🚀 Simular estrategia manual"):
            aportes = df_edit["Aporte"].tolist()
            aportes = aplica_crecimiento_inflacion(aportes, inflacion, aportes_crecen)

        else:
            st.info("Haz cambios en la tabla y presiona *Simular estrategia manual* para ver resultados.")

        # aportes = df_edit["Aporte"].tolist()

    # ---------------------------------------------------
    # SOLO SIMULAMOS SI aportes YA está definido
    # ---------------------------------------------------
    if aportes is not None:
        saldo_adv, df_adv = simula_aportes_personalizados(aportes, inflacion, rendimiento)
        df_adv["Aportes acumulados"] = df_adv["Aporte"].cumsum()

        pension_adv = pension_alcanzable_desde_capital(saldo_adv, años_retiro, inflacion, rendimiento)
        pension_adv_hoy = valor_presente(pension_adv, inflacion, años_a_retiro)



        # =============================
        #       Resultados BASELINE
        # =============================
        st.markdown("### 🧱 Resultado sin estrategia (baseline)")

        # CALCULAR PENSIONES BASELINE
        pension_base_nominal = pension_alcanzable_desde_capital(saldo_base, años_retiro, inflacion, rendimiento)
        pension_base_hoy = valor_presente(pension_base_nominal, inflacion, años_a_retiro)

        colb1, colb2, colb3 = st.columns(3)

        with colb1:
            st.metric(
                "Saldo al retiro (baseline)",
                f"${saldo_base:,.2f}"
            )

        with colb2:
            st.metric(
                "Pensión alcanzada (nominal, baseline)",
                f"${pension_base_nominal:,.2f}"
            )

        with colb3:
            st.metric(
                "Pensión alcanzada (HOY, baseline)",
                f"${pension_base_hoy:,.2f}"
            )

        st.subheader("🚀 Resultado de la estrategia")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Saldo al retiro", f"${saldo_adv:,.2f}")
        col2.metric("Pensión alcanzada (nominal)", f"${pension_adv:,.2f}")
        col3.metric("Pensión alcanzada (HOY)", f"${pension_adv_hoy:,.2f}")

        mejora_saldo = (saldo_adv / saldo_base - 1) * 100
        col4.metric("% de mejora obtenido",  f"{mejora_saldo:.2f}%")



        # ---- GRÁFICO CON FANTASMA ----
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df_base["Mes"],
            y=df_base["Saldo"],
            mode="lines",
            name="Base (mensualidad constante)",
            line=dict(color="gray", width=2, dash="dash")
        ))

        fig.add_trace(go.Scatter(
            x=df_adv["Mes"],
            y=df_adv["Saldo"],
            mode="lines",
            name="Estrategia avanzada",
            line=dict(width=4)
        ))

        fig.update_layout(
            title="Evolución del saldo — Estrategia vs Base",
            xaxis_title="Mes",
            yaxis_title="Saldo",
        )

        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📄 Tabla completa de la estrategia"):
            st.dataframe(df_adv)

with tab6:
    st.header("🧓 Simulación completa del retiro")

    st.markdown("""
    Aquí puedes ver cómo evoluciona tu saldo *después* del retiro:

    - Tu pensión mensual sube con la inflación  
    - Tu saldo gana rendimientos cada mes  
    - Observa si te quedas sin dinero antes del tiempo esperado
    """)

    # --- Datos clave del usuario ---
    capital_final = saldo  # saldo acumulado de taba 1
    pension_inicial = pension_alcanzada  # pensión inicial (nominal)

    # Configuración ajustable
    st.subheader("⚙️ Ajustes del escenario de retiro")

    pension_inicial_mult = st.slider(
        "Multiplicador de la pensión inicial (para probar variaciones)",
        0.5, 2.0, 1.0, step=0.1
    )

    pension_inicial_adj = pension_inicial * pension_inicial_mult

    st.write(f"📌 Pensión mensual al iniciar el retiro: **${pension_inicial_adj:,.2f}**")

    # --- Simulación ---
    df_retiro = simula_retiro_mes_a_mes(
        capital_final, años_retiro, inflacion, rendimiento, pension_inicial_adj
    )

    saldo_final = df_retiro["Saldo final"].iloc[-1]
    mes_final = df_retiro["Mes"].iloc[-1]

    # --- Resultados principales ---
    st.subheader("📊 Resultado del periodo de retiro")

    col1, col2, col3 = st.columns(3)
    col1.metric("Mes donde se agota el capital", f"{mes_final}" if saldo_final == 0 else "No se agotó")
    col2.metric("Saldo final al llegar al final", f"${saldo_final:,.2f}")
    col3.metric("Años reales alcanzados", f"{mes_final / 12:.2f}")

    # --- Gráfica ---
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_retiro["Mes"],
        y=df_retiro["Saldo final"],
        mode="lines",
        name="Saldo durante el retiro",
        line=dict(color="purple", width=4)
    ))

    fig.update_layout(
        title="📉 Evolución del saldo durante el retiro",
        xaxis_title="Mes",
        yaxis_title="Saldo",
    )

    st.plotly_chart(fig, use_container_width=True)

    # Advertencia si se acabó
    if saldo_final == 0:
        st.error(f"⚠️ Te quedaste sin dinero en el mes {mes_final} ({mes_final / 12:.1f} años).")
    else:
        st.success("🎉 ¡Tu capital duró hasta el final del periodo de retiro!")

    # Tabla
    with st.expander("📄 Ver tabla completa del retiro mes a mes"):
        st.dataframe(df_retiro)

with tab7:
    st.header("⬇️ Exportación de resultados")

    st.markdown("""
    Descarga tus simulaciones y parámetros para usarlos en Excel, Google Sheets o análisis más avanzados.
    """)



    st.subheader("📁 Exportar tablas principales")

    # --- Export Acumulación ---
    st.markdown("### 🟦 Acumulación (Tab 1)")
    st.download_button(
        "📤 Descargar acumulación (CSV)",
        export_df_to_csv(df),
        file_name="acumulacion.csv",
        mime="text/csv"
    )

    st.download_button(
        "📤 Descargar acumulación (Excel)",
        export_df_to_excel(df),
        file_name="acumulacion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --- Export valor presente y resumen pensión ---
    resumen_objetivo = pd.DataFrame({
        "Concepto": ["Pensión objetivo (nominal)", "Pensión alcanzada (nominal)",
                     "Pensión objetivo (HOY)", "Pensión alcanzada (HOY)"],
        "Valor": [pension_retiro, pension_alcanzada, vp_objetivo, vp_alcanzado]
    })



    st.markdown("### 🟩 Resumen de Pensión (Tabs 2 y 3)")
    st.dataframe(resumen_objetivo)

    st.download_button(
        "📤 Descargar resumen pensión (CSV)",
        export_df_to_csv(resumen_objetivo),
        file_name="resumen_pension.csv",
        mime="text/csv"
    )

    # --- Export comparador de edades ---
    st.markdown("### 🟧 Comparador de edades de retiro (Tab 4)")
    st.download_button(
        "📤 Descargar comparador edades (CSV)",
        export_df_to_csv(df_ret),
        file_name="comparador_edades.csv",
        mime="text/csv",
        disabled=("df_ret" not in locals())
    )

    # --- Export sensibilidad ---
    st.markdown("### 🟨 Sensibilidad (Tab 5)")
    if "df_sens" in locals():
        st.download_button(
            "📤 Descargar sensibilidad (CSV)",
            export_df_to_csv(df_sens),
            file_name="sensibilidad.csv",
            mime="text/csv"
        )
    else:
        st.info("Realiza una simulación en la pestaña Sensibilidad para habilitar la descarga.")

    # --- Export estrategia avanzada ---
    st.markdown("### 🟪 Estrategias avanzadas (Tab 6)")
    if "df_adv" in locals():
        st.download_button(
            "📤 Descargar estrategia avanzada (CSV)",
            export_df_to_csv(df_adv),
            file_name="estrategia_avanzada.csv",
            mime="text/csv"
        )
    else:
        st.info("Realiza una simulación en Estrategias Avanzadas para habilitar la exportación.")

    # --- Export retiro mes a mes ---
    st.markdown("### 🧓 Simulación de Retiro (Tab 7)")
    if "df_retiro" in locals():
        st.download_button(
            "📤 Descargar simulación de retiro (CSV)",
            export_df_to_csv(df_retiro),
            file_name="simulacion_retiro.csv",
            mime="text/csv"
        )
    else:
        st.info("Ejecuta la pestaña de Simulación de Retiro para habilitar esta descarga.")


    # -------------------------------------------
    # PARÁMETROS DEL USUARIO (JSON)
    # -------------------------------------------
    st.subheader("⚙️ Guardar / Exportar parámetros")

    params = parametros_actuales_json(
        edad_actual, edad_retiro, edad_final,
        pension_hoy, inflacion, rendimiento,
        aporte_inicial, aportes_crecen
    )

    st.json(params)

    st.download_button(
        "📤 Descargar parámetros (JSON)",
        data=json.dumps(params, indent=4),
        file_name="parametros_simulacion.json",
        mime="application/json"
    )

    st.subheader("📘 Exportar archivo Excel completo (varias hojas)")

    excel_completo = export_excel_completo(
        df_acum=df,
        df_resumen=resumen_objetivo,
        df_ret=df_ret if "df_ret" in locals() else None,
        df_sens=df_sens if "df_sens" in locals() else None,
        df_adv=df_adv if "df_adv" in locals() else None,
        df_retiro=df_retiro if "df_retiro" in locals() else None,
        params=params
    )

    st.download_button(
        "📤 Descargar Excel completo (XLSX)",
        data=excel_completo,
        file_name="simulador_retiro.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")
    st.info("PDF estará disponible próximamente (requiere módulo adicional).")

with tab8:
    st.header("🟪 Comparación con Allianz (PPR real vs ETF mágico vs Colchón)")

    st.markdown("Configura tus datos:")

    colA, colB = st.columns(2)

    with colA:
        salario_anual = st.number_input(
            "💵 Salario anual (antes de impuestos)",
            0, 5_000_000, 600_000
        )
        aporte_mensual = st.number_input(
            "📦 Aporte mensual al PPR / ETF",
            0, 200_000, 5000
        )
        rendimiento_allianz = st.number_input(
            "📈 Rendimiento estimado (%)",
            0.0, 30.0, 10.0
        ) / 100  # lo usamos también para el ETF mágico

        tasa_marginal_isr = st.number_input(
            "🧾 Tasa marginal de ISR (%)",
            min_value=0.0, max_value=50.0, value=32.0
        ) / 100  # por ahora solo la mostramos, luego la usaremos para Allianz

    with colB:
        valor_udi = st.number_input(
            "📐 Valor actual de la UDI",
            5.0, 20.0, 8.60
        )
        inflacion_anual = st.number_input(
            "📊 Inflación anual (%)",
            0.0, 20.0, 4.0
        ) / 100
        reinvertir_sat = st.checkbox("Reinvertir devolución del SAT (para Allianz, más adelante)")

    años_retiro = st.number_input(
        "🎯 Años restantes para el retiro",
        1, 60, 37
    )

    # ----------------------------
    # BOTÓN
    # ----------------------------
    if st.button("🚀 Simular Allianz vs ETF vs Colchón"):
        # ==========================================================
        #   1) ETF MÁGICO (sin comisiones, mismo motor base)
        # ==========================================================
        saldo_etf_bruto, df_etf = simula_acumulacion(
            años_retiro,
            inflacion_anual,
            rendimiento_allianz,
            aporte_mensual,
            aportes_crecen,
        )

        # Colchón = mismos aportes pero sin rendimiento
        df_etf["Colchón"] = df_etf["Aporte"].cumsum()
        saldo_colchon = df_etf["Colchón"].iloc[-1]

        # Ganancia y ETF neto después de ISR
        aportes_totales = df_etf["Aporte"].sum()
        ganancia_etf = saldo_etf_bruto - aportes_totales

        tasa_isr_etf = 0.35
        isr_etf = max(0, ganancia_etf * tasa_isr_etf)
        saldo_etf_neto = saldo_etf_bruto - isr_etf

        # ==========================================================
        #   2) ALLIANZ SIMPLE (sólo comisión UDI, SIN SAT, SIN ISR)
        # ==========================================================
        saldo_allianz_bruto, df_allianz = simula_acumulacion_allianz(
            años_retiro,
            inflacion_anual,
            rendimiento_allianz,
            aporte_mensual,
            aportes_crecen,
            valor_udi
        )

        saldo_allianz_con_sat, df_allianz_sat = simula_allianz_con_sat(
            años_retiro,
            inflacion_anual,
            rendimiento_allianz,
            aporte_mensual,
            aportes_crecen,
            valor_udi,
            tasa_marginal_isr,
            reinvertir_sat
        )

        # ==========================================================
        #   3) MÉTRICAS
        # ==========================================================
        st.subheader("📊 Resultados (sin ISR, sin SAT)")

        col1, col2, col3 = st.columns(3)
        col1.metric("ETF mágico (bruto)", f"${saldo_etf_bruto:,.2f}")
        col2.metric("Allianz simple (con comisión UDI)", f"${saldo_allianz_bruto:,.2f}")
        col3.metric("Colchón (sin rendimiento)", f"${saldo_colchon:,.2f}")

        st.subheader("📊 Resultados con opción SAT")

        col1, col2 = st.columns(2)
        col1.metric("Allianz + SAT reinvertido", f"${saldo_allianz_con_sat:,.2f}")
        col2.metric("SAT acumulado (solo mostrando)",
                    f"${df_allianz_sat['SAT_Acumulado'].iloc[-1]:,.2f}")


        # ==========================================================
        #   4) GRÁFICA ETF vs Allianz vs Colchón
        # ==========================================================
        fig = go.Figure()

        # ETF
        fig.add_trace(go.Scatter(
            x=df_etf["Mes"],
            y=df_etf["Saldo"],
            name="ETF mágico (sin comisiones)",
            line=dict(width=3)
        ))

        # Allianz
        fig.add_trace(go.Scatter(
            x=df_etf["Mes"],  # mismos meses
            y=df_allianz["Saldo"],
            name="Allianz simple (15 UDIS/mes)",
            line=dict(width=3, color="red")
        ))

        # Colchón
        fig.add_trace(go.Scatter(
            x=df_etf["Mes"],
            y=df_etf["Colchón"],
            name="Colchón (sin rendimiento)",
            line=dict(width=2, dash="dash", color="gray")
        ))

        fig.add_trace(go.Scatter(
            x=df_allianz_sat["Mes"],
            y=df_allianz_sat["SAT_Acumulado"],
            name="Devolución SAT acumulada",
            line=dict(width=3, color="green")
        ))

        fig.add_trace(go.Scatter(
            x=df_allianz_sat["Mes"],
            y=df_allianz_sat["Saldo_Allianz_SAT"],
            name="Allianz + SAT reinvertido",
            line=dict(width=3, color="green")
        ))

        fig.update_layout(
            title="Evolución — Allianz (simple) vs ETF vs Colchón",
            xaxis_title="Mes",
            yaxis_title="Saldo",
        )

        st.plotly_chart(fig, use_container_width=True)


        # ==========================================================
        df_final = df_etf.copy()
        df_final["Saldo_Allianz"] = df_allianz["Saldo"]
        df_final["Saldo_Allianz_SAT"] = df_allianz_sat["Saldo_Allianz_SAT"]
        df_final["SAT_Acumulado"] = df_allianz_sat["SAT_Acumulado"]

        st.subheader("📋 Tabla completa de la simulación")
        st.dataframe(df_final)