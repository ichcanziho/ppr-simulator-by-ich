# 📑 Changelog — PPR Simulator by Ich

Todas las modificaciones relevantes del proyecto se documentan aquí.

---

## 🟩 Versión 1.4 — 2025-11-20
### 🚀 Actualización mayor del simulador
- Integración completa del código real de Allianz 100% replicado desde Folleto de Allianz.
- Implementación de:
  - **Estrategia optimizada de aportaciones (primeros 18 meses)**.
  - **Early Stop** (detener aportaciones después de un número de años).
  - **SAT real** con UMA, salario variable por inflación y tasa marginal ISR.
  - **Valor Presente (VP)** y **Valor Futuro (VF)** en todas las tablas.
  - **Reinversión del SAT** directamente dentro del PPR.
- Se agregaron nuevas gráficas:
  - Evolución temporal VS ETF
  - Comparativo ETF Neto vs Allianz + SAT

---

## 🟦 Versión 1.3 — 2025-11-18
### 📊 Módulo de Retiro totalmente reescrito
- Soporte para:
  - **Retiro nominal**
  - **Retiro indexado**
- Cálculo del **retiro óptimo** mediante búsqueda binaria.
- Gráficas completas en VP.
- Tablas reales mes a mes (PPR y CETES).

---

## 🟧 Versión 1.2 — 2025-11-15
### 📈 Mejoras en acumulación
- Agregado:
  - Comparación directa con **ETF ideal bruto y neto**.
  - Cálculo de impuestos sobre ganancia del ETF (10% ISR).
- Implementación del **Bono de Fidelidad real** basado en aportación inicial.
- Integración de **aportaciones con inflación** mensual y anual.

---

## 🟨 Versión 1.1 — 2025-11-12
### 🧮 Primero prototipo completo
- Cálculo de:
  - Aportes mes a mes.
  - Rendimiento compuesto mensual.
  - Comparación inicial entre Allianz y un ETF.
- Interfaz base en Streamlit.

---

## 🟫 Versión 1.0 — 2025-11-10
### 🎉 Primera versión pública (open source)
- Estructura inicial del repositorio.
- Streamlit + Plotly configurados.
- Esqueleto general del simulador.

---

## ✨ Notas
Este changelog seguirá creciendo conforme se agreguen nuevas funciones.
