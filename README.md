
# 🧮 PPR Simulator by Ich  
Simulador profesional de ahorro y retiro basado en Allianz, CETES y cálculos reales 100% replicados desde Excel.

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
- Early Stop opcional para detener aportaciones en cualquier año
- Estrategia de aportes optimizada (primeros 18 meses reducidos + offset automático/manual)
- Simulación exacta de Allianz (comisiones, UDIS, cargos fijos, bono de fidelidad)
- SAT real según UMA, salarios, ISR marginal y límites fiscales
- Comparación directa con ETF ideal **bruto** y **neto**

### 🟥 Etapa de retiro
- Simulación de retiro **nominal** (mismo monto cada mes)
- Simulación de retiro **indexado** (sube cada año con la inflación)
- Búsqueda del retiro óptimo con algoritmo binario
- Cálculo de mensualidades máximas para agotar el fondo en *N* años
- Gráficas comparativas de saldos VF y VP
- Tablas reales de PPR vs CETES, nominal e indexado

---

## 📂 Estructura del proyecto

```
ppr-simulator-by-ich/
│
├─ allianz.py                      # UI con Streamlit
├─ allianz_functions.py            # Funciones nominales (PPR/CETES)
├─ allianz_functions_indexadas.py  # Funciones para retiros indexados
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

## 🧑‍💻 Autor

**Gabriel Ichcanziho Pérez Landa**  
Aka *Ich*

---

## 🤝 Contribuciones

Este proyecto es **código abierto**.

Puedes crear una rama con:

```
git checkout -b feature/nueva-funcion
```

Y subirla con:

```
git push --set-upstream origin feature/nueva-funcion
```

---

## 📄 Licencia

Open Source — MIT License.
