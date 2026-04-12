import pandas as pd
import re
import unicodedata
from rapidfuzz import process, fuzz

class Matcher:
    def __init__(self):
        # Eliminamos la carga del modelo de IA para liberar RAM y tiempo
        print("Matcher optimizado para velocidad (Solo Fuzzy).")

    def limpiar_texto(self, texto):
        if not texto: return ""
        texto = "".join(c for c in unicodedata.normalize('NFD', str(texto)) 
                       if unicodedata.category(c) != 'Mn').lower()
        texto = re.sub(r'[^a-z0-9 ]', ' ', texto)
        return " ".join(texto.split())

    def limpiar_precio(self, texto_precio):
        if isinstance(texto_precio, (int, float)): return texto_precio
        texto = str(texto_precio)
        limpio = re.sub(r'[^\d]', '', texto)
        try:
            return int(limpio)
        except ValueError:
            return 0

    def run_pipeline(self, df_scraped, df_odoo):
        df_odoo = df_odoo.copy()
        df_odoo['name_clean'] = df_odoo['name'].apply(self.limpiar_texto)
        choices_odoo = df_odoo['name_clean'].tolist()

        def match_row(row):
            nombre_scrap = self.limpiar_texto(row['nombre'])
            precio_scrap = self.limpiar_precio(row['precio'])
            
            # --- SOLO FUZZY MATCHING (Sintáctico) ---
            res = process.extractOne(nombre_scrap, choices_odoo, scorer=fuzz.token_set_ratio)
            
            match_name = ""
            score = 0
            idx_ganador = None
            metodo = "fuzzy"

            if res:
                match_name, score, idx_ganador = res
                
            # --- EXTRACCIÓN DE DATOS ---
            if idx_ganador is not None:
                odoo_rec = df_odoo.iloc[idx_ganador]
                odoo_id = odoo_rec['id']
                precio_odoo = odoo_rec['precio_odoo_base']
                
                diff_pct = (abs(precio_scrap - precio_odoo) / precio_odoo * 100) if precio_odoo > 0 else 100
                amount_range = precio_odoo * 0.30
                rango_min = precio_odoo - amount_range
                rango_max = precio_odoo + amount_range
                
                # Clasificación más estricta ya que no tenemos IA
                status = 'fail'
                if score >= 95:
                    status = 'matched'
                elif score >= 50:
                    status = 'suspicious'
            else:
                odoo_id, precio_odoo, diff_pct, status = None, None, 0, 'fail'

            return pd.Series([odoo_id, match_name, precio_odoo, score, diff_pct, metodo, status])

        cols = ['odoo_id', 'match_name', 'precio_odoo', 'score', 'diff_precio_pct', 'metodo_match', 'status']
        df_scraped[cols] = df_scraped.apply(match_row, axis=1)

        priority_map = {'matched': 3, 'suspicious': 2, 'fail': 1}
        df_scraped['status_priority'] = df_scraped['status'].map(priority_map).fillna(0)

        df_sorted = df_scraped.sort_values(by=['pharmacy', 'odoo_id', 'status_priority', 'score', 'diff_precio_pct'], ascending=[True, True, False, False, True])
        df_final = df_sorted.drop_duplicates(subset=['pharmacy', 'odoo_id'], keep='first')
        
        return df_final