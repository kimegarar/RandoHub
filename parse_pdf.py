#extractor automatizado de datos de PDF a CSV
#analiza cada línea del PDF y deduce columnas basándose en el formato de las palabras:
#ante la falta de interoperabilidad y APIs, un motor de ingesta ETL provisional para rescatar los datos del formato impreso

import pypdf  # 👈 Usamos pypdf, 100% compatible y sin dependencias complejas
import csv
import os
import re

# Asegúrate de que el nombre del PDF coincide exactamente con el que tienes en tu Mac

#ESTO NO ME CONVENCE es como un parche especifico total a un unico pdf
pdf_filename = "Premis-Randonneur-IndividividualTOTA-2025.pdf"
csv_filename = "randonneurs_reales_esp25.csv"

if not os.path.exists(pdf_filename):
    print(f"Error: No se encuentra el archivo PDF '{pdf_filename}' en esta carpeta.")
    print("Por favor, cópialo a la raíz de tu proyecto RandoHub.")
    exit()

print("Iniciando extracción con pypdf... Esto tomará muy pocos segundos.")

randonneurs_data = []

# Abrimos el archivo en modo binario de lectura
with open(pdf_filename, "rb") as f:
    reader = pypdf.PdfReader(f)
    total_paginas = len(reader.pages)
    print(f"Total páginas a procesar: {total_paginas}")

    # Recorremos cada página del PDF de forma secuencial
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if not text:
            continue

        # Dividimos el texto extraído en líneas individuales
        lines = text.split("\n")
        for line in lines:
            line = line.strip()

            # Buscamos líneas que empiecen por el número de orden (ej: "946 ABAD EXPOSITO...")
            match = re.match(r"^(\d+)\s+(.+)$", line)
            if match:
                content = match.group(2)

                # Buscamos el código ACP que empieza por 'ES' dentro de la línea
                acp_match = re.search(r"\b(ES\d+)\b", content)
                if acp_match:
                    acp_code = acp_match.group(1)

                    # Extraemos todo el texto que está antes del código ACP (Nombre, Apellidos y Club)
                    text_before_acp = content.split(acp_code)[0].strip()
                    words = text_before_acp.split()

                    if len(words) >= 2:
                        apellidos_list = []
                        nombre = ""
                        club_list = []

                        # ALGORITMO HEURÍSTICO INTELIGENTE (Data Cleansing):
                        # Separa Nombre, Apellidos y Club analizando el tipo:
                        # - Los Apellidos en MAYÚSCULAS.
                        # - El Nombre tiene formato de Título (Ej: Francisco, Sergio).
                        # - El Club viene después del Nombre.
                        found_name = False
                        for word in words:
                            # Detectamos el nombre propio (Capitalizado, ej: Sergio, Francisco)
                            if not found_name and word.istitle() and not word.isupper():
                                nombre = word
                                found_name = True
                            elif not found_name:
                                apellidos_list.append(word)  # Mayúsculas antes del nombre = Apellidos
                            else:
                                club_list.append(word)  # Texto después del nombre = Club

                        # Fallback de seguridad por si falla la detección tipográfica
                        if not nombre:
                            nombre = words[1]
                            apellidos_list = [words[0]]
                            club_list = words[2:]

                        apellidos = " ".join(apellidos_list)
                        club = " ".join(club_list) if club_list else "independiente"

                        # Guardamos el participante depurado de forma relacional
                        randonneurs_data.append({
                            'cognoms': apellidos,
                            'nom': nombre,
                            'club_name': club,
                            'acp_code': acp_code
                        })

#se guarda los resultados finales en un CSV limpio
with open(csv_filename, mode='w', encoding='utf-8', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=['cognoms', 'nom', 'club_name', 'acp_code'])
    writer.writeheader()
    for r in randonneurs_data:
        writer.writerow(r)

print(f"¡Éxito total! Se han extraído {len(randonneurs_data)} participantes reales de forma limpia utilizando pypdf.")
print(f"Los datos se han guardado en: '{csv_filename}'")


#ejecutar y saca la info a csv!
#python parse_pdf.py