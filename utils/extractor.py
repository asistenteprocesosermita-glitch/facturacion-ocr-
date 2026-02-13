import re
import pandas as pd

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
    fechas = []
    # Hospitalización general
    hosp_ing = re.search(r'FECHA\s+(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})\s+TIPO DE ATENCION\s*:\s*HOSPITALIZACION', text, re.IGNORECASE)
    if hosp_ing:
        fechas.append(('HOSPITALIZACION', 'INGRESO', hosp_ing.group(1)))
    # UCI
    uci_ing = re.search(r'INGRESO A UNIDAD DE CUIDADOS (?:INTERMEDIOS|INTENSIVOS).*?(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})', text, re.IGNORECASE)
    if uci_ing:
        fechas.append(('UCI', 'INGRESO', uci_ing.group(1)))
    # Última fecha como posible egreso
    all_dates = re.findall(r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})', text)
    if all_dates:
        fechas.append(('UCI', 'EGRESO', all_dates[-1]))
    return fechas

def extract_procedimientos(text):
    """Extrae procedimientos facturables."""
    procedimientos = []
    keywords = [
        'BIOPSIA', 'CATETER VENOSO CENTRAL', 'INTUBACION', 'TRANSFUSION',
        'VENTILACION MECANICA', 'ECOGRAFIA', 'TORACENTESIS', 'SONDA VESICAL',
        'SONDA OROGASTRICA'
    ]
    lines = text.split('\n')
    for line in lines:
        for kw in keywords:
            if kw in line.upper():
                fecha = re.search(r'(\d{2}/\d{2}/\d{4})', line)
                fecha = fecha.group(1) if fecha else ''
                procedimientos.append({'procedimiento': kw, 'fecha': fecha, 'descripcion': line.strip()})
    return procedimientos

def extract_medicamentos(text):
    """Extrae medicamentos de las fórmulas médicas."""
    medicamentos = []
    blocks = re.split(r'FORMULA MEDICA ESTANDAR', text, flags=re.IGNORECASE)
    for block in blocks[1:]:
        lines = block.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            match = re.match(r'\s*(\d+\.?\d*)\s+(.*?)(?:\s+\d+|\s*$)', line)
            if match:
                cantidad = match.group(1)
                desc = match.group(2).strip()
                dosis = via = frecuencia = ''
                if i+1 < len(lines):
                    dosis_match = re.search(r'Dosis:\s*(.*?)(?:\s+Via|\s*$)', lines[i+1])
                    dosis = dosis_match.group(1).strip() if dosis_match else ''
                    via_match = re.search(r'Via\s+(.*?)(?:\s+Frecuencia|\s*$)', lines[i+1])
                    via = via_match.group(1).strip() if via_match else ''
                    freq_match = re.search(r'Frecuencia\s+(.*?)(?:\s+Estado|\s*$)', lines[i+1])
                    frecuencia = freq_match.group(1).strip() if freq_match else ''
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
    """Extrae órdenes de laboratorio."""
    labs = []
    blocks = re.split(r'ORDENES DE LABORATORIO', text, flags=re.IGNORECASE)
    for block in blocks[1:]:
        for line in block.split('\n'):
            match = re.search(r'\d+\s+(.*?)(?:\s+Interpretado|\s+En proceso|\s+Cancelado|\s*$)', line)
            if match:
                examen = match.group(1).strip()
                fecha = re.search(r'(\d{2}/\d{2}/\d{4})', line)
                fecha = fecha.group(1) if fecha else ''
                labs.append({'examen': examen, 'fecha': fecha, 'linea': line.strip()})
    return labs

def extract_imagenes(text):
    """Extrae estudios de imágenes."""
    imagenes = []
    blocks = re.split(r'ORDENES DE IMAGENES DIAGNOSTICAS', text, flags=re.IGNORECASE)
    for block in blocks[1:]:
        for line in block.split('\n'):
            match = re.search(r'\d+\s+(.*?)(?:\s+Interpretado|\s+En proceso|\s+Cancelado|\s*$)', line)
            if match:
                estudio = match.group(1).strip()
                fecha = re.search(r'(\d{2}/\d{2}/\d{4})', line)
                fecha = fecha.group(1) if fecha else ''
                imagenes.append({'estudio': estudio, 'fecha': fecha, 'linea': line.strip()})
    return imagenes

def extract_interconsultas(text):
    """Extrae interconsultas."""
    inter = []
    blocks = re.split(r'INTERCONSULTA POR:', text, flags=re.IGNORECASE)
    for block in blocks[1:]:
        lines = block.split('\n')
        especialidad = lines[0].strip() if lines else ''
        fecha = re.search(r'(\d{2}/\d{2}/\d{4})', block)
        fecha = fecha.group(1) if fecha else ''
        inter.append({'especialidad': especialidad, 'fecha': fecha})
    return inter

def extract_notas_enfermeria(text):
    """Extrae eventos relevantes de enfermería."""
    eventos = []
    lines = text.split('\n')
    for line in lines:
        if 'TRANSFUSION' in line.upper() or 'ADMINISTRA' in line.upper():
            tipo = 'TRANSFUSION' if 'TRANSFUSION' in line.upper() else 'ADMINISTRACION'
            fecha = re.search(r'(\d{2}/\d{2}/\d{4})', line)
            fecha = fecha.group(1) if fecha else ''
            eventos.append({'tipo': tipo, 'fecha': fecha, 'detalle': line.strip()})
    return eventos
