import streamlit as st
import pytesseract
from PIL import Image
import tempfile
import os
import pandas as pd
import re
from datetime import datetime
import PyPDF2

# Intentar importar pdf2image, si falla, marcamos que Poppler no está disponible
try:
    from pdf2image import convert_from_path
    POPPLER_AVAILABLE = True
except ImportError:
    POPPLER_AVAILABLE = False
    st.warning("⚠️ Poppler no está instalado. Solo se podrá extraer texto de PDFs digitales (no escaneados).")

from utils.extractor import *

st.set_page_config(page_title="Facturación con OCR", layout="wide")
st.title("🩺 Extracción de Datos Facturables desde Historia Clínica")

uploaded_file = st.file_uploader("Sube el archivo PDF o imagen", type=['pdf', 'png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    with st.spinner("Procesando archivo..."):
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        text = ""

        if uploaded_file.type == "application/pdf":
            # Intentar extraer texto directamente con PyPDF2
            try:
                with open(tmp_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text
                # Si el texto extraído es muy corto, probablemente es un PDF escaneado
                if len(text.strip()) < 100:
                    if POPPLER_AVAILABLE:
                        st.info("El PDF parece ser escaneado. Usando OCR...")
                        images = convert_from_path(tmp_path, dpi=300)
                        text = ""
                        for img in images:
                            text += pytesseract.image_to_string(img, lang='spa')
                    else:
                        st.error("No se pudo extraer texto. El PDF probablemente es escaneado y Poppler no está instalado.")
            except Exception as e:
                st.error(f"Error al leer el PDF: {e}")
                if POPPLER_AVAILABLE:
                    st.info("Usando OCR como fallback...")
                    images = convert_from_path(tmp_path, dpi=300)
                    text = ""
                    for img in images:
                        text += pytesseract.image_to_string(img, lang='spa')
        else:
            # Es imagen, usar OCR directamente
            img = Image.open(tmp_path)
            text = pytesseract.image_to_string(img, lang='spa')

        os.unlink(tmp_path)  # eliminar temporal

    if not text.strip():
        st.error("No se pudo extraer texto del archivo.")
        st.stop()

    st.success("Archivo procesado. Resultados:")

    # Extraer datos del paciente
    with st.expander("📋 Datos del Paciente", expanded=True):
        patient = extract_patient_data(text)
        col1, col2 = st.columns(2)
        col1.metric("CC", patient.get('CC', 'N/A'))
        col2.metric("Edad", patient.get('Edad', 'N/A'))
        col1.metric("Empresa", patient.get('Empresa', 'N/A'))
        col2.metric("Afiliado", patient.get('Afiliado', 'N/A'))

    # Estancias
    with st.expander("🏥 Estancias por Servicio"):
        estancias = extract_estancias(text)
        if estancias:
            df_est = pd.DataFrame(estancias, columns=['Servicio', 'Tipo', 'Fecha'])
            st.dataframe(df_est)
        else:
            st.info("No se encontraron datos de estancia.")

    # Procedimientos
    with st.expander("🩸 Procedimientos Facturables"):
        proced = extract_procedimientos(text)
        if proced:
            df_proc = pd.DataFrame(proced)
            st.dataframe(df_proc)
        else:
            st.info("No se encontraron procedimientos.")

    # Medicamentos
    with st.expander("💊 Medicamentos Administrados"):
        medic = extract_medicamentos(text)
        if medic:
            df_med = pd.DataFrame(medic)
            st.dataframe(df_med)
        else:
            st.info("No se encontraron medicamentos.")

    # Laboratorios
    with st.expander("🧪 Laboratorios"):
        labs = extract_laboratorios(text)
        if labs:
            df_labs = pd.DataFrame(labs)
            st.dataframe(df_labs)
        else:
            st.info("No se encontraron órdenes de laboratorio.")

    # Imágenes
    with st.expander("📷 Imágenes Diagnósticas"):
        img_dx = extract_imagenes(text)
        if img_dx:
            df_img = pd.DataFrame(img_dx)
            st.dataframe(df_img)
        else:
            st.info("No se encontraron imágenes diagnósticas.")

    # Interconsultas
    with st.expander("👥 Interconsultas"):
        inter = extract_interconsultas(text)
        if inter:
            df_inter = pd.DataFrame(inter)
            st.dataframe(df_inter)
        else:
            st.info("No se encontraron interconsultas.")

    # Notas de enfermería
    with st.expander("📝 Notas de Enfermería Relevantes"):
        enfer = extract_notas_enfermeria(text)
        if enfer:
            df_enfer = pd.DataFrame(enfer)
            st.dataframe(df_enfer)
        else:
            st.info("No se encontraron notas relevantes.")

    # Botón de descarga
    all_dfs = []
    for df_name in ['df_est', 'df_proc', 'df_med', 'df_labs', 'df_img', 'df_inter', 'df_enfer']:
        if df_name in locals():
            all_dfs.append(locals()[df_name])
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        csv = combined_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Reporte Completo (CSV)",
            data=csv,
            file_name=f"facturacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
