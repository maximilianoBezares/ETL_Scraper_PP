
import re
import xmlrpc.client
import pandas as pd

class OdooClient:
    _instance = None  # Aquí guardaremos la instancia única

    def __new__(cls, *args, **kwargs):
        """Controla la creación de la instancia"""
        if not cls._instance:
            cls._instance = super(OdooClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, url=None, db=None, user=None, api_key=None):
        """Solo inicializamos la primera vez"""
        if self._initialized:
            return
        
        # Atributos de conexión
        self.url = url
        self.db = db
        self.user = user
        self.api_key = api_key
        self.uid = None
        self.models = None
        self._initialized = True

    def connect(self):
        # Si ya estamos conectados, no perdemos tiempo re-autenticando
        if self.uid and self.models:
            return True

        try:
            common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
            self.uid = common.authenticate(self.db, self.user, self.api_key, {})
            if self.uid:
                self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")
                print(" Conexión exitosa a Odoo.")
                return True
            else:
                print( "Error de autenticación.")
                return False    
        except Exception as e:
            print(f" Error al conectar con Odoo: {e}")
            return False

    def push_scraped_data(self, model_name, df_exitosos):
        if not self.uid or not self.models:
            print("❌ No hay conexión activa.")
            return

        # Filtramos solo filas que tengan un ID de Odoo válido
        df_limpio = df_exitosos.dropna(subset=['odoo_id'])
        registros = df_limpio.to_dict(orient='records')
        
        print(f">>> Intentando subir {len(registros)} productos a {model_name}...")
        
        exitos = 0
        errores = 0

        # Enviamos en grupos de 50 para evitar bloqueos por FK
        batch_size = 50
        for i in range(0, len(registros), batch_size):
            batch = registros[i:i + batch_size]
            data_to_send = []
            
            for p in batch:
                data_to_send.append({
                    'product_id': int(p['odoo_id']),
                    'scraped_product_name': str(p['nombre'])[:255],
                    'scraped_price': self.limpiar_precio(p['precio']),
                    'scraped_pharmaceutical_name': str(p.get('pharmacy', 'desconocida')),
                    'catalog': str(p.get('id_catalogo', '0')),
                    'suspicious': True if p.get('status') == 'suspicious' else False
                })

            try:
                self.models.execute_kw(self.db, self.uid, self.api_key, model_name, 'create', [data_to_send])
                exitos += len(data_to_send)
            except Exception as e:
                # CAMBIADO: Usamos print en lugar de self.logger.error
                print(f"⚠️ Error en el bloque {i}: {e}")
                errores += len(data_to_send)

        print(f" Sincronización terminada: {exitos} exitosos, {errores} fallidos.")

    
    def fetch_models(self):
        if not self.uid or not self.models:
            print("No hay conexión activa. Llama a connect() primero.")
            return {}

        try:
            models = self.models.execute_kw(self.db, self.uid, self.api_key, 'pharmacy.catalog.map', 'search_read',
                [[]], {'fields': ['url', 'pharmacy_name', 'odoo_category_id']})
            categories_map = {}
            for cat in models:
                key = (cat['url'], cat['pharmacy_name'])
                categories_map[key] = cat['odoo_category_id'][0] if cat['odoo_category_id'] else None
            return categories_map
            # extraer las nombres de las categorías

        except Exception as e:
            print(f"Error al obtener categorías: {e}")
            return {}   
        
    def limpiar_precio(self, texto_precio):
        if not texto_precio:
            return 0
        
        # Convertir a string por si viene un None o número
        texto = str(texto_precio)
        
        # Eliminar símbolos de moneda, puntos de miles y espacios
        # Buscamos todo lo que NO sea un número
        limpio = re.sub(r'[^\d]', '', texto)
        
        # Convertir a entero
        try:
            return int(limpio)
        except ValueError:
            return 0
        
    def fetch_existing_products(self, category_id):
        if not self.uid or not self.models:
            return pd.DataFrame()

        try:
            domain = [('categ_id', 'child_of', category_id)]
            fields = ['id', 'name', 'list_price', 'categ_id'] 
            print(f"Cargando maestros de Odoo (Categoría {category_id} y sus subcategorías)...")
            
            records = self.models.execute_kw(
                self.db, self.uid, self.api_key,
                'product.template', 'search_read',
                [domain], {'fields': fields}
            )

            if not records:
                print(f"⚠️ No hay productos maestros en el árbol de la categoría {category_id}")
                return pd.DataFrame()

            df = pd.DataFrame(records)
            
            df['categoria_nombre'] = df['categ_id'].apply(lambda x: x[1] if isinstance(x, list) else 'Sin Categ')
            df['categ_id'] = df['categ_id'].apply(lambda x: x[0] if isinstance(x, list) else x)
            df = df.rename(columns={'list_price': 'precio_odoo_base'})
            
            print(f"{len(df)} productos maestros encontrados (incluyendo categorías hijas).")
            return df

        except Exception as e:
            print(f"Error al obtener maestros con jerarquía: {e}")
            return pd.DataFrame()