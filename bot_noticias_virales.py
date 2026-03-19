#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT NOTICIAS VIRALES LATAM 24/7 - V4.1 DEBUG
Generacion de imagenes: Gemini -> Pollinations (fallback)
"""

import requests
import feedparser
import re
import hashlib
import json
import os
import random
import base64
import io
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from urllib.parse import urlparse, quote

# CONFIGURACION
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWSDATA_API_KEY = os.getenv('NEWSDATA_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

# APIs de imagen
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_viral.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot_viral.json')

TIEMPO_ENTRE_PUBLICACIONES = 55
MAX_TITULOS_HISTORIA = 300
UMBRAL_SIMILITUD_TITULO = 0.85
UMBRAL_SIMILITUD_CONTENIDO = 0.75

COLORES_BACKUP = {
    'urgente': (220, 20, 60),
    'negativa': (139, 0, 0),
    'positiva': (34, 139, 34),
    'neutral': (25, 25, 112),
    'deporte': (255, 140, 0),
    'politica': (75, 0, 130)
}

# [Aquí va todo el código de PERSONAJES_POLITICOS, EVENTOS_DEPORTIVOS, etc. que ya tienes]
# ... (mantén tu código existente de las bases de datos) ...

# ═══════════════════════════════════════════════════════════════
# FUNCIONES UTILITARIAS (mantener las que ya tienes)
# ═══════════════════════════════════════════════════════════════

def log(mensaje, tipo='info'):
    iconos = {'info': '[i]', 'exito': '[OK]', 'error': '[ERR]', 'advertencia': '[!]', 'debug': '[DBG]', 'imagen': '[IMG]'}
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {iconos.get(tipo, '[i]')} {mensaje}")

def cargar_json(ruta, default=None):
    if default is None: 
        default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else default.copy()
        except Exception as e:
            log(f"Error cargando JSON {ruta}: {e}", 'error')
    return default.copy()

def guardar_json(ruta, datos):
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        temp_path = f"{ruta}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        os.replace(temp_path, ruta)
        return True
    except Exception as e:
        log(f"Error guardando JSON: {e}", 'error')
        return False

def generar_hash(texto):
    if not texto: 
        return ""
    t = re.sub(r'[^\w\s]', '', texto.lower().strip())
    t = re.sub(r'\s+', ' ', t)
    return hashlib.md5(t.encode()).hexdigest()

def normalizar_url(url):
    if not url: 
        return ""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        path = parsed.path.lower()
        netloc = re.sub(r'^(www\.|m\.|mobile\.|amp\.)', '', netloc)
        path = re.sub(r'/index\.(html|php|htm|asp)$', '/', path)
        path = path.rstrip('/')
        path = re.sub(r'\.html?$', '', path)
        return f"{netloc}{path}"
    except:
        return url.lower().strip()

def calcular_similitud(t1, t2):
    if not t1 or not t2: 
        return 0.0
    def normalizar(t):
        t = re.sub(r'[^\w\s]', '', t.lower().strip())
        t = re.sub(r'\s+', ' ', t)
        stop_words = {'el', 'la', 'de', 'y', 'en', 'the', 'of', 'a', 'que', 'con'}
        palabras = [p for p in t.split() if p not in stop_words and len(p) > 3]
        return ' '.join(palabras)
    return SequenceMatcher(None, normalizar(t1), normalizar(t2)).ratio()

def es_titulo_generico(titulo):
    if not titulo: 
        return True
    tl = titulo.lower().strip()
    palabras = re.findall(r'\b\w+\b', tl)
    palabras_significativas = [p for p in palabras if len(p) > 4]
    return len(set(palabras_significativas)) < 3

def limpiar_texto(texto):
    if not texto: 
        return ""
    import html
    t = html.unescape(texto)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'https?://\S*', '', t)
    return t.strip()

def calcular_puntaje_viral(titulo, desc):
    txt = f"{titulo} {desc}".lower()
    puntaje = 0
    palabras_alta = ["golpe de estado", "corrupcion", "dictadura", "protestas", "crisis", "impeachment", 
                     "masacre", "feminicidio", "escandalo", "muerte", "viral", "trump", "milei", "amlo"]
    for palabra in palabras_alta:
        if palabra in txt:
            puntaje += 10
            if palabra in titulo.lower():
                puntaje += 5
    if 40 <= len(titulo) <= 90:
        puntaje += 5
    if re.search(r'\d+', titulo):
        puntaje += 3
    return puntaje

# ═══════════════════════════════════════════════════════════════
# GENERACION DE IMAGENES - CORREGIDO Y MEJORADO
# ═══════════════════════════════════════════════════════════════

def generar_imagen_gemini(prompt, titulo):
    """Genera imagen usando Gemini API"""
    if not GEMINI_API_KEY:
        return None, "No Gemini API key"
    
    try:
        log("Intentando Gemini...", 'imagen')
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp-image-generation:generateContent?key={GEMINI_API_KEY}"
        
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [{
                "parts": [{"text": f"Generate a news thumbnail image: {prompt}"}]
            }],
            "generationConfig": {
                "responseModalities": ["Text", "Image"],
                "temperature": 0.7
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'candidates' in data and len(data['candidates']) > 0:
                candidate = data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'inlineData' in part:
                            img_data = base64.b64decode(part['inlineData']['data'])
                            img_path = f'/tmp/viral_gemini_{generar_hash(titulo)}.jpg'
                            
                            with open(img_path, 'wb') as f:
                                f.write(img_data)
                            
                            if os.path.getsize(img_path) > 10000:
                                log(f"Imagen Gemini generada: {img_path}", 'exito')
                                return img_path, "Gemini"
        
        log(f"Gemini fallo: {response.status_code}", 'advertencia')
        return None, f"Gemini error: {response.status_code}"
        
    except Exception as e:
        log(f"Error Gemini: {e}", 'error')
        return None, str(e)

def generar_imagen_pollinations(prompt, titulo, seed=None):
    """Genera imagen usando Pollinations.ai"""
    try:
        log("Usando Pollinations...", 'imagen')
        
        prompt_enhanced = (
            f"breaking news thumbnail, viral news style, {prompt}, "
            f"professional news broadcast graphic, dramatic lighting, "
            f"high contrast, cinematic composition, 4k, photorealistic"
        )
        
        prompt_encoded = quote(prompt_enhanced[:1000])
        seed = seed or random.randint(1000, 9999)
        
        url = (
            f"https://image.pollinations.ai/prompt/{prompt_encoded}"
            f"?width=1200&height=630&nologo=true&seed={seed}"
            f"&enhance=true&quality=high"
        )
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        response = requests.get(url, headers=headers, timeout=60)
        
        if response.status_code == 200:
            img_path = f'/tmp/viral_pollinations_{generar_hash(titulo)}_{seed}.jpg'
            with open(img_path, 'wb') as f:
                f.write(response.content)
            
            if os.path.getsize(img_path) > 15000:
                log(f"Imagen Pollinations: {img_path}", 'exito')
                return img_path, "Pollinations"
            else:
                os.remove(img_path)
                return None, "Imagen muy pequeña"
        
        return None, f"HTTP {response.status_code}"
        
    except Exception as e:
        log(f"Error Pollinations: {e}", 'error')
        return None, str(e)

def generar_imagen_inteligente(titulo, contenido, descripcion=""):
    """Intenta generar imagen con múltiples estrategias"""
    # Importar aquí para evitar dependencia circular
    from types import SimpleNamespace
    
    # Crear un analizador simple si no existe
    class AnalizadorSimple:
        def analizar(self, titulo, contenido, descripcion=""):
            return {
                'personaje_principal': None,
                'tipo_evento': None,
                'deporte': None,
                'pais': None,
                'emocion': 'neutral',
                'escenario': 'default',
                'elementos_extra': []
            }
    
    analizador = AnalizadorSimple()
    analisis = analizador.analizar(titulo, contenido, descripcion)
    
    # Generar prompt simple pero efectivo
    prompt = (
        f"viral news thumbnail, breaking news style, dramatic, "
        f"news about: {titulo[:100]}, "
        f"professional photojournalism, news broadcast graphic, high impact"
    )
    
    log(f"Prompt: {prompt[:120]}...", 'imagen')
    
    # Intentar Gemini
    if GEMINI_API_KEY:
        img_path, fuente = generar_imagen_gemini(prompt, titulo)
        if img_path:
            return img_path, prompt, fuente, analisis
    
    # Intentar Pollinations (3 veces con diferentes seeds)
    for i in range(3):
        seed = random.randint(1000, 9999)
        img_path, fuente = generar_imagen_pollinations(prompt, titulo, seed)
        if img_path:
            return img_path, prompt, fuente, analisis
        time.sleep(1)
    
    # Último intento con prompt simplificado
    try:
        log("Último intento Pollinations...", 'imagen')
        prompt_minimal = f"breaking news photo: {titulo[:80]}"
        prompt_enc = quote(prompt_minimal)
        url = f"https://image.pollinations.ai/prompt/{prompt_enc}?width=1200&height=630&nologo=true&seed={random.randint(1,9999)}"
        
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=40)
        if r.status_code == 200:
            img_path = f'/tmp/viral_last_{generar_hash(titulo)}.jpg'
            with open(img_path, 'wb') as f:
                f.write(r.content)
            if os.path.getsize(img_path) > 10000:
                return img_path, prompt, "Pollinations-Last", analisis
    except:
        pass
    
    log("Todas las APIs de imagen fallaron", 'error')
    return None, prompt, "Ninguna", analisis

def crear_imagen_backup(titulo, analisis_contexto=None):
    """Crea imagen de respaldo con diseño profesional"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        width, height = 1200, 630
        
        # Color según emoción
        emocion = analisis_contexto.get('emocion', 'neutral') if analisis_contexto else 'neutral'
        color_fondo = COLORES_BACKUP.get(emocion, COLORES_BACKUP['neutral'])
        
        img = Image.new('RGB', (width, height), color_fondo)
        draw = ImageDraw.Draw(img)
        
        # Gradient sutil
        for i in range(200):
            color_gradiente = (
                max(0, color_fondo[0] - 50),
                max(0, color_fondo[1] - 50),
                max(0, color_fondo[2] - 50)
            )
            draw.rectangle([(0, height-200+i), (width, height-200+i+1)], fill=color_gradiente)
        
        # Fuentes
        try:
            font_titulo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            font_info = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except:
            font_titulo = ImageFont.load_default()
            font_sub = font_info = font_titulo
        
        # Barra superior
        draw.rectangle([(0, 0), (width, 15)], fill=(255, 255, 255))
        
        # Info contextual
        y_pos = 35
        if analisis_contexto:
            info_lineas = []
            if analisis_contexto.get('personaje_principal'):
                info_lineas.append("POLÍTICA")
            if analisis_contexto.get('pais'):
                info_lineas.append(analisis_contexto['pais'].upper())
            if analisis_contexto.get('deporte'):
                info_lineas.append("DEPORTES")
            if analisis_contexto.get('tipo_evento'):
                info_lineas.append("URGENTE")
            
            if info_lineas:
                texto_info = " • ".join(info_lineas)
                draw.text((52, y_pos+2), texto_info, font=font_info, fill=(0, 0, 0))
                draw.text((50, y_pos), texto_info, font=font_info, fill=(220, 220, 220))
                y_pos = 70
        
        # Título wrap
        titulo_limpio = titulo[:140]
        lineas = textwrap.wrap(titulo_limpio, width=28)
        if len(lineas) > 4:
            lineas = lineas[:4]
            lineas[-1] = lineas[-1][:25] + "..."
        
        altura_texto = len(lineas) * 55
        y_start = ((height - altura_texto) // 2) - 20
        
        for i, linea in enumerate(lineas):
            y = y_start + (i * 55)
            x = 60
            for offset in [(3, 3), (2, 2), (1, 1)]:
                draw.text((x+offset[0], y+offset[1]), linea, font=font_titulo, fill=(0, 0, 0))
            draw.text((x-1, y-1), linea, font=font_titulo, fill=(255, 255, 255))
            draw.text((x, y), linea, font=font_titulo, fill=(255, 255, 255))
        
        # Footer
        draw.rectangle([(50, height-80), (width-50, height-78)], fill=(255, 255, 255))
        draw.text((50, height-70), "NOTICIAS VIRALES LATAM 24/7", font=font_sub, fill=(255, 255, 255))
        fecha_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        draw.text((50, height-40), f"{fecha_str} | Información que importa", 
                 font=font_info, fill=(200, 200, 200))
        
        img_path = f'/tmp/viral_backup_{generar_hash(titulo[:50])}.jpg'
        img.save(img_path, 'JPEG', quality=95)
        
        log(f"Imagen backup creada: {img_path}", 'exito')
        return img_path
        
    except Exception as e:
        log(f"Error creando imagen backup: {e}", 'error')
        return None

# ═══════════════════════════════════════════════════════════════
# PUBLICACION FACEBOOK - CORREGIDA CON DEBUG
# ═══════════════════════════════════════════════════════════════

def publicar_facebook(titulo, texto, imagen_path, hashtags):
    """Publica en Facebook con manejo de errores mejorado"""
    print(f"\n[DEBUG] === INICIANDO PUBLICACIÓN FACEBOOK ===")
    print(f"[DEBUG] FB_PAGE_ID: {FB_PAGE_ID}")
    print(f"[DEBUG] FB_ACCESS_TOKEN: {'Configurado (longitud: ' + str(len(FB_ACCESS_TOKEN)) + ')' if FB_ACCESS_TOKEN else 'NO CONFIGURADO'}")
    print(f"[DEBUG] Imagen path: {imagen_path}")
    print(f"[DEBUG] Imagen existe: {os.path.exists(imagen_path) if imagen_path else 'N/A'}")
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales Facebook", 'error')
        print(f"[DEBUG] FB_PAGE_ID={FB_PAGE_ID is not None}, FB_ACCESS_TOKEN={FB_ACCESS_TOKEN is not None}")
        return False
    
    if not imagen_path or not os.path.exists(imagen_path):
        log("ERROR: No hay imagen para publicar", 'error')
        return False
    
    mensaje = f"{texto}\n\n{hashtags}\n\nNoticias Virales LATAM 24/7\nSiguenos para mas contenido viral"
    
    if len(mensaje) > 2200:
        lineas = texto.split('\n')
        texto_corto = ""
        for linea in lineas:
            if len(texto_corto + linea + "\n") < 1800:
                texto_corto += linea + "\n"
            else:
                break
        mensaje = f"{texto_corto.rstrip()}\n\n[...]\n\n{hashtags}\n\nNoticias Virales LATAM 24/7"
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        print(f"[DEBUG] URL de publicación: {url}")
        print(f"[DEBUG] Tamaño imagen: {os.path.getsize(imagen_path)} bytes")
        
        with open(imagen_path, 'rb') as f:
            files = {'file': ('imagen.jpg', f, 'image/jpeg')}
            data = {
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN,
                'published': 'true'
            }
            
            print(f"[DEBUG] Enviando POST a Facebook...")
            r = requests.post(url, files=files, data=data, timeout=60)
            
            print(f"[DEBUG] Status code: {r.status_code}")
            print(f"[DEBUG] Respuesta: {r.text[:500]}")
            
            resultado = r.json()
            
            if 'id' in resultado:
                log(f"Publicado exitosamente ID: {resultado['id']}", 'exito')
                return True
            else:
                error_msg = resultado.get('error', {}).get('message', 'Error desconocido')
                error_code = resultado.get('error', {}).get('code', 'N/A')
                log(f"Error Facebook: {error_msg} (Code: {error_code})", 'error')
                return False
                
    except Exception as e:
        log(f"Excepción publicando en Facebook: {e}", 'error')
        import traceback
        traceback.print_exc()
        return False

# ═══════════════════════════════════════════════════════════════
# FLUJO PRINCIPAL - CORREGIDO CON DEBUG COMPLETO
# ═══════════════════════════════════════════════════════════════

def verificar_tiempo():
    """Verifica si ha pasado el tiempo mínimo entre publicaciones"""
    estado = cargar_json(ESTADO_PATH, {'ultima_publicacion': None})
    ultima = estado.get('ultima_publicacion')
    
    # Si estamos en GitHub Actions, siempre permitir
    run_number = os.getenv('GITHUB_RUN_NUMBER')
    if run_number:
        print(f"[DEBUG] GitHub Actions detectado (run #{run_number}), permitiendo publicación")
        return True
    
    if not ultima:
        print(f"[DEBUG] No hay registro de última publicación, permitiendo")
        return True
    
    try:
        ultima_dt = datetime.fromisoformat(ultima)
        minutos = (datetime.now() - ultima_dt).total_seconds() / 60
        print(f"[DEBUG] Última publicación hace {minutos:.1f} minutos (mínimo: {TIEMPO_ENTRE_PUBLICACIONES})")
        
        if minutos < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"Esperando... Última hace {minutos:.0f} min", 'info')
            return False
    except Exception as e:
        print(f"[DEBUG] Error parseando fecha: {e}")
        pass
    
    return True

def main():
    print("\n" + "="*70)
    print("BOT NOTICIAS VIRALES LATAM 24/7 - V4.1 DEBUG")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # DEBUG: Variables de entorno
    print(f"\n[DEBUG] === CONFIGURACIÓN ===")
    print(f"[DEBUG] FB_PAGE_ID: {'✓ Configurado' if FB_PAGE_ID else '✗ NO CONFIGURADO'}")
    print(f"[DEBUG] FB_ACCESS_TOKEN: {'✓ Configurado' if FB_ACCESS_TOKEN else '✗ NO CONFIGURADO'}")
    print(f"[DEBUG] GEMINI_API_KEY: {'✓ Configurado' if GEMINI_API_KEY else '✗ No configurado (usará Pollinations)'}")
    print(f"[DEBUG] NEWS_API_KEY: {'✓ Configurado' if NEWS_API_KEY else '✗ No configurado'}")
    print(f"[DEBUG] GITHUB_RUN_NUMBER: {os.getenv('GITHUB_RUN_NUMBER', 'No (ejecución local)')}")
    print(f"[DEBUG] HISTORIAL_PATH: {HISTORIAL_PATH}")
    print(f"[DEBUG] ESTADO_PATH: {ESTADO_PATH}")
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR CRÍTICO: Faltan credenciales Facebook", 'error')
        print(f"\n[DEBUG] Para configurar, establece las variables de entorno:")
        print(f"  export FB_PAGE_ID='tu_page_id'")
        print(f"  export FB_ACCESS_TOKEN='tu_access_token'")
        return False
    
    # Verificar tiempo entre publicaciones
    puede_publicar = verificar_tiempo()
    if not puede_publicar:
        log("No se puede publicar aún (tiempo de espera entre posts)", 'advertencia')
        return True  # Retorna True para no marcar como error en CI/CD
    
    print(f"\n[DEBUG] === CARGANDO HISTORIAL ===")
    historial = cargar_json(HISTORIAL_PATH, {
        'urls': [], 'urls_normalizadas': [], 'hashes': [], 'timestamps': [],
        'titulos': [], 'descripciones': [],
        'estadisticas': {'total_publicadas': 0, 'ultimas_24h': 0}
    })
    
    total_historial = len(historial.get('urls', []))
    print(f"[DEBUG] URLs en historial: {total_historial}")
    print(f"[DEBUG] Total publicadas: {historial.get('estadisticas', {}).get('total_publicadas', 0)}")
    
    # Para prueba: Crear noticia de ejemplo si no hay APIs configuradas
    noticias = []
    
    if NEWS_API_KEY or NEWSDATA_API_KEY or GNEWS_API_KEY:
        print(f"\n[DEBUG] === OBTENIENDO NOTICIAS DE APIS ===")
        # Aquí irían tus funciones de obtención de noticias
        # Por ahora, creamos una noticia de prueba
        noticias = []
    else:
        print(f"\n[DEBUG] No hay APIs de noticias configuradas, usando noticia de prueba")
    
    # NOTICIA DE PRUEBA (eliminar cuando tengas APIs configuradas)
    noticia_prueba = {
        'titulo': 'Irán ejecuta a tres personas detenidas por las protestas de enero',
        'descripcion': 'Las autoridades iraníes confirmaron la ejecución de tres manifestantes detenidos durante las protestas que sacudieron el país en enero pasado.',
        'url': 'https://ejemplo.com/noticia-prueba-' + str(int(time.time())),
        'imagen': None,
        'fuente': 'Prueba:Noticias',
        'fecha': datetime.now().isoformat(),
        'puntaje': 50
    }
    
    if not noticias:
        noticias = [noticia_prueba]
        print(f"[DEBUG] Usando noticia de prueba: {noticia_prueba['titulo']}")
    
    print(f"\n[DEBUG] === PROCESANDO NOTICIAS ===")
    print(f"[DEBUG] Total noticias: {len(noticias)}")
    
    # Seleccionar primera noticia disponible (para prueba)
    seleccionada = noticias[0]
    print(f"[DEBUG] Noticia seleccionada: {seleccionada['titulo'][:60]}...")
    
    # Verificar si ya fue publicada
    url_norm = normalizar_url(seleccionada['url'])
    hash_titulo = generar_hash(seleccionada['titulo'])
    
    print(f"[DEBUG] URL normalizada: {url_norm}")
    print(f"[DEBUG] Hash título: {hash_titulo}")
    print(f"[DEBUG] ¿Ya publicada?: {url_norm in historial.get('urls_normalizadas', [])}")
    
    if url_norm in historial.get('urls_normalizadas', []):
        log("Noticia ya publicada anteriormente", 'advertencia')
        # Para prueba, modificamos la URL
        seleccionada['url'] = seleccionada['url'] + '?t=' + str(int(time.time()))
        print(f"[DEBUG] URL modificada para prueba: {seleccionada['url']}")
    
    # Generar contenido
    contenido = seleccionada.get('descripcion', 'Contenido de prueba para la noticia.')
    
    # Construir publicación
    publicacion = f"{seleccionada['titulo']}\n\n{contenido}\n\nFuente: {seleccionada['fuente']}"
    hashtags = "#NoticiasVirales #LATAM #UltimaHora #Viral"
    
    print(f"\n[DEBUG] === GENERANDO IMAGEN ===")
    
    # Generar imagen
    imagen_path, prompt_usado, fuente_imagen, analisis = generar_imagen_inteligente(
        seleccionada['titulo'], contenido, seleccionada.get('descripcion', '')
    )
    
    print(f"[DEBUG] Fuente imagen: {fuente_imagen}")
    print(f"[DEBUG] Prompt usado: {prompt_usado[:100]}..." if prompt_usado else "[DEBUG] No hay prompt")
    
    if not imagen_path:
        log("Generación de imagen falló, creando backup...", 'advertencia')
        analisis_simple = {'emocion': 'urgente', 'pais': 'iran'}
        imagen_path = crear_imagen_backup(seleccionada['titulo'], analisis_simple)
        fuente_imagen = "Backup"
    
    if not imagen_path:
        log("ERROR CRÍTICO: No se pudo generar ninguna imagen", 'error')
        return False
    
    print(f"[DEBUG] Imagen final: {imagen_path}")
    print(f"[DEBUG] Tamaño: {os.path.getsize(imagen_path)} bytes")
    
    # PUBLICAR
    print(f"\n[DEBUG] === PUBLICANDO EN FACEBOOK ===")
    exito = publicar_facebook(seleccionada['titulo'], publicacion, imagen_path, hashtags)
    
    print(f"\n[DEBUG] === RESULTADO ===")
    print(f"[DEBUG] Éxito: {exito}")
    
    # Limpiar imagen temporal
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
            print(f"[DEBUG] Imagen temporal eliminada")
    except Exception as e:
        print(f"[DEBUG] No se pudo eliminar imagen temporal: {e}")
    
    if exito:
        # Guardar en historial
        historial['urls'].append(seleccionada['url'])
        historial['urls_normalizadas'].append(normalizar_url(seleccionada['url']))
        historial['hashes'].append(generar_hash(seleccionada['titulo']))
        historial['timestamps'].append(datetime.now().isoformat())
        historial['titulos'].append(seleccionada['titulo'])
        historial['descripciones'].append(seleccionada.get('descripcion', '')[:400])
        
        stats = historial.get('estadisticas', {'total_publicadas': 0, 'ultimas_24h': 0})
        stats['total_publicadas'] = stats.get('total_publicadas', 0) + 1
        historial['estadisticas'] = stats
        
        guardar_json(HISTORIAL_PATH, historial)
        
        # Guardar estado
        estado = {
            'ultima_publicacion': datetime.now().isoformat(),
            'github_run_number': os.getenv('GITHUB_RUN_NUMBER'),
            'ultima_noticia': seleccionada['titulo'][:50],
            'fuente_imagen': fuente_imagen
        }
        guardar_json(ESTADO_PATH, estado)
        
        log(f"✓ PUBLICACIÓN EXITOSA - Total: {stats['total_publicadas']}", 'exito')
        return True
    else:
        log("✗ PUBLICACIÓN FALLIDA", 'error')
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
