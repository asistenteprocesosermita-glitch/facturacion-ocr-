import streamlit as st
import pytesseract
from PIL import Image
import pdf2image
import tempfile
import os
import pandas as pd
import re
from datetime import datetime

# Importar funciones de extracción
from utils.extractor import *

st.set_page_config(page_title="Facturación con OCR", layout="wide")
st.title("🩺 Extracción de Datos Facturables desde Historia Clínica")

uploaded_file = st.file_uploader("Sube el archivo PDF o imagen de la historia clínica", type=['pdf', 'png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    with st.spinner("Procesando archivo..."):
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        # Convertir PDF a imágenes si es necesario
        if uploaded_file.type == "application/pdf":
            images = pdf2image.convert_from_path(tmp_path, dpi=300)
            text = ""
            for img in images:
                text += pytesseract.image_to_string(img, lang='spa')
        else:
            img = Image.open(tmp_path)
            text = pytesseract.image_to_string(img, lang='spa')

        os.unlink(tmp_path)  # eliminar archivo temporal

    st.success("Archivo procesado. Resultados:")

    # Extraer datos
    with st.expander("📋 Datos del Paciente", expanded=True):
        patient = extract_patient_data(text)
        col1, col2 = st.columns(2)
        col1.metric("CC", patient.get('CC', 'N/A'))
        col2.metric("Edad", patient.get('Edad', 'N/A'))
        col1.metric("Empresa", patient.get('Empresa', 'N/A'))
        col2.metric("Afiliado", patient.get('Afiliado', 'N/A'))

    with st.expander("🏥 Estancias por Servicio"):
        estancias = extract_estancias(text)
        if estancias:
            df_est = pd.DataFrame(estancias, columns=['Servicio', 'Tipo', 'Fecha'])
            st.dataframe(df_est)
        else:
            st.info("No se encontraron datos de estancia.")

    with st.expander("🩸 Procedimientos Facturables"):
        proced = extract_procedimientos(text)
        if proced:
            df_proc = pd.DataFrame(proced)
            st.dataframe(df_proc)
        else:
            st.info("No se encontraron procedimientos.")

    with st.expander("💊 Medicamentos Administrados"):
        medic = extract_medicamentos(text)
        if medic:
            df_med = pd.DataFrame(medic)
            st.dataframe(df_med)
        else:
            st.info("No se encontraron medicamentos.")

    with st.expander("🧪 Laboratorios"):
        labs = extract_laboratorios(text)
        if labs:
            df_labs = pd.DataFrame(labs)
            st.dataframe(df_labs)
        else:
            st.info("No se encontraron órdenes de laboratorio.")

    with st.expander("📷 Imágenes Diagnósticas"):
        img_dx = extract_imagenes(text)
        if img_dx:
            df_img = pd.DataFrame(img_dx)
            st.dataframe(df_img)
        else:
            st.info("No se encontraron imágenes diagnósticas.")

    with st.expander("👥 Interconsultas"):
        inter = extract_interconsultas(text)
        if inter:
            df_inter = pd.DataFrame(inter)
            st.dataframe(df_inter)
        else:
            st.info("No se encontraron interconsultas.")

    with st.expander("📝 Notas de Enfermería Relevantes"):
        enfer = extract_notas_enfermeria(text)
        if enfer:
            df_enfer = pd.DataFrame(enfer)
            st.dataframe(df_enfer)
        else:
            st.info("No se encontraron notas de enfermería relevantes.")

    # Botón para descargar reporte consolidado
    st.download_button(
        label="📥 Descargar Reporte Completo (CSV)",
        data=pd.concat([df_est, df_proc, df_med, df_labs, df_img, df_inter, df_enfer], ignore_index=True).to_csv(index=False).encode('utf-8'),
        file_name=f"facturacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
