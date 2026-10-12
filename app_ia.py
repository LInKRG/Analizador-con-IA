import json
import time
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types
from io import BytesIO

# Configuración inicial de la página
st.set_page_config(
    page_title="Analizador Inteligente de Datos con IA",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 Analizador & Clasificador de Textos con IA")
st.write(
    "Sube una planilla de Excel que contenga una columna con comentarios, reseñas o tickets de soporte. "
    "La Inteligencia Artificial analizará cada fila, clasificará el sentimiento y la categoría, "
    "y te generará un reporte listo para descargar."
)

# ---------------------------------------------------------
# 1. BARRA LATERAL: Configuración de la API Key
# ---------------------------------------------------------
st.sidebar.header("⚙️ Configuración")
api_key_ingresada = st.sidebar.text_input(
    "Ingresa tu Gemini API Key:", 
    type="password",
    help="Tu clave se usa solo durante la sesión y no se almacena."
)

st.sidebar.markdown("---")
st.sidebar.info(
    "**Cómo usar esta app:**\n"
    "1. Asegúrate de que tu Excel tenga una columna con texto (ej: comentarios, feedback).\n"
    "2. Ingresa tu API Key de Gemini en la barra lateral.\n"
    "3. Sube el archivo, selecciona la columna a analizar y presiona 'Procesar'."
)

# ---------------------------------------------------------
# 2. SUBIDA DE ARCHIVO EXCEL / CSV
# ---------------------------------------------------------
archivo_subido = st.file_uploader("Sube tu archivo de datos (.xlsx o .csv)", type=["xlsx", "csv"])

if archivo_subido is not None:
    try:
        # Cargar datos dinámicamente
        if archivo_subido.name.endswith('.csv'):
            df = pd.read_csv(archivo_subido)
        else:
            df = pd.read_excel(archivo_subido)
            
        st.subheader("📋 Vista Previa de los Datos:")
        st.dataframe(df.head(), use_container_width=True)
        
        # Obtener las columnas del DataFrame para que el usuario elija cuál analizar
        columnas = df.columns.tolist()
        columna_seleccionada = st.selectbox(
            "Selecciona la columna que contiene el texto a analizar por la IA:", 
            options=columnas
        )
        
        # Botón para disparar el procesamiento con IA
        if st.button("🚀 Ejecutar Análisis con IA", type="primary"):
            if not api_key_ingresada:
                st.warning("⚠️ Por favor, ingresa tu API Key de Gemini en la barra lateral.")
                st.stop()
                
            # Inicializar cliente de Gemini con la clave provista
            client = genai.Client(api_key=api_key_ingresada)
            
            sentimientos = []
            categorias = []
            
            # Elementos visuales de progreso
            barra_progreso = st.progress(0)
            status_text = st.empty()
            total_filas = len(df)
            
            # Función interna para consultar a la IA con Structured Outputs (JSON)
            def analizar_texto(texto):
                prompt = f"""
                Analiza el siguiente texto de un cliente o usuario:
                "{texto}"

                Responde ÚNICAMENTE en formato JSON estricto con las siguientes dos claves:
                - "sentimiento": Debe ser exactamente "Positivo", "Neutral" o "Negativo".
                - "categoria": Debe ser exactamente "Atención al cliente", "Interfaz/UX", "Facturación/Cobros" o "General".
                """
                
                config = types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
                
                try:
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt,
                        config=config
                    )
                    return json.loads(response.text)
                except Exception:
                    # Fallback de seguridad si ocurre un error temporal
                    return {
                        "sentimiento": "Neutral",
                        "categoria": "General"
                    }

            # Bucle de procesamiento fila por fila
            for i, (_, row) in enumerate(df.iterrows()):
                texto_a_evaluar = str(row[columna_seleccionada])
                status_text.text(f"Analizando registro {i+1} de {total_filas}...")
                
                resultado_ia = analizar_texto(texto_a_evaluar)
                
                sentimientos.append(resultado_ia.get("sentimiento", "Neutral"))
                categorias.append(resultado_ia.get("categoria", "General"))
                
                # Actualizar barra de progreso
                barra_progreso.progress((i + 1) / total_filas)
                time.sleep(0.3) # Pequeña pausa de cortesía para la API

            status_text.text("¡Análisis completado con éxito!")
            
            # 3. Asignar resultados al DataFrame
            df["IA_Sentimiento"] = sentimientos
            df["IA_Categoria"] = categorias
            
            st.markdown("---")
            st.subheader("✨ Resultados del Análisis con IA:")
            st.dataframe(df, use_container_width=True)
            
            # 4. Botón de descarga del Excel enriquecido
            @st.cache_data
            def convertir_a_excel(df_resultado):
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_resultado.to_excel(writer, index=False)
                return output.getvalue()
            
            excel_bytes = convertir_a_excel(df)
            
            st.download_button(
                label="📥 Descargar Reporte Enriquecido en Excel",
                data=excel_bytes,
                file_name="reporte_analizado_ia.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary"
            )

    except Exception as e:
        st.error(f"Ocurrió un error al procesar el archivo: {e}")