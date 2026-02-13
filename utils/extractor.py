import re
import pandas as pd
from datetime import datetime

def extract_patient_data(text):
    """Extrae datos básicos del paciente."""
    data = {}
    patterns = {
        'CC': r'No\.\s*CC[:\s]*(\d+)',
        'Nombre': r'(?:JAVIER ENRIQUE MARRUGO RODRIGUEZ)',  # Se puede adaptar
        'Edad': r'Edad actual[:\s]*(\d+)\s*AÑOS',
        'Empresa': r'Empresa[:\s]*(.*?)(?:\n|$)',
        'Afiliado': r'Afiliado[:\s]*(.*?)(?:\n|$)',
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        data[key] = match.group(1).strip() if match else ''
    return data

def extract_estancias(text):
    """Extrae fechas de ingreso y egreso por servicio."""
    # Buscar patrones de ingreso a hospitalización general y UCI
    pattern_hosp_ingreso = r'FECHA\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})\s+TIPO DE ATENCION\s*:\s*HOSPITALIZACION'
    pattern_uci_ingreso = r'INGRESO A UNIDAD DE CUIDADOS (?:INTERMEDIOS|INTENSIVOS).*?(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})'
    pattern_traslado = r'TRASLADADO A (?:UNIDAD DE CUIDADOS INTENSIVOS).*?(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})'
    
    fechas = []
    
    hosp_ing = re.search(pattern_hosp_ingreso, text, re.IGNORECASE)
    if hosp_ing:
        fechas.append(('HOSPITALIZACION', 'INGRESO', hosp_ing.group(1)))
    
    uci_ing = re.search(pattern_uci_ingreso, text, re.IGNORECASE) or re.search(pattern_traslado, text, re.IGNORECASE)
    if uci_ing:
        fechas.append(('UCI', 'INGRESO', uci_ing.group(1)))
    
    # Intentar buscar egresos (fecha de última evolución en UCI o egreso)
    # Podría ser la última fecha encontrada en el documento
    # Por simplicidad, tomaremos la última fecha del documento como fin de estancia
    all_dates = re.findall(r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})', text)
    if all_dates:
        last_date = all_dates[-1]
        # Asumimos que el último servicio es UCI
        fechas.append(('UCI', 'EGRESO', last_date))
    
    return fechas

def extract_procedimientos(text):
    """Extrae procedimientos facturables."""
    procedimientos = []
    # Palabras clave de procedimientos
    keywords = [
        'BIOPSIA', 'CATETER VENOSO CENTRAL', 'INTUBACION', 'TRANSFUSION',
        'VENTILACION MECANICA', 'ECOGRAFIA', 'TORACENTESIS', 'SONDA VESICAL',
        'SONDA OROGASTRICA', 'HEMODIALISIS'
    ]
    lines = text.split('\n')
    for line in lines:
        for kw in keywords:
            if kw in line.upper():
                # Buscar fecha en la misma línea o cercana
                date_match = re.search(r'(\d{2}/\d{2}/\d{4})', line)
                fecha = date_match.group(1) if date_match else ''
                procedimientos.append({'procedimiento': kw, 'fecha': fecha, 'descripcion': line.strip()})
    return procedimientos

def extract_medicamentos(text):
    """Extrae medicamentos de las fórmulas médicas."""
    medicamentos = []
    # Buscar bloques de FORMULA MEDICA ESTANDAR
    blocks = re.split(r'FORMULA MEDICA ESTANDAR', text, flags=re.IGNORECASE)
    for block in blocks[1:]:  # saltar el primer split antes de la primera aparición
        lines = block.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            # Patrón: cantidad, descripción, dosis, vía, frecuencia
            match = re.match(r'\s*(\d+\.?\d*)\s+(.*?)(?:\s+\d+|\s*$)', line)
            if match:
                cantidad = match.group(1)
                desc = match.group(2).strip()
                # Buscar dosis y vía en líneas siguientes
                dosis = ''
                via = ''
                frecuencia = ''
                if i+1 < len(lines):
                    dosis_match = re.search(r'Dosis:\s*(.*?)(?:\s+Via|\s*$)', lines[i+1])
                    if dosis_match:
                        dosis = dosis_match.group(1).strip()
                    via_match = re.search(r'Via\s+(.*?)(?:\s+Frecuencia|\s*$)', lines[i+1])
                    if via_match:
                        via = via_match.group(1).strip()
                    freq_match = re.search(r'Frecuencia\s+(.*?)(?:\s+Estado|\s*$)', lines[i+1])
                    if freq_match:
                        frecuencia = freq_match.group(1).strip()
                medicamentos.append({
                    'cantidad': cantidad,
                    'medicamento': desc,
                    'dosis': dosis,
                    'via': via,
                    'frecuencia': frecuencia
                })
                i += 2
            else:
                i += 1
    return medicamentos

def extract_laboratorios(text):
    """Extrae órdenes de laboratorio y resultados."""
    labs = []
    blocks = re.split(r'ORDENES DE LABORATORIO', text, flags=re.IGNORECASE)
    for block in blocks[1:]:
        lines = block.split('\n')
        for line in lines:
            # Buscar descripción de examen
            match = re.search(r'\d+\s+(.*?)(?:\s+Interpretado|\s+En proceso|\s+Cancelado|\s*$)', line)
            if match:
                examen = match.group(1).strip()
                # Buscar fecha de aplicación
                fecha_match = re.search(r'(\d{2}/\d{2}/\d{4})', line)
                fecha = fecha_match.group(1) if fecha_match else ''
                labs.append({'examen': examen, 'fecha': fecha, 'linea': line.strip()})
    return labs

def extract_imagenes(text):
    """Extrae estudios de imágenes diagnósticas."""
    imagenes = []
    blocks = re.split(r'ORDENES DE IMAGENES DIAGNOSTICAS', text, flags=re.IGNORECASE)
    for block in blocks[1:]:
        lines = block.split('\n')
        for line in lines:
            match = re.search(r'\d+\s+(.*?)(?:\s+Interpretado|\s+En proceso|\s+Cancelado|\s*$)', line)
            if match:
                estudio = match.group(1).strip()
                fecha_match = re.search(r'(\d{2}/\d{2}/\d{4})', line)
                fecha = fecha_match.group(1) if fecha_match else ''
                imagenes.append({'estudio': estudio, 'fecha': fecha, 'linea': line.strip()})
    return imagenes

def extract_interconsultas(text):
    """Extrae interconsultas a otras especialidades."""
    interconsultas = []
    blocks = re.split(r'INTERCONSULTA POR:', text, flags=re.IGNORECASE)
    for block in blocks[1:]:
        lines = block.split('\n')
        especialidad = lines[0].strip() if lines else ''
        fecha_match = re.search(r'(\d{2}/\d{2}/\d{4})', block)
        fecha = fecha_match.group(1) if fecha_match else ''
        interconsultas.append({'especialidad': especialidad, 'fecha': fecha})
    return interconsultas

def extract_notas_enfermeria(text):
    """Extrae eventos relevantes de enfermería (transfusiones, administración de medicamentos)."""
    eventos = []
    lines = text.split('\n')
    for line in lines:
        if 'TRANSFUSION' in line.upper() or 'ADMINISTRA' in line.upper():
            if 'TRANSFUSION' in line.upper():
                tipo = 'TRANSFUSION'
            else:
                tipo = 'ADMINISTRACION'
            fecha_match = re.search(r'(\d{2}/\d{2}/\d{4})', line)
            fecha = fecha_match.group(1) if fecha_match else ''
            eventos.append({'tipo': tipo, 'fecha': fecha, 'detalle': line.strip()})
    return eventos
