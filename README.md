# 🧮 PPR Simulator by Ich  
Simulador profesional de ahorro y retiro basado en Allianz, CETES, y cálculos reales 100% replicados desde Excel.

Este proyecto permite comparar:

- Allianz real **con y sin SAT**
- ETF ideal vs Allianz
- Retiro **nominal** vs **indexado**
- Cálculos a **Valor Futuro (VF)** y **Valor Presente (VP)**
- Tablas completas de simulación mes a mes
- Gráficas interactivas (Plotly)
- Ejecución visual mediante Streamlit

---

## 🚀 Características principales

### 🟦 Etapa de acumulación
- Aportes crecientes con inflación
- Simulación exacta de Allianz (comisiones, UDIS, cargos fijos, bono)
- SAT real según UMA, salarios e ISR marginal
- Comparación directa con ETF ideal bruto y neto

### 🟥 Etapa de retiro
- Simulación de retiro **nominal** (mismo monto cada mes)
- Simulación de retiro **indexado** (sube con inflación anual)
- Retiro óptimo mediante búsqueda binaria
- Cálculo de mensualidades máximas
- Gráficas y tablas de saldos VF y VP
- Total gastado acumulado
- PPR vs CETES indexado

---

## 📂 Estructura del proyecto

```
ppr-simulator-by-ich/
│
├─ allianz.py                      # UI con Streamlit
├─ allianz_functions.py            # Funciones nominales (PPR/CETES)
├─ allianz_functions_indexadas.py  # Funciones indexadas (PPR/CETES)
├─ tablas.py                       # Cálculos reales de Allianz/Excel
├─ requirements.txt                # Dependencias
├─ README.md                       # Este archivo
└─ .gitignore
```

---

## ▶️ Ejecución

Desde terminal:

```bash
streamlit run allianz.py
```

El simulador abrirá tu navegador automáticamente.

---

## 📦 Dependencias principales

- Python 3.9+
- Streamlit
- Plotly
- NumPy
- Pandas

Instala todo con:

```bash
pip install -r requirements.txt
```

---

## ✨ Autor

**Gabriel Ichcanziho Pérez Landa**  
Aka *Ich*

---

## 🤝 Contribuciones

Proyecto privado, pero puedes crear ramas:

```
git checkout -b feature/nueva-funcion
```

y luego:

```
git push --set-upstream origin feature/nueva-funcion
```

---

## 📄 Licencia

Proyecto privado. Todos los derechos reservados.
