import streamlit as st
import numpy as np
import pulp           # Librería de programación lineal (Linear Programming) usada para optimizar la mezcla de alimento
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================================
# CONFIGURACIÓN DE LA PÁGINA Y ESTILOS VISUALES 
# =====================================================================

# Configura las propiedades generales de la pestaña/página de la app
# (título que aparece en el navegador, icono y diseño de ancho completo)
st.set_page_config(
    page_title="Asistente de Decisiones Avícolas - UCR",
    page_icon="🐔",
    layout="wide"
)

# Constante comercial de empaque en Costa Rica
# Se usa para convertir kilogramos a "sacos" (unidad comercial estándar de 46 kg)
PESO_SACO = 46.0

# Estilos CSS personalizados para mantener la app visual, ordenada y clara
# Se inyectan directamente como HTML/CSS dentro de Streamlit mediante st.markdown
st.markdown("""
    <style>
    .big-font { font-size:20px !important; font-weight: bold; color: #1f77b4; }
    .farmer-card { background-color: #f7f9fa; padding: 15px; border-radius: 10px; border-left: 5px solid #ffc107; margin-bottom: 10px; }
    .success-card { background-color: #f0f7f4; padding: 15px; border-radius: 10px; border-left: 5px solid #2e7d32; margin-bottom: 10px; }
    .warning-card { background-color: #fffde7; padding: 15px; border-radius: 10px; border-left: 5px solid #fbc02d; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Título principal y subtítulo de la aplicación
st.title("Asistente de Decisiones Avícolas")
st.markdown("### **Calculadora Inteligente de Costos y Riesgos para la Granja**")
st.divider()

# =====================================================================
# SECCIÓN 1: PANEL LATERAL - ENTRADAS PARAMÉTRICAS
# =====================================================================
# Todo este bloque construye el sidebar (barra lateral) donde el usuario
# ingresa los datos de su granja: tipo de ave, cantidad, edad, precios, etc.

st.sidebar.header(" 1. Datos de las Gallinas")
# Selector de la raza/línea genética de las gallinas (afecta consumo de alimento)
tipo_ave = st.sidebar.selectbox("Raza o línea de las aves:", ["Ponedora Rubia (Pesada)", "Ponedora Blanca (Ligera)"])
# Número total de gallinas en la granja
aves = st.sidebar.number_input("¿Cuántas gallinas tiene en total?:", min_value=100, max_value=50000, value=1200, step=100)
# Edad de las gallinas en semanas, determina la etapa productiva (cría, desarrollo, producción)
edad = st.sidebar.slider("Edad de las gallinas (Semanas):", min_value=1.0, max_value=80.0, value=35.0, step=1.0)

st.sidebar.divider()
st.sidebar.header(" 2. Precio de los Granos (Sueltos)")
# Precios unitarios de las materias primas que se usarían si se fabrica el alimento en la granja
p_maiz = st.sidebar.number_input("Precio del Kilo de Maíz Amarillo (₡/kg):", min_value=1.0, value=215.0, step=5.0)
p_soya = st.sidebar.number_input("Precio del Kilo de Harina de Soya (₡/kg):", min_value=1.0, value=405.0, step=5.0)
p_caliza = st.sidebar.number_input("Precio del Kilo de Caliza Molida (₡/kg):", min_value=1.0, value=80.0, step=5.0)

st.sidebar.divider()
st.sidebar.header(" 3. Opción Alternativa: Comprar Alimento Hecho")
# Precio del alimento balanceado ya preparado, vendido por saco de 46 kg
precio_alimento_hecho_saco = st.sidebar.number_input("Precio de 1 SACO de alimento ya preparado (₡ por saco de 46kg):", min_value=1.0, value=12000.0, step=100.0)
# Se convierte el precio por saco a precio por kilogramo para poder comparar contra los granos sueltos
precio_alimento_hecho_kg = precio_alimento_hecho_saco / PESO_SACO

st.sidebar.divider()
st.sidebar.header(" 4. Gastos de Camión y Bodega Unificados")
# Costo fijo de cada viaje de transporte (flete), independiente de cuánto se traiga
costo_flete_viaje = st.sidebar.number_input("Costo de un viaje de camión a la granja (₡ por flete):", min_value=0.0, value=22000.0, step=500.0)
# Tiempo de espera (lead time) entre que se hace el pedido y llega el camión
dias_entrega = st.sidebar.number_input("¿Cuántos días tarda el proveedor en entregar? (Días):", min_value=1, max_value=15, value=3, step=1)
# Porcentaje anual del valor del inventario que representa el costo de almacenarlo (bodega, mermas, etc.)
# Se divide entre 100 para convertir el slider (en %) a una proporción decimal
porcentaje_bodega = st.sidebar.slider("Gasto estimado de mantener la bodega al año (% del valor del producto):", min_value=5, max_value=40, value=15, step=1) / 100.0

st.sidebar.divider()
st.sidebar.header(" 5. Mercado del Huevo")
# Precio de venta de cada huevo, usado para estimar ingresos
precio_huevo_unidad = st.sidebar.number_input("Precio al que vende cada huevo en la zona (₡):", min_value=1.0, value=85.0, step=5.0)

# =====================================================================
# SECCIÓN 2: ÁREA DE DATOS — PRONÓSTICO Y REQUERIMIENTOS POR EDAD
# =====================================================================
# Aquí se calculan, según la edad y tipo de ave, los valores biológicos esperados:
# consumo diario de alimento, requerimientos nutricionales (proteína/calcio)
# y porcentaje de postura (cuántas gallinas ponen huevo en promedio).

# Valores por defecto (se sobrescriben más abajo según la edad real)
consumo_diario_pronosticado = 0.115
req_proteina = 0.165
req_calcio = 0.0375
porcentaje_puesta_pronosticado = 0.0
categoria_texto = "No especificada"

try:
    if edad < 18.0:
        # Antes de las 18 semanas las gallinas todavía no ponen huevos (etapa de cría/desarrollo)
        etapa_productiva = "Pollita en Crecimiento (No pone huevos)"
        porcentaje_puesta_pronosticado = 0.0
        if edad <= 5.0:
            # Fase inicial (pollita bebé): consumo crece linealmente con la edad, mayor requerimiento de proteína
            consumo_diario_pronosticado = (0.0038 * edad) + 0.002
            req_proteina = 0.185  
            req_calcio = 0.0100   
            categoria_texto = "Pollita Bebé (Fase Inicial)"
        else:
            # Fase de desarrollo: consumo crece a otra tasa, requerimientos nutricionales menores
            consumo_diario_pronosticado = (0.0025 * edad) + 0.009
            req_proteina = 0.160  
            req_calcio = 0.0090   
            categoria_texto = "Pollita en Desarrollo"
    else:
        # A partir de las 18 semanas la gallina entra en etapa productiva (pone huevos)
        etapa_productiva = "Gallina en Producción de Huevos"
        if tipo_ave == "Ponedora Blanca (Línea Ligera)":
            # Nota: esta comparación nunca es verdadera porque el selectbox usa el texto
            # "Ponedora Blanca (Ligera)" (sin la palabra "Línea"), así que esta rama
            # de la línea ligera nunca se ejecuta tal como está escrito el código.
            consumo_diario_pronosticado = 0.100
        else:
            consumo_diario_pronosticado = 0.115
            
        if edad < 50.0:
            # Gallina joven: mayor requerimiento de proteína, menor de calcio
            req_proteina = 0.165  
            req_calcio = 0.0375   
            categoria_texto = "Gallina Joven (Alta producción de huevos)"
        else:
            # Gallina madura: menos proteína, más calcio (cáscara más gruesa necesaria)
            req_proteina = 0.158  
            req_calcio = 0.0390   
            categoria_texto = "Gallina Madura (Necesita más calcio)"

        # Curva de postura (% de gallinas que ponen huevo) en tres tramos según la edad:
        if edad < 22.0:
            # Tramo de arranque: la postura sube progresivamente desde 0%
            porcentaje_puesta_pronosticado = max(0.0, (0.15 * (edad - 18.0)))
        elif edad <= 35.0:
            # Tramo de pico productivo: sube hasta un máximo de 94%
            porcentaje_puesta_pronosticado = min(0.94, 0.85 + (0.006 * (edad - 22.0)))
        else:
            # Tramo de declive: la postura baja gradualmente pero no por debajo de 65%
            porcentaje_puesta_pronosticado = max(0.65, 0.94 - (0.0045 * (edad - 35.0)))

    # Meta de alimento mensual = consumo diario por ave * número de aves * 30 días
    alimento_meta_kg = aves * consumo_diario_pronosticado * 30
    # Estimación de huevos producidos por día y por mes según el % de postura
    huevos_diarios_estimados = aves * porcentaje_puesta_pronosticado
    huevos_mensuales_estimados = huevos_diarios_estimados * 30
    # Cartones de 30 huevos producidos "por día equivalente" (huevos mensuales / 30)
    cartones_mensuales = huevos_mensuales_estimados / 30

except Exception as e:
    # Si algo falla en los cálculos de pronóstico, se muestra el error y se detiene la app
    st.error(f"❌ Error al calcular los datos de las aves: {e}")
    st.stop()

# --- Presentación visual del resumen operativo calculado arriba ---
st.header(" Resumen Operativo de la Finca (Pronósticos)")
st.info(f" **Situación de las aves:** Etapa actual: **{categoria_texto}**")

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    # Tarjeta con el consumo diario por gallina (convertido a gramos) y el total mensual en kg/sacos
    st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
    st.metric(" Consumo por Gallina al Día", f"{consumo_diario_pronosticado * 1000:.0f} gramos")
    st.write(f"**Comida necesaria al mes:** {alimento_meta_kg:,.1f} kg")
    st.write(f"Equivale a unos **{alimento_meta_kg/PESO_SACO:,.0f} sacos** al mes.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_f2:
    # Tarjeta con el porcentaje de postura estimado
    st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
    st.metric(" Porcentaje de Postura", f"{porcentaje_puesta_pronosticado * 100:.1f} %")
    st.markdown("</div>", unsafe_allow_html=True)

with col_f3:
    # Tarjeta con la producción mensual estimada en cartones y el ingreso bruto esperado
    st.markdown("<div class='farmer-card'>", unsafe_allow_html=True)
    st.metric(" Producción Mensual Estimada", f"{cartones_mensuales:,.0f} Cartones (de 30 h.)")
    ingreso_estimado = huevos_mensuales_estimados * precio_huevo_unidad
    st.write(f"**Venta bruta estimada al mes:** ₡ {ingreso_estimado:,.2f}")
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# =====================================================================
# SECCIÓN 3: ÁREA DE OPTIMIZACIÓN — PROGRAMACIÓN LINEAL INTERNA
# =====================================================================
# Se resuelve un problema de programación lineal (con PuLP) para encontrar
# la mezcla de Maíz + Soya + Caliza de MENOR COSTO que cumpla con los
# requerimientos nutricionales y la meta total de alimento del mes.

es_factible = False
try:
    # Problema de minimización: minimizar el costo total de la mezcla
    prob = pulp.LpProblem("Mezcla_Costo_Minimo", pulp.LpMinimize)
    # Variables de decisión: cantidad en kg de cada ingrediente (no pueden ser negativas)
    x1 = pulp.LpVariable("Maiz", lowBound=0)
    x2 = pulp.LpVariable("Soya", lowBound=0)
    x3 = pulp.LpVariable("Caliza", lowBound=0)

    # Función objetivo: costo total = suma de (cantidad * precio) de cada ingrediente
    prob += (x1 * p_maiz + x2 * p_soya + x3 * p_caliza)

    # Restricción 1: la suma de los tres ingredientes debe ser exactamente igual
    # a la meta de alimento mensual calculada en la Sección 2
    prob += x1 + x2 + x3 == alimento_meta_kg                                           
    # Restricción 2: el aporte de proteína (maíz aporta 8.5%, soya aporta 44%)
    # debe ser al menos el requerimiento de proteína total de la mezcla
    prob += 0.085 * x1 + 0.440 * x2 >= (alimento_meta_kg * req_proteina)               
    # Restricción 3: el aporte de calcio (maíz, soya y caliza aportan distintas proporciones)
    # debe ser al menos el requerimiento de calcio total de la mezcla
    prob += 0.0002 * x1 + 0.0025 * x2 + 0.3800 * x3 >= (alimento_meta_kg * req_calcio) 
    # Restricción 4: el maíz debe representar como mínimo el 55% de la mezcla total
    # (restricción práctica/comercial de formulación)
    prob += x1 >= 0.55 * alimento_meta_kg                                              

    # Se resuelve el problema usando el solver CBC (msg=False para no imprimir logs en consola)
    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    # Se verifica si el solver encontró una solución óptima (factible)
    es_factible = pulp.LpStatus[status] == "Optimal"

except Exception as e:
    st.error(f"❌ Error en el cálculo de programación lineal: {e}")

# =====================================================================
# SECCIÓN 4: MODELO DE INVENTARIO CONTRATADO / UNIFICADO (EOQ Y ROP)
# =====================================================================
# Si la mezcla óptima es factible, se calculan dos planes logísticos comparables:
#   Plan A: fabricar el alimento en la granja comprando los 3 insumos por separado
#   Plan B: comprar el alimento balanceado ya hecho
# Para cada plan se calcula el Lote Económico de Pedido (EOQ) y el Punto de Reorden (ROP).
if es_factible:
    try:
        # Cantidades óptimas (en kg) resueltas por el modelo de programación lineal
        kg_maiz = x1.varValue
        kg_soya = x2.varValue
        kg_caliza = x3.varValue
        # Costo total mensual de fabricar la mezcla (valor de la función objetivo)
        costo_total_fabricar = pulp.value(prob.objective)
        # Costo promedio por kg de la mezcla fabricada
        precio_promedio_fabricado_kg = costo_total_fabricar / alimento_meta_kg
        
        # Proporción (peso relativo) de cada ingrediente dentro de la mezcla total
        proporcion_maiz = kg_maiz / alimento_meta_kg
        proporcion_soya = kg_soya / alimento_meta_kg
        proporcion_caliza = kg_caliza / alimento_meta_kg
        
        # Demanda anual total de alimento (kg/mes * 12 meses) y demanda diaria promedio
        demanda_anual_total = alimento_meta_kg * 12
        demanda_diaria_total = alimento_meta_kg / 30
        # Colchón de seguridad: stock adicional para cubrir 1.5 días de consumo ante imprevistos
        colchon_seguridad_total = demanda_diaria_total * 1.5

        # ---------------- PLAN A: LOGÍSTICA CONSOLIDADA DE MATERIAS PRIMAS ----------------
        # Precio promedio ponderado por kg de la mezcla (usado para el costo de mantener inventario)
        precio_ponderado_mezcla_kg = (proporcion_maiz * p_maiz) + (proporcion_soya * p_soya) + (proporcion_caliza * p_caliza)
        # Costo anual de mantener (almacenar) 1 kg de la mezcla en bodega
        h_ponderado_mezcla = precio_ponderado_mezcla_kg * porcentaje_bodega

        # Fórmula clásica de EOQ (Lote Económico de Pedido): Q* = sqrt(2 * D * S / H)
        # D = demanda anual, S = costo de ordenar/flete, H = costo de mantener inventario por unidad
        q_grupo_total_kg = np.sqrt((2 * demanda_anual_total * costo_flete_viaje) / h_ponderado_mezcla) if h_ponderado_mezcla > 0 else 0
        # Número de viajes de camión al año necesarios para cubrir la demanda anual con ese lote
        viajes_al_ano_fabricar = demanda_anual_total / q_grupo_total_kg if q_grupo_total_kg > 0 else 0
        
        # Se reparte el lote óptimo total (q_grupo_total_kg) entre los 3 insumos según su proporción en la mezcla
        q_maiz_viaje = q_grupo_total_kg * proporcion_maiz
        q_soya_viaje = q_grupo_total_kg * proporcion_soya
        q_caliza_viaje = q_grupo_total_kg * proporcion_caliza

        # Punto de Reorden (ROP) = demanda durante el tiempo de entrega + colchón de seguridad
        rop_grupo_total = (demanda_diaria_total * dias_entrega) + colchon_seguridad_total

        # ---------------- PLAN B: LOGÍSTICA DE ALIMENTO COMERCIAL TERMINADO ----------------
        # Costo total mensual de comprar todo el alimento ya preparado
        costo_total_comprar_hecho = alimento_meta_kg * precio_alimento_hecho_kg
        # Costo anual de mantener 1 kg de alimento comercial en bodega
        costo_almacenar_hecho_anual = precio_alimento_hecho_kg * porcentaje_bodega
        
        # EOQ para el alimento comercial (misma fórmula que en el Plan A)
        q_optimo_comprar = np.sqrt((2 * demanda_anual_total * costo_flete_viaje) / costo_almacenar_hecho_anual)
        # Viajes de camión al año necesarios para el alimento comercial
        viajes_al_ano_comprar = demanda_anual_total / q_optimo_comprar
        # ROP para el alimento comercial (misma lógica que el Plan A)
        rop_hecho = (demanda_diaria_total * dias_entrega) + colchon_seguridad_total

        # ---------------- PRESENTACIÓN EN PARALELO COMPARATIVA ----------------
        st.header(" Análisis de Costos e Inventario Unificado")
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # --- Columna izquierda: detalle del Plan A (fabricar en la granja) ---
            st.markdown("<div class='farmer-card' style='border-left: 5px solid #1f77b4;'>", unsafe_allow_html=True)
            st.markdown("####  OPCIÓN A: Fabricar el alimento en la granja")
            st.write(f"* **Costo de los granos por kilo mezclado:** ₡ {precio_promedio_fabricado_kg:.2f} el kg.")
            st.write("---")
            
            # Tabla con el detalle de consumo mensual y cantidad a pedir por camión (EOQ) de cada insumo
            df_inv_mp = pd.DataFrame({
                "Insumo / Concepto": ["Maíz Amarillo", "Harina de Soya", "Caliza Molida"],
                "Gasto al Mes (kg)": [kg_maiz, kg_soya, kg_caliza],
                "Traer por Camión (kg) [EOQ]": [q_maiz_viaje, q_soya_viaje, q_caliza_viaje]
            })
            
            # Se agrega una fila de totales al final de la tabla, para evitar confusiones al sumar manualmente
            fila_total_mp = pd.DataFrame({
                "Insumo / Concepto": ["TOTAL (Masa Bruta)"],
                "Gasto al Mes (kg)": [df_inv_mp["Gasto al Mes (kg)"].sum()],
                "Traer por Camión (kg) [EOQ]": [df_inv_mp["Traer por Camión (kg) [EOQ]"].sum()]
            })
            df_inv_mp = pd.concat([df_inv_mp, fila_total_mp], ignore_index=True)
            
            # Se muestra la tabla con formato de número (1 decimal, separador de miles) y sin índice
            st.dataframe(df_inv_mp.style.format({
                "Gasto al Mes (kg)": "{:,.1f}", 
                "Traer por Camión (kg) [EOQ]": "{:,.1f}"
            }), hide_index=True)
            
            # Texto explicativo en lenguaje sencillo de la logística calculada (EOQ, frecuencia, ROP)
            st.markdown("#####  Distribución Logística Inteligente:")
            st.write(f"* **Consumo de la Granja:** Tus gallinas se comen **{alimento_meta_kg:,.1f} kg** al mes.")
            st.write(f"* **Pedido al Camión (EOQ):** Para ahorrar fletes, pides un camión consolidado con **{q_grupo_total_kg:,.1f} kg** totales por viaje.")
            st.write(f"* **Frecuencia:** Llamas al camión de granos unas **{viajes_al_ano_fabricar:.1f} veces al año**.")
            st.write(f"*  **Punto de Reorden (ROP):** Pide de nuevo cuando queden menos de **{rop_grupo_total:,.1f} kg** en tu bodega.")
            
            # Costo mensual total de fabricar el alimento (granos sueltos)
            st.metric(" Costo Mensual de Granos", f"₡ {costo_total_fabricar:,.2f}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col_g2:
            # --- Columna derecha: detalle del Plan B (comprar alimento ya hecho) ---
            st.markdown("<div class='farmer-card' style='border-left: 5px solid #9467bd;'>", unsafe_allow_html=True)
            st.markdown("####  OPCIÓN B: Comprar el alimento ya preparado")
            st.write(f"* **Costo por kilo comprado en veterinaria:** ₡ {precio_alimento_hecho_kg:.2f} el kg.")
            st.write("---")
            
            # Tabla con el consumo mensual y el EOQ del alimento comercial (un solo "insumo")
            df_inv_hecho = pd.DataFrame({
                "Insumo / Concepto": ["Alimento Comercial Listo"],
                "Gasto al Mes (kg)": [alimento_meta_kg],
                "Traer por Camión (kg) [EOQ]": [q_optimo_comprar]
            })
            
            # Fila de totales (en este caso coincide con la única fila, pero se mantiene la misma estructura que el Plan A)
            fila_total_hecho = pd.DataFrame({
                "Insumo / Concepto": ["TOTAL (Masa Bruta)"],
                "Gasto al Mes (kg)": [df_inv_hecho["Gasto al Mes (kg)"].sum()],
                "Traer por Camión (kg) [EOQ]": [df_inv_hecho["Traer por Camión (kg) [EOQ]"].sum()]
            })
            df_inv_hecho = pd.concat([df_inv_hecho, fila_total_hecho], ignore_index=True)
            
            # Se muestra la tabla con el mismo formato numérico que la del Plan A
            st.dataframe(df_inv_hecho.style.format({
                "Gasto al Mes (kg)": "{:,.1f}", 
                "Traer por Camión (kg) [EOQ]": "{:,.1f}"
            }), hide_index=True)
            
            # Texto explicativo de la logística del alimento comercial (EOQ en sacos, frecuencia, ROP)
            st.markdown("#####  Distribución Logística Comercial:")
            st.write(f"* **Consumo de la Granja:** Tus gallinas se comen **{alimento_meta_kg:,.1f} kg** al mes.")
            st.write(f"* **Pedido al Camión (EOQ):** Para ahorrar fletes, pides un flete con **{q_optimo_comprar:,.1f} kg** ({q_optimo_comprar/PESO_SACO:.0f} sacos) por viaje.")
            st.write(f"* **Frecuencia:** Llamas al camión de la veterinaria unas **{viajes_al_ano_comprar:.1f} veces al año**.")
            st.write(f"*  **Punto de Reorden (ROP):** Pide de nuevo cuando queden menos de **{rop_hecho:,.1f} kg** ({rop_hecho/PESO_SACO:.0f} sacos) en bodega.")
            
            # Costo mensual total de comprar el alimento ya preparado
            st.metric(" Costo Mensual de Sacos Hechos", f"₡ {costo_total_comprar_hecho:,.2f}")
            st.markdown("</div>", unsafe_allow_html=True)
            
        # ---------------- VEREDICTO: comparación final entre Plan A y Plan B ----------------
        st.subheader(" Veredicto Técnico: ¿Cuál camino le ahorra dinero?")
        # Diferencia absoluta de costo mensual entre ambas opciones
        diferencia_mensual = abs(costo_total_fabricar - costo_total_comprar_hecho)
        
        if costo_total_fabricar < costo_total_comprar_hecho:
            # Caso 1: fabricar es más barato que comprar el alimento hecho
            st.markdown(f"""
            <div class='success-card'>
             <b>Recomendación para la granja:</b> Le sale mucho mejor <b>FABRICAR SU PROPIO ALIMENTO</b>.<br>
            Se ahorra <b>₡ {diferencia_mensual:,.2f} al mes</b> utilizando fletes unificados de granos frente a la opción comercial de veterinaria.
            </div>
            """, unsafe_allow_html=True)
            # Se guarda el costo por kg de la opción elegida (fabricar) para usarlo después en la simulación de Monte Carlo
            costo_por_kg_elegido = precio_promedio_fabricado_kg
        else:
            # Caso 2: comprar el alimento ya hecho resulta más barato
            st.markdown(f"""
            <div class='warning-card'>
             <b>Recomendación para la granja:</b> Le sale mejor <b>COMPRAR EL ALIMENTO YA HECHO</b>.<br>
            Se ahorra <b>₡ {diferencia_mensual:,.2f} al mes</b> porque la compra de granos sueltos resulta menos de un lote pequeño actualmente.
            </div>
            """, unsafe_allow_html=True)
            # Se guarda el costo por kg de la opción elegida (comprar) para usarlo después en la simulación de Monte Carlo
            costo_por_kg_elegido = precio_alimento_hecho_kg

    except Exception as log_err:
        st.error(f"⚠️ Error en los cálculos de inventarios de transporte consolidado: {log_err}")
        st.stop()

    st.divider()

    # =====================================================================
    # SECCIÓN 5: SIMULACIÓN DE MONTE CARLO
    # =====================================================================
    # Se simulan 10,000 meses "aleatorios" variando el precio del huevo, el consumo
    # de alimento y el porcentaje de postura, para estimar la distribución de
    # utilidades posibles y el riesgo de pérdida del plan elegido (A o B).
    st.header(" Análisis de Riesgo en el Tiempo (Simulación de Incertidumbre)")
    st.write("El sistema evalúa 10,000 meses simulados variando los precios del huevo y el clima para asegurar la rentabilidad del camino seleccionado.")
    
    try:
        n_simulaciones = 10000
        # Precio del huevo simulado: distribución normal centrada en el precio ingresado, con desviación de ₡5
        sim_precio_huevo = np.random.normal(loc=precio_huevo_unidad, scale=5.0, size=n_simulaciones)
        # Consumo diario simulado: distribución uniforme entre -6 g y +6 g del valor pronosticado
        sim_consumo = np.random.uniform(low=consumo_diario_pronosticado - 0.006, high=consumo_diario_pronosticado + 0.006, size=n_simulaciones)
        # Porcentaje de postura simulado: distribución normal centrada en el valor pronosticado, con desviación de 4 puntos porcentuales
        sim_postura = np.random.normal(loc=porcentaje_puesta_pronosticado, scale=0.04, size=n_simulaciones)
        # Se recorta (clip) el porcentaje de postura para que quede siempre entre 0% y 100%
        sim_postura = np.clip(sim_postura, 0.0, 1.0) 

        # Ingresos simulados por venta de huevos = (aves * % postura simulada * 30 días) * precio simulado
        sim_ingresos_huevos = (aves * sim_postura * 30) * sim_precio_huevo
        # Costo simulado de alimento = (aves * consumo simulado * 30 días) * costo por kg de la opción elegida
        sim_costo_alimento = (aves * sim_consumo * 30) * costo_por_kg_elegido
        # Utilidad simulada de cada uno de los 10,000 meses
        sim_utilidad = sim_ingresos_huevos - sim_costo_alimento

        # Estadísticas resumen de la distribución de utilidades simuladas
        utilidad_media = np.mean(sim_utilidad)
        # Percentil 2.5%: límite inferior de un intervalo de confianza del 95% ("escenario seguro mínimo")
        ic_inferior = np.percentile(sim_utilidad, 2.5)
        # Percentil 5%: Valor en Riesgo (VaR) al 5%, peor caso razonable
        var_5 = np.percentile(sim_utilidad, 5)
        # Probabilidad de pérdida = % de simulaciones donde la utilidad fue cero o negativa
        prob_fracaso = (np.sum(sim_utilidad <= 0) / n_simulaciones) * 100
        # Probabilidad de éxito (complemento de la probabilidad de fracaso)
        prob_exito = 100 - prob_fracaso

        # --- Tarjetas con las métricas de riesgo calculadas arriba ---
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

        # --- Gráficos de la distribución de utilidades simuladas ---
        st.subheader(" Gráficos de Riesgo del Negocio")
        col_plot1, col_plot2 = st.columns(2)
        
        with col_plot1:
            # Histograma: frecuencia con la que se repiten distintos niveles de ganancia simulada
            fig1, ax1 = plt.subplots(figsize=(6, 3.8))
            ax1.hist(sim_utilidad, bins=50, color='skyblue', edgecolor='black', alpha=0.7, density=False)
            ax1.axvline(utilidad_media, color='blue', linestyle='-', linewidth=2, label=f'Ganancia Promedio')
            ax1.axvline(0, color='red', linestyle='--', linewidth=2, label='Línea de Pérdida (₡ 0)')
            ax1.set_title("¿Qué tan seguido se repiten las ganancias simuladas?")
            ax1.set_xlabel("Ganancia Neta Libre del Mes (₡)")
            ax1.set_ylabel("Número de simulaciones")
            ax1.legend(prop={'size': 8})
            st.pyplot(fig1)
            plt.close(fig1)  # Se cierra la figura para liberar memoria y evitar que Streamlit la reutilice por error
            
        with col_plot2:
            # Curva de probabilidad acumulada (CDF empírica): probabilidad de obtener al menos cierta ganancia
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
            plt.close(fig2)  # Se cierra la figura para liberar memoria

        # =================================================================
        # SECCIÓN 5.1 — SUGERENCIA SEGÚN LOS RESULTADOS DE MONTE CARLO
        # =================================================================
        # Mismo estilo que categoria_texto de la Sección 2: un texto corto
        # que se calcula con if/elif a partir de los números que YA arrojó
        # la simulación (prob_fracaso, ic_inferior, var_5, utilidad_media).
        # No cambia ningún cálculo anterior, solo interpreta el resultado.
        if prob_fracaso >= 15.0:
            # Riesgo alto: más del 15% de probabilidad de terminar el mes en pérdida
            sugerencia_texto = "Riesgo Alto: Replantear la Decisión"
            sugerencia_detalle = (
                f"Con la decisión actual hay **{prob_fracaso:.1f}% de probabilidad de perder dinero** en un mes cualquiera. "
                f"Esto es un riesgo considerable: conviene revisar el precio de venta del huevo, buscar reducir el costo "
                f"del alimento elegido, o tener un fondo de reserva antes de seguir adelante."
            )
        elif prob_fracaso >= 5.0:
            # Riesgo moderado: entre 5% y 15% de probabilidad de pérdida
            sugerencia_texto = "Riesgo Moderado: Mantener Vigilancia"
            sugerencia_detalle = (
                f"La decisión actual es rentable en promedio, pero igual existe un **{prob_fracaso:.1f}% de probabilidad de pérdida** "
                f"en algún mes. Se recomienda guardar parte de la ganancia de los meses buenos como colchón para los meses malos."
            )
        elif ic_inferior < (utilidad_media * 0.5):
            # Riesgo de pérdida bajo, pero el escenario seguro (percentil 2.5%) cae a menos de la mitad del promedio:
            # la ganancia es muy variable de un mes a otro aunque casi nunca se pierda dinero
            sugerencia_texto = "Riesgo Bajo, pero Resultado Variable"
            sugerencia_detalle = (
                f"El riesgo de pérdida es bajo ({prob_fracaso:.1f}%), pero la ganancia varía bastante de un mes a otro: "
                f"en un mes malo (escenario seguro al 95%) podría caer hasta ₡ {ic_inferior:,.2f}, "
                f"muy por debajo del promedio de ₡ {utilidad_media:,.2f}. Conviene no comprometer toda la ganancia mensual en gastos fijos."
            )
        else:
            # Caso ideal: bajo riesgo de pérdida y resultados estables mes a mes
            sugerencia_texto = "Decisión Sólida y Estable"
            sugerencia_detalle = (
                f"La decisión actual tiene bajo riesgo de pérdida ({prob_fracaso:.1f}%) y un resultado bastante estable mes a mes. "
                f"La simulación respalda mantener el camino elegido sin cambios."
            )

        # Se muestra la sugerencia final calculada según el escenario de riesgo detectado
        st.info(f" **Sugerencia según Monte Carlo:** {sugerencia_texto}")
        st.write(sugerencia_detalle)

        
    except Exception as sim_err:
        st.error(f"⚠️ Error en la simulación de Monte Carlo: {sim_err}")

else:
    # Si el modelo de programación lineal (Sección 3) no encontró solución factible,
    # significa que con los precios/restricciones actuales no se puede armar una mezcla
    # que cumpla los requerimientos nutricionales de las gallinas según su edad.
    st.error("❌ COMBINACIÓN DE GRANOS IMPOSIBLE")
    st.markdown("Los requerimientos de nutrición para la edad de estas gallinas no se pueden cumplir con los precios o límites actuales.")