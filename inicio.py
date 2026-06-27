import streamlit as st
import numpy as np
import pulp
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================================
# CONFIGURACIÓN DE LA PÁGINA Y ESTILOS VISUALES 
# =====================================================================
st.set_page_config(
    page_title="Asistente de Decisiones Avícolas - UCR",
    page_icon="🐔",
    layout="wide"
)

# Constante comercial de empaque en Costa Rica
PESO_SACO = 46.0

# Estilos CSS personalizados para mantener la app visual, ordenada y clara
st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; color: #1f77b4; }
    .farmer-card { background-color: #f7f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #ffc107; margin-bottom: 10px; }
    .success-card { background-color: #f0f7f4; padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32; margin-bottom: 10px; }
    .warning-card { background-color: #fffde7; padding: 15px; border-radius: 10px; border-left: 5px solid #fbc02d; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("Asistente de Decisiones Avícolas")
st.markdown("### **Calculadora Inteligente de Costos y Riesgos para la Granja**")
st.divider()

# =====================================================================
# SECCIÓN 1: PANEL LATERAL - ENTRADAS PARAMÉTRICAS
# =====================================================================
st.sidebar.header(" 1. Datos de las Gallinas")
tipo_ave = st.sidebar.selectbox("Raza o línea de las aves:", ["Ponedora Rubia (Pesada)", "Ponedora Blanca (Ligera)"])
aves = st.sidebar.number_input("¿Cuántas gallinas tiene en total?:", min_value=100, max_value=50000, value=1200, step=100)
edad = st.sidebar.slider("Edad de las gallinas (Semanas):", min_value=1.0, max_value=80.0, value=35.0, step=1.0)

st.sidebar.divider()
st.sidebar.header(" 2. Precio de los Granos (Sueltos)")
p_maiz = st.sidebar.number_input("Precio del Kilo de Maíz Amarillo (₡/kg):", min_value=1.0, value=215.0, step=5.0)
p_soya = st.sidebar.number_input("Precio del Kilo de Harina de Soya (₡/kg):", min_value=1.0, value=405.0, step=5.0)
p_caliza = st.sidebar.number_input("Precio del Kilo de Caliza Molida (₡/kg):", min_value=1.0, value=80.0, step=5.0)

st.sidebar.divider()
st.sidebar.header(" 3. Opción Alternativa: Comprar Alimento Hecho")
precio_alimento_hecho_saco = st.sidebar.number_input("Precio de 1 SACO de alimento ya preparado (₡ por saco de 46kg):", min_value=1.0, value=12000.0, step=100.0)
precio_alimento_hecho_kg = precio_alimento_hecho_saco / PESO_SACO

st.sidebar.divider()
st.sidebar.header(" 4. Gastos de Camión y Bodega Unificados")
costo_flete_viaje = st.sidebar.number_input("Costo de un viaje de camión a la granja (₡ por flete):", min_value=0.0, value=22000.0, step=500.0)
dias_entrega = st.sidebar.number_input("¿Cuántos días tarda el proveedor en entregar? (Días):", min_value=1, max_value=15, value=3, step=1)
porcentaje_bodega = st.sidebar.slider("Gasto estimado de mantener la bodega al año (% del valor del producto):", min_value=5, max_value=40, value=15, step=1) / 100.0

st.sidebar.divider()
st.sidebar.header(" 5. Mercado del Huevo")
precio_huevo_unidad = st.sidebar.number_input("Precio al que vende cada huevo en la zona (₡):", min_value=1.0, value=85.0, step=5.0)

# =====================================================================
# SECCIÓN 2: ÁREA DE DATOS — PRONÓSTICO Y REQUERIMIENTOS POR EDAD
# =====================================================================
consumo_diario_pronosticado = 0.115
req_proteina = 0.165
req_calcio = 0.0375
porcentaje_puesta_pronosticado = 0.0
categoria_texto = "No especificada"

try:
    if edad < 18.0:
        etapa_productiva = "Pollita en Crecimiento (No pone huevos)"
        porcentaje_puesta_pronosticado = 0.0
        if edad <= 5.0:
            consumo_diario_pronosticado = (0.0038 * edad) + 0.002
            req_proteina = 0.185  
            req_calcio = 0.0100   
            categoria_texto = "Pollita Bebé (Fase Inicial)"
        else:
            consumo_diario_pronosticado = (0.0025 * edad) + 0.009
            req_proteina = 0.160  
            req_calcio = 0.0090   
            categoria_texto = "Pollita en Desarrollo"
    else:
        etapa_productiva = "Gallina en Producción de Huevos"
        if tipo_ave == "Ponedora Blanca (Línea Ligera)":
            consumo_diario_pronosticado = 0.100
        else:
            consumo_diario_pronosticado = 0.115
            
        if edad < 50.0:
            req_proteina = 0.165  
            req_calcio = 0.0375   
            categoria_texto = "Gallina Joven (Alta producción de huevos)"
        else:
            req_proteina = 0.158  
            req_calcio = 0.0390   
            categoria_texto = "Gallina Madura (Necesita más calcio)"

        if edad < 22.0:
            porcentaje_puesta_pronosticado = max(0.0, (0.15 * (edad - 18.0)))
        elif edad <= 35.0:
            porcentaje_puesta_pronosticado = min(0.94, 0.85 + (0.006 * (edad - 22.0)))
        else:
            porcentaje_puesta_pronosticado = max(0.65, 0.94 - (0.0045 * (edad - 35.0)))

    alimento_meta_kg = aves * consumo_diario_pronosticado * 30
    huevos_diarios_estimados = aves * porcentaje_puesta_pronosticado
    huevos_mensuales_estimados = huevos_diarios_estimados * 30
    cartones_mensuales = huevos_mensuales_estimados / 30

except Exception as e:
    st.error(f"❌ Error al calcular los datos de las aves: {e}")
    st.stop()

st.header(" Resumen Operativo de la Finca (Pronósticos)")
st.info(f" **Situación de las aves:** Etapa actual: **{categoria_texto}**")

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
    st.metric(" Consumo por Gallina al Día", f"{consumo_diario_pronosticado * 1000:.0f} gramos")
    st.write(f"**Comida necesaria al mes:** {alimento_meta_kg:,.1f} kg")
    st.write(f"Equivale a unos **{alimento_meta_kg/PESO_SACO:,.0f} sacos** al mes.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_f2:
    st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
    st.metric(" Porcentaje de Postura", f"{porcentaje_puesta_pronosticado * 100:.1f} %")
    st.markdown("</div>", unsafe_allow_html=True)

with col_f3:
    st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
    st.metric(" Producción Mensual Estimada", f"{cartones_mensuales:,.0f} Cartones (de 30 h.)")
    ingreso_estimado = huevos_mensuales_estimados * precio_huevo_unidad
    st.write(f"**Venta bruta estimada al mes:** ₡ {ingreso_estimado:,.2f}")
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# =====================================================================
# SECCIÓN 3: ÁREA DE OPTIMIZACIÓN — PROGRAMACIÓN LINEAL INTERNA
# =====================================================================
es_factible = False
try:
    prob = pulp.LpProblem("Mezcla_Costo_Minimo", pulp.LpMinimize)
    x1 = pulp.LpVariable("Maiz", lowBound=0)
    x2 = pulp.LpVariable("Soya", lowBound=0)
    x3 = pulp.LpVariable("Caliza", lowBound=0)

    prob += (x1 * p_maiz + x2 * p_soya + x3 * p_caliza)

    prob += x1 + x2 + x3 == alimento_meta_kg                                           
    prob += 0.085 * x1 + 0.440 * x2 >= (alimento_meta_kg * req_proteina)               
    prob += 0.0002 * x1 + 0.0025 * x2 + 0.3800 * x3 >= (alimento_meta_kg * req_calcio) 
    prob += x1 >= 0.55 * alimento_meta_kg                                              

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    es_factible = pulp.LpStatus[status] == "Optimal"

except Exception as e:
    st.error(f"❌ Error en el cálculo de programación lineal: {e}")

# =====================================================================
# SECCIÓN 4: MODELO DE INVENTARIO CONTRATADO / UNIFICADO (EOQ Y ROP)
# =====================================================================
if es_factible:
    try:
        kg_maiz = x1.varValue
        kg_soya = x2.varValue
        kg_caliza = x3.varValue
        costo_total_fabricar = pulp.value(prob.objective)
        precio_promedio_fabricado_kg = costo_total_fabricar / alimento_meta_kg
        
        proporcion_maiz = kg_maiz / alimento_meta_kg
        proporcion_soya = kg_soya / alimento_meta_kg
        proporcion_caliza = kg_caliza / alimento_meta_kg
        
        demanda_anual_total = alimento_meta_kg * 12
        demanda_diaria_total = alimento_meta_kg / 30
        colchon_seguridad_total = demanda_diaria_total * 1.5

        # PLAN A: LOGÍSTICA CONSOLIDADA DE MATERIAS PRIMAS
        precio_ponderado_mezcla_kg = (proporcion_maiz * p_maiz) + (proporcion_soya * p_soya) + (proporcion_caliza * p_caliza)
        h_ponderado_mezcla = precio_ponderado_mezcla_kg * porcentaje_bodega

        q_grupo_total_kg = np.sqrt((2 * demanda_anual_total * costo_flete_viaje) / h_ponderado_mezcla) if h_ponderado_mezcla > 0 else 0
        viajes_al_ano_fabricar = demanda_anual_total / q_grupo_total_kg if q_grupo_total_kg > 0 else 0
        
        q_maiz_viaje = q_grupo_total_kg * proporcion_maiz
        q_soya_viaje = q_grupo_total_kg * proporcion_soya
        q_caliza_viaje = q_grupo_total_kg * proporcion_caliza

        rop_grupo_total = (demanda_diaria_total * dias_entrega) + colchon_seguridad_total

        # PLAN B: LOGÍSTICA DE ALIMENTO COMERCIAL TERMINADO
        costo_total_comprar_hecho = alimento_meta_kg * precio_alimento_hecho_kg
        costo_almacenar_hecho_anual = precio_alimento_hecho_kg * porcentaje_bodega
        
        q_optimo_comprar = np.sqrt((2 * demanda_anual_total * costo_flete_viaje) / costo_almacenar_hecho_anual)
        viajes_al_ano_comprar = demanda_anual_total / q_optimo_comprar
        rop_hecho = (demanda_diaria_total * dias_entrega) + colchon_seguridad_total

        # PRESENTACIÓN EN PARALELO COMPARATIVA RESTRUCTURADA
        st.header(" Análisis de Costos e Inventario Unificado")
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("<div class='farmer-card' style='border-left: 5px solid #1f77b4;'>", unsafe_allow_html=True)
            st.markdown("####  OPCIÓN A: Fabricar el alimento en la granja")
            st.write(f"* **Costo de los granos por kilo mezclado:** ₡ {precio_promedio_fabricado_kg:.2f} el kg.")
            st.write("---")
            
            # Tabla con fila de totales para evitar confusiones
            df_inv_mp = pd.DataFrame({
                "Insumo / Concepto": ["Maíz Amarillo", "Harina de Soya", "Caliza Molida"],
                "Gasto al Mes (kg)": [kg_maiz, kg_soya, kg_caliza],
                "Traer por Camión (kg) [EOQ]": [q_maiz_viaje, q_soya_viaje, q_caliza_viaje]
            })
            
            fila_total_mp = pd.DataFrame({
                "Insumo / Concepto": ["TOTAL (Masa Bruta)"],
                "Gasto al Mes (kg)": [df_inv_mp["Gasto al Mes (kg)"].sum()],
                "Traer por Camión (kg) [EOQ]": [df_inv_mp["Traer por Camión (kg) [EOQ]"].sum()]
            })
            df_inv_mp = pd.concat([df_inv_mp, fila_total_mp], ignore_index=True)
            
            st.dataframe(df_inv_mp.style.format({
                "Gasto al Mes (kg)": "{:,.1f}", 
                "Traer por Camión (kg) [EOQ]": "{:,.1f}"
            }), hide_index=True)
            
            st.markdown("#####  Distribución Logística Inteligente:")
            st.write(f"* **Consumo de la Granja:** Tus gallinas se comen **{alimento_meta_kg:,.1f} kg** al mes.")
            st.write(f"* **Pedido al Camión (EOQ):** Para ahorrar fletes, pides un camión consolidado con **{q_grupo_total_kg:,.1f} kg** totales por viaje.")
            st.write(f"* **Frecuencia:** Llamas al camión de granos unas **{viajes_al_ano_fabricar:.1f} veces al año**.")
            st.write(f"*  **Punto de Reorden (ROP):** Pide de nuevo cuando queden menos de **{rop_grupo_total:,.1f} kg** en tu bodega.")
            
            st.metric(" Costo Mensual de Granos", f"₡ {costo_total_fabricar:,.2f}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col_g2:
            st.markdown("<div class='farmer-card' style='border-left: 5px solid #9467bd;'>", unsafe_allow_html=True)
            st.markdown("####  OPCIÓN B: Comprar el alimento ya preparado")
            st.write(f"* **Costo por kilo comprado en veterinaria:** ₡ {precio_alimento_hecho_kg:.2f} el kg.")
            st.write("---")
            
            df_inv_hecho = pd.DataFrame({
                "Insumo / Concepto": ["Alimento Comercial Listo"],
                "Gasto al Mes (kg)": [alimento_meta_kg],
                "Traer por Camión (kg) [EOQ]": [q_optimo_comprar]
            })
            
            fila_total_hecho = pd.DataFrame({
                "Insumo / Concepto": ["TOTAL (Masa Bruta)"],
                "Gasto al Mes (kg)": [df_inv_hecho["Gasto al Mes (kg)"].sum()],
                "Traer por Camión (kg) [EOQ]": [df_inv_hecho["Traer por Camión (kg) [EOQ]"].sum()]
            })
            df_inv_hecho = pd.concat([df_inv_hecho, fila_total_hecho], ignore_index=True)
            
            st.dataframe(df_inv_hecho.style.format({
                "Gasto al Mes (kg)": "{:,.1f}", 
                "Traer por Camión (kg) [EOQ]": "{:,.1f}"
            }), hide_index=True)
            
            st.markdown("#####  Distribución Logística Comercial:")
            st.write(f"* **Consumo de la Granja:** Tus gallinas se comen **{alimento_meta_kg:,.1f} kg** al mes.")
            st.write(f"* **Pedido al Camión (EOQ):** Para ahorrar fletes, pides un flete con **{q_optimo_comprar:,.1f} kg** ({q_optimo_comprar/PESO_SACO:.0f} sacos) por viaje.")
            st.write(f"* **Frecuencia:** Llamas al camión de la veterinaria unas **{viajes_al_ano_comprar:.1f} veces al año**.")
            st.write(f"*  **Punto de Reorden (ROP):** Pide de nuevo cuando queden menos de **{rop_hecho:,.1f} kg** ({rop_hecho/PESO_SACO:.0f} sacos) en bodega.")
            
            st.metric(" Costo Mensual de Sacos Hechos", f"₡ {costo_total_comprar_hecho:,.2f}")
            st.markdown("</div>", unsafe_allow_html=True)
            
        st.subheader(" Veredicto Técnico: ¿Cuál camino le ahorra dinero?")
        diferencia_mensual = abs(costo_total_fabricar - costo_total_comprar_hecho)
        
        if costo_total_fabricar < costo_total_comprar_hecho:
            st.markdown(f"""
            <div class='success-card'>
             <b>Recomendación para la granja:</b> Le sale mucho mejor <b>FABRICAR SU PROPIO ALIMENTO</b>.<br>
            Se ahorra <b>₡ {diferencia_mensual:,.2f} al mes</b> utilizando fletes unificados de granos frente a la opción comercial de veterinaria.
            </div>
            """, unsafe_allow_html=True)
            costo_por_kg_elegido = precio_promedio_fabricado_kg
        else:
            st.markdown(f"""
            <div class='warning-card'>
             <b>Recomendación para la granja:</b> Le sale mejor <b>COMPRAR EL ALIMENTO YA HECHO</b>.<br>
            Se ahorra <b>₡ {diferencia_mensual:,.2f} al mes</b> porque la compra de granos sueltos resulta menos de un lote pequeño actualmente.
            </div>
            """, unsafe_allow_html=True)
            costo_por_kg_elegido = precio_alimento_hecho_kg

    except Exception as log_err:
        st.error(f"⚠️ Error en los cálculos de inventarios de transporte consolidado: {log_err}")
        st.stop()

    st.divider()

    # =====================================================================
    # SECCIÓN 5: SIMULACIÓN DE MONTE CARLO
    # =====================================================================
    st.header(" Análisis de Riesgo en el Tiempo (Simulación de Incertidumbre)")
    st.write("El sistema evalúa 10,000 meses simulados variando los precios del huevo y el clima para asegurar la rentabilidad del camino seleccionado.")
    
    try:
        n_simulaciones = 10000
        sim_precio_huevo = np.random.normal(loc=precio_huevo_unidad, scale=5.0, size=n_simulaciones)
        sim_consumo = np.random.uniform(low=consumo_diario_pronosticado - 0.006, high=consumo_diario_pronosticado + 0.006, size=n_simulaciones)
        sim_postura = np.random.normal(loc=porcentaje_puesta_pronosticado, scale=0.04, size=n_simulaciones)
        sim_postura = np.clip(sim_postura, 0.0, 1.0) 

        sim_ingresos_huevos = (aves * sim_postura * 30) * sim_precio_huevo
        sim_costo_alimento = (aves * sim_consumo * 30) * costo_por_kg_elegido
        sim_utilidad = sim_ingresos_huevos - sim_costo_alimento

        utilidad_media = np.mean(sim_utilidad)
        ic_inferior = np.percentile(sim_utilidad, 2.5)
        var_5 = np.percentile(sim_utilidad, 5)
        prob_fracaso = (np.sum(sim_utilidad <= 0) / n_simulaciones) * 100
        prob_exito = 100 - prob_fracaso

        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        with col_r1:
            st.metric(" Ganancia Mensual Promedio", f"₡ {utilidad_media:,.2f}")
            st.write("El dinero promedio libre estimado por mes.")
        with col_r2:
            st.metric(" Escenario Seguro Mínimo", f"₡ {ic_inferior:,.2f}")
            st.write("En un mes malo, esto es lo mínimo que ganaría.")
        with col_r3:
            st.metric(" Peor Caso Alerta (VaR 5%)", f"₡ {var_5:,.2f}")
            st.write("Hay solo 5% de riesgo de ganar menos de esto.")
        with col_r4:
            st.metric(" Probabilidad de Ganar Dinero", f"{prob_exito:.2f} %")
            st.metric(" Riesgo de Pérdida", f"{prob_fracaso:.2f} %", delta_color="inverse")

        st.subheader(" Gráficos de Riesgo del Negocio")
        col_plot1, col_plot2 = st.columns(2)
        
        with col_plot1:
            fig1, ax1 = plt.subplots(figsize=(6, 3.8))
            ax1.hist(sim_utilidad, bins=50, color='skyblue', edgecolor='black', alpha=0.7, density=False)
            ax1.axvline(utilidad_media, color='blue', linestyle='-', linewidth=2, label=f'Ganancia Promedio')
            ax1.axvline(0, color='red', linestyle='--', linewidth=2, label='Línea de Pérdida (₡ 0)')
            ax1.set_title("¿Qué tan seguido se repiten las ganancias simuladas?")
            ax1.set_xlabel("Ganancia Neta Libre del Mes (₡)")
            ax1.set_ylabel("Número de simulaciones")
            ax1.legend(prop={'size': 8})
            st.pyplot(fig1)
            plt.close(fig1)
            
        with col_plot2:
            fig2, ax2 = plt.subplots(figsize=(6, 3.8))
            valores_ordenados = np.sort(sim_utilidad)
            prob_acumulada = np.arange(1, n_simulaciones + 1) / n_simulaciones
            ax2.plot(valores_ordenados, prob_acumulada, color='darkorange', linewidth=2, label='Línea de Riesgo')
            ax2.axvline(0, color='red', linestyle='--', linewidth=2, label='Punto de Quiebra (₡ 0)')
            ax2.set_title("Probabilidad de Alcanzar Metas de Ganancia")
            ax2.set_xlabel("Ganancia Neta Libre del Mes (₡)")
            ax2.set_ylabel("Probabilidad de Lograrlo")
            ax2.legend(prop={'size': 8})
            ax2.grid(True, alpha=0.3)
            st.pyplot(fig2)
            plt.close(fig2)

        # =================================================================
        # SECCIÓN 5.1 — SUGERENCIA SEGÚN LOS RESULTADOS DE MONTE CARLO
        # =================================================================
        # Mismo estilo que categoria_texto de la Sección 2: un texto corto
        # que se calcula con if/elif a partir de los números que YA arrojó
        # la simulación (prob_fracaso, ic_inferior, var_5, utilidad_media).
        # No cambia ningún cálculo anterior, solo interpreta el resultado.
        if prob_fracaso >= 15.0:
            sugerencia_texto = "Riesgo Alto: Replantear la Decisión"
            sugerencia_detalle = (
                f"Con la decisión actual hay **{prob_fracaso:.1f}% de probabilidad de perder dinero** en un mes cualquiera. "
                f"Esto es un riesgo considerable: conviene revisar el precio de venta del huevo, buscar reducir el costo "
                f"del alimento elegido, o tener un fondo de reserva antes de seguir adelante."
            )
        elif prob_fracaso >= 5.0:
            sugerencia_texto = "Riesgo Moderado: Mantener Vigilancia"
            sugerencia_detalle = (
                f"La decisión actual es rentable en promedio, pero igual existe un **{prob_fracaso:.1f}% de probabilidad de pérdida** "
                f"en algún mes. Se recomienda guardar parte de la ganancia de los meses buenos como colchón para los meses malos."
            )
        elif ic_inferior < (utilidad_media * 0.5):
            sugerencia_texto = "Riesgo Bajo, pero Resultado Variable"
            sugerencia_detalle = (
                f"El riesgo de pérdida es bajo ({prob_fracaso:.1f}%), pero la ganancia varía bastante de un mes a otro: "
                f"en un mes malo (escenario seguro al 95%) podría caer hasta ₡ {ic_inferior:,.2f}, "
                f"muy por debajo del promedio de ₡ {utilidad_media:,.2f}. Conviene no comprometer toda la ganancia mensual en gastos fijos."
            )
        else:
            sugerencia_texto = "Decisión Sólida y Estable"
            sugerencia_detalle = (
                f"La decisión actual tiene bajo riesgo de pérdida ({prob_fracaso:.1f}%) y un resultado bastante estable mes a mes. "
                f"La simulación respalda mantener el camino elegido sin cambios."
            )

        st.info(f" **Sugerencia según Monte Carlo:** {sugerencia_texto}")
        st.write(sugerencia_detalle)

        
    except Exception as sim_err:
        st.error(f"⚠️ Error en la simulación de Monte Carlo: {sim_err}")

else:
    st.error("❌ COMBINACIÓN DE GRANOS IMPOSIBLE")
    st.markdown("Los requerimientos de nutrición para la edad de estas gallinas no se pueden cumplir con los precios o límites actuales.")
