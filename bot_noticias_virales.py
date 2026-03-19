#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 BOT NOTICIAS VIRALES LATAM 24/7 - V1.0
Bot de noticias virales para Facebook con IA generativa de imágenes
"""

import requests
import feedparser
import re
import hashlib
import json
import os
import random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from urllib.parse import urlparse, urlunparse, quote

# ═══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════

NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWSDATA_API_KEY = os.getenv('NEWSDATA_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')
HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_viral.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot_viral.json')

# Configuración de publicación
TIEMPO_ENTRE_PUBLICACIONES = 45  # Minutos entre posts (más frecuente para viral)
MAX_TITULOS_HISTORIA = 200  # Más historial para evitar repeticiones

# Umbrales anti-duplicados
UMBRAL_SIMILITUD_TITULO = 0.80
UMBRAL_SIMILITUD_CONTENIDO = 0.70

# ═══════════════════════════════════════════════════════════════
# PALABRAS CLAVE PARA CONTENIDO VIRAL LATAM
# ═══════════════════════════════════════════════════════════════

PALABRAS_VIRALES_ALTA = [
    # Política y poder
    "golpe de estado", "corrupción", "dictadura", "protestas masivas", "crisis política",
    "impeachment", "renuncia", "detención", "extradición", "narco", "cartel",
    # Economía y crisis
    "crisis económica", "inflación récord", "devaluación", "dólar", "pobreza extrema",
    "crisis alimentaria", "escasez", "apagón", "apagones",
    # Seguridad y violencia
    "masacre", "feminicidio", "secuestro", "violencia", "crimen organizado",
    "balacera", "explosión", "tragedia", "accidente fatal",
    # Famosos y entretenimiento
    "famoso", "celebridad", "escándalo", "divorcio", "romance", "embarazo",
    "muerte", "homenaje", "premio", "ganador", "finalista",
    # Tecnología y tendencias
    "viral", "tiktok", "tendencia", "filtro", "challenge", "meme",
    "inteligencia artificial", "robot", "ovni", "extraterrestre",
    # Deportes
    "mundial", "final", "campeón", "gol", "lesión", "traspaso", "millones"
]

PALABRAS_VIRALES_MEDIA = [
    "revelan", "exclusiva", "filtran", "inesperado", "sorprendente", "impactante",
    "indignante", "conmovedor", "heroico", "increíble", "inédito", "histórico",
    "urgente", "alerta", "emergencia", "sancionan", "prohiben", "descubren"
]

# Plantillas de CTA virales
CTAS_VIRALES = [
    "🔥 ¿Qué opinas? ¡Déjalo en los comentarios! 👇",
    "😱 ¿Te lo esperabas? Reacciona con ❤️ si te sorprendió",
    "💬 ¿Crees que es justo? ¡Comenta tu opinión!",
    "🚨 COMPARTE si crees que esto debe saberse",
    "👀 ¿Conoces a alguien afectado? Etiquétalo 👇",
    "🤔 ¿Tú qué harías en esta situación? 💭",
    "⚡️ NOTICIA EN DESARROLLO - Mantente informado",
    "📲 Síguenos para más noticias virales de LATAM",
    "🔔 Activa las notificaciones para no perderte nada",
    "💥 Esto está rompiendo internet ahora mismo",
    "🌎 ¿Afectará a tu país? ¡Comenta! 👇",
    "⏰ ÚLTIMO MINUTO - Información en constante actualización"
]

EMOJIS_VIRALES = ["🔥", "⚡️", "💥", "🚨", "😱", "🤯", "👀", "💯", "🌎", "📢", "‼️", "🆘"]

# Blacklist de títulos genéricos
BLACKLIST_TITULOS = [
    r'^\s*última hora\s*$', r'^\s*breaking news\s*$', r'^\s*noticias de hoy\s*$',
    r'^\s*alerta\s*$', r'^\s*news\s*$', r'^\s*actualización\s*$'
]

# ═══════════════════════════════════════════════════════════════
# FUNCIONES UTILITARIAS
# ═══════════════════════════════════════════════════════════════

def log(mensaje, tipo='info'):
    """Logging con emojis y colores conceptuales"""
    iconos = {
        'info': 'ℹ️', 
        'exito': '✅', 
        'error': '❌', 
        'advertencia': '⚠️', 
        'debug': '🔍',
        'viral': '🚀',
        'imagen': '🎨'
    }
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {iconos.get(tipo, 'ℹ️')} {mensaje}")

def cargar_json(ruta, default=None):
    """Carga archivo JSON con manejo de errores"""
    if default is None: 
        default = {}
    if os.path.exists(ruta):
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else default.copy()
        except Exception as e:
            log(f"Error cargando JSON {ruta}: {e}", 'error')
            try:
                backup = f"{ruta}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
                os.rename(ruta, backup)
                log(f"Backup creado: {backup}", 'advertencia')
            except: 
                pass
    return default.copy()

def guardar_json(ruta, datos):
    """Guarda JSON de forma segura con archivo temporal"""
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
    """Genera hash MD5 de texto normalizado"""
    if not texto: 
        return ""
    t = re.sub(r'[^\w\s]', '', texto.lower().strip())
    t = re.sub(r'\s+', ' ', t)
    return hashlib.md5(t.encode()).hexdigest()

def normalizar_url(url):
    """Normalización agresiva de URLs para detectar duplicados"""
    if not url: 
        return ""
    try:
        parsed = urlparse(url)
    except:
        return url.lower().strip()
    
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.lower()
    
    # Remover prefijos comunes
    netloc = re.sub(r'^(www\.|m\.|mobile\.|amp\.)', '', netloc)
    path = re.sub(r'/index\.(html|php|htm|asp)$', '/', path)
    path = path.rstrip('/')
    path = re.sub(r'\.html?$', '', path)
    
    url_base = f"{netloc}{path}"
    
    # Mantener solo parámetros esenciales
    query_params = []
    if parsed.query:
        params = parsed.query.split('&')
        for p in params:
            if '=' in p:
                key = p.split('=')[0].lower()
                if key in ['id', 'article', 'post', 'p', 'noticia', 'newsid']:
                    query_params.append(p.lower())
    
    if query_params:
        url_base += '?' + '&'.join(sorted(query_params))
    
    return url_base

def extraer_dominio(url):
    """Extrae dominio principal"""
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        parts = netloc.split('.')
        if len(parts) > 2:
            return '.'.join(parts[-2:])
        return netloc
    except:
        return ""

def calcular_similitud(t1, t2):
    """Calcula similitud entre textos"""
    if not t1 or not t2: 
        return 0.0
    
    def normalizar(t):
        t = re.sub(r'[^\w\s]', '', t.lower().strip())
        t = re.sub(r'\s+', ' ', t)
        # Remover palabras vacías
        stop_words = {'el', 'la', 'de', 'y', 'en', 'the', 'of', 'a', 'que', 'con'}
        palabras = [p for p in t.split() if p not in stop_words and len(p) > 3]
        return ' '.join(palabras)
    
    return SequenceMatcher(None, normalizar(t1), normalizar(t2)).ratio()

def es_titulo_generico(titulo):
    """Detecta si un título es demasiado genérico"""
    if not titulo: 
        return True
    tl = titulo.lower().strip()
    for patron in BLACKLIST_TITULOS:
        if re.match(patron, tl): 
            return True
    
    palabras = re.findall(r'\b\w+\b', tl)
    palabras_significativas = [p for p in palabras if len(p) > 4]
    return len(palabras_significativas) < 3

def limpiar_texto(texto):
    """Limpia HTML y normaliza texto"""
    if not texto: 
        return ""
    import html
    t = html.unescape(texto)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'https?://\S*', '', t)
    return t.strip()

def calcular_puntaje_viral(titulo, desc):
    """Calcula puntaje de viralidad basado en palabras clave"""
    txt = f"{titulo} {desc}".lower()
    puntaje = 0
    
    # Puntos por palabras virales de alta prioridad
    for palabra in PALABRAS_VIRALES_ALTA:
        if palabra in txt:
            puntaje += 10
            if palabra in titulo.lower():
                puntaje += 5  # Bonus si está en el título
    
    # Puntos por palabras de media prioridad
    for palabra in PALABRAS_VIRALES_MEDIA:
        if palabra in txt:
            puntaje += 3
    
    # Bonus por longitud óptima de título (más corto = más viral)
    long_titulo = len(titulo)
    if 40 <= long_titulo <= 80:
        puntaje += 5
    elif long_titulo > 120:
        puntaje -= 3
    
    # Bonus por presencia de números (engagement)
    if re.search(r'\d+', titulo):
        puntaje += 3
    
    # Bonus por signos de exclamación/interrogación
    if '!' in titulo or '?' in titulo:
        puntaje += 2
    
    return puntaje

# ═══════════════════════════════════════════════════════════════
# EXTRACCIÓN DE CONTENIDO
# ═══════════════════════════════════════════════════════════════

def extraer_contenido(url):
    """Extrae contenido de artículo desde URL"""
    if not url: 
        return None, None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Remover elementos no deseados
        for elem in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            elem.decompose()
        
        # Buscar en article
        article = soup.find('article')
        if article:
            parrafos = article.find_all('p')
            if len(parrafos) >= 3:
                texto = ' '.join([
                    limpiar_texto(p.get_text()) 
                    for p in parrafos 
                    if len(p.get_text()) > 40
                ])
                if len(texto) > 300:
                    return texto[:2000], None
        
        # Buscar por clases comunes
        for clase in ['article-content', 'entry-content', 'post-content', 'content']:
            elem = soup.find(class_=lambda x: x and clase in x.lower())
            if elem:
                parrafos = elem.find_all('p')
                if len(parrafos) >= 2:
                    texto = ' '.join([
                        limpiar_texto(p.get_text()) 
                        for p in parrafos 
                        if len(p.get_text()) > 40
                    ])
                    if len(texto) > 300:
                        return texto[:2000], None
        
        return None, None
        
    except Exception as e:
        log(f"Error extrayendo contenido: {e}", 'debug')
        return None, None

def extraer_imagen_web(url):
    """Extrae imagen principal de una URL"""
    if not url:
        return None
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.content, 'html.parser')
        
        # Meta tags
        for meta in ['og:image', 'twitter:image']:
            tag = soup.find('meta', property=meta) or soup.find('meta', attrs={'name': meta})
            if tag:
                img_url = tag.get('content', '').strip()
                if img_url and img_url.startswith('http'):
                    return img_url
        
        # Imagen en artículo
        article = soup.find('article') or soup.find('main')
        if article:
            for img in article.find_all('img'):
                src = img.get('data-src') or img.get('src', '')
                if src and src.startswith('http') and 'logo' not in src.lower():
                    return src
        
        return None
        
    except:
        return None

# ═══════════════════════════════════════════════════════════════
# GENERACIÓN DE IMÁGENES CON IA (POLLINATIONS.AI - GRATUITO)
# ═══════════════════════════════════════════════════════════════

def generar_prompt_imagen(titulo, contenido):
    """Genera un prompt optimizado para IA basado en la noticia"""
    # Extraer keywords del título
    palabras_clave = []
    
    # Detectar categoría
    txt = f"{titulo} {contenido[:200]}".lower()
    
    if any(p in txt for p in ['política', 'gobierno', 'presidente', 'congreso', 'protesta']):
        categoria = "political news photography, press conference, government building"
        estilo = "photojournalism style, dramatic lighting"
    elif any(p in txt for p in ['crimen', 'policía', 'accidente', 'tragedia', 'violencia']):
        categoria = "breaking news photography, emergency scene, documentary style"
        estilo = "cinematic lighting, high contrast, urgent atmosphere"
    elif any(p in txt for p in ['economía', 'dinero', 'crisis', 'mercado', 'banco']):
        categoria = "financial news illustration, stock market, economic crisis visualization"
        estilo = "modern infographic style, professional business photography"
    elif any(p in txt for p in ['famoso', 'celebridad', 'escándalo', 'entretenimiento']):
        categoria = "celebrity news, red carpet, paparazzi style"
        estilo = "glamour photography, high fashion lighting"
    elif any(p in txt for p in ['deporte', 'fútbol', 'gol', 'partido']):
        categoria = "sports news photography, stadium, action shot"
        estilo = "dynamic sports photography, motion blur, energetic"
    else:
        categoria = "news photography, breaking news, documentary"
        estilo = "professional photojournalism, vivid colors, impactful"
    
    # Limpiar título para prompt
    titulo_limpio = re.sub(r'[^\w\s]', '', titulo)
    titulo_limpio = titulo_limpio[:100]  # Limitar longitud
    
    prompt = f"{categoria}, {titulo_limpio}, {estilo}, high quality, 4k, professional photography, news broadcast style, dramatic composition"
    
    return prompt

def generar_imagen_ia(titulo, contenido):
    """
    Genera imagen usando Pollinations.ai (gratuito, sin API key)
    """
    try:
        prompt = generar_prompt_imagen(titulo, contenido)
        log(f"🎨 Generando imagen con prompt: {prompt[:80]}...", 'imagen')
        
        # Codificar prompt para URL
        prompt_encoded = quote(prompt)
        
        # URL de Pollinations.ai (servicio gratuito)
        url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1200&height=630&nologo=true&seed={random.randint(1000, 9999)}"
        
        # Descargar imagen
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=60)
        
        if response.status_code == 200:
            # Guardar imagen
            img_path = f'/tmp/viral_img_{generar_hash(titulo)}.jpg'
            with open(img_path, 'wb') as f:
                f.write(response.content)
            
            # Verificar tamaño mínimo
            if os.path.getsize(img_path) > 10000:
                log(f"✅ Imagen generada: {img_path}", 'exito')
                return img_path
            else:
                os.remove(img_path)
                log("Imagen generada muy pequeña", 'advertencia')
                return None
        else:
            log(f"Error generando imagen: HTTP {response.status_code}", 'error')
            return None
            
    except Exception as e:
        log(f"Error en generación de imagen: {e}", 'error')
        return None

def crear_imagen_backup(titulo):
    """Crea imagen de respaldo con texto si la IA falla"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        # Colores vibrantes para viralidad
        colores_fondo = ['#FF006E', '#FB5607', '#FFBE0B', '#8338EC', '#3A86FF', '#06FFA5']
        color_fondo = random.choice(colores_fondo)
        
        img = Image.new('RGB', (1200, 630), color=color_fondo)
        draw = ImageDraw.Draw(img)
        
        # Intentar cargar fuentes
        try:
            font_titulo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        except:
            font_titulo = ImageFont.load_default()
            font_sub = font_titulo
        
        # Barra superior decorativa
        draw.rectangle([(0, 0), (1200, 12)], fill='white')
        
        # Texto del título
        titulo_wrapped = textwrap.fill(titulo[:120], width=32)
        lineas = titulo_wrapped.split('\n')
        
        # Calcular posición centrada
        y_start = (630 - len(lineas) * 60) // 2 - 40
        
        # Dibujar sombra
        for i, linea in enumerate(lineas):
            y = y_start + i * 60
            draw.text((62, y+2), linea, font=font_titulo, fill='black')
        
        # Dibujar texto principal
        for i, linea in enumerate(lineas):
            y = y_start + i * 60
            draw.text((60, y), linea, font=font_titulo, fill='white')
        
        # Footer
        draw.text((60, 550), "🔥 NOTICIAS VIRALES LATAM", font=font_sub, fill='white')
        draw.text((60, 590), "24/7 • Información que importa", font=font_sub, fill='rgba(255,255,255,0.8)')
        
        img_path = f'/tmp/viral_backup_{generar_hash(titulo)}.jpg'
        img.save(img_path, 'JPEG', quality=90)
        
        return img_path
        
    except Exception as e:
        log(f"Error creando imagen backup: {e}", 'error')
        return None

# ═══════════════════════════════════════════════════════════════
# CONSTRUCCIÓN DE PUBLICACIÓN VIRAL
# ═══════════════════════════════════════════════════════════════

def dividir_parrafos_viral(texto):
    """Divide texto en párrafos cortos y impactantes"""
    if not texto:
        return []
    
    # Dividir por oraciones
    oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', texto) if len(o.strip()) > 20]
    
    if len(oraciones) < 3:
        return [texto[:300] + "..."] if len(texto) > 100 else []
    
    # Agrupar en párrafos de 2-3 oraciones máximo (más legible en móvil)
    parrafos = []
    actual = []
    palabras = 0
    
    for i, oracion in enumerate(oraciones[:12]):  # Máximo 12 oraciones
        actual.append(oracion)
        palabras += len(oracion.split())
        
        if palabras >= 25 or i == len(oraciones) - 1 or len(actual) >= 2:
            if len(' '.join(actual).split()) >= 10:
                parrafos.append(' '.join(actual))
            actual = []
            palabras = 0
    
    return parrafos[:5]  # Máximo 5 párrafos para no saturar

def construir_publicacion_viral(titulo, contenido, fuente):
    """
    Construye publicación en formato viral optimizado para engagement
    """
    titulo_limpio = limpiar_texto(titulo)
    parrafos = dividir_parrafos_viral(contenido)
    
    if len(parrafos) < 2:
        # Fallback si no hay suficientes párrafos
        oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', contenido) if len(o.strip()) > 20]
        parrafos = [' '.join(oraciones[i:i+2]) for i in range(0, min(6, len(oraciones)), 2)]
    
    lineas = []
    
    # Hook inicial con emoji viral
    emoji_header = random.choice(EMOJIS_VIRALES)
    lineas.append(f"{emoji_header} {titulo_limpio}")
    lineas.append("")
    
    # Separador visual
    lineas.append("─" * 25)
    lineas.append("")
    
    # Contenido en párrafos cortos
    for i, parrafo in enumerate(parrafos):
        lineas.append(parrafo)
        if i < len(parrafos) - 1:
            lineas.append("")  # Línea vacía entre párrafos
    
    # Separador antes de CTA
    lineas.append("")
    lineas.append("─" * 25)
    lineas.append("")
    
    # CTA principal
    cta = random.choice(CTAS_VIRALES)
    lineas.append(cta)
    lineas.append("")
    
    # Crédito
    lineas.append(f"📰 Fuente: {fuente}")
    lineas.append("🌎 Noticias Virales LATAM 24/7")
    
    return '\n'.join(lineas)

def generar_hashtags_virales(titulo, contenido):
    """Genera hashtags virales optimizados para LATAM"""
    txt = f"{titulo} {contenido}".lower()
    hashtags = ['#NoticiasVirales', '#LATAM', '#ÚltimaHora']
    
    # Hashtags temáticos
    temas = {
        r'(mexico|méxico|amlo)': '#México',
        r'(argentina|milei|buenos aires)': '#Argentina',
        r'(colombia|petro|bogotá|bogota)': '#Colombia',
        r'(chile|boric|santiago)': '#Chile',
        r'(peru|perú|lima|dina)': '#Perú',
        r'(venezuela|maduro|caracas)': '#Venezuela',
        r'(brasil|brazil|lula)': '#Brasil',
        r'(politica|política|gobierno)': '#Política',
        r'(economia|economía|crisis|dinero)': '#Economía',
        r'(seguridad|crimen|policia|policía)': '#Seguridad',
        r'(famoso|celebridad|espectaculo)': '#Espectáculos',
        r'(deporte|futbol|fútbol|mundial)': '#Deportes',
        r'(tecnologia|tecnología|viral)': '#Tecnología'
    }
    
    for patron, hashtag in temas.items():
        if re.search(patron, txt) and hashtag not in hashtags:
            hashtags.append(hashtag)
    
    # Hashtags genéricos virales
    hashtags.extend(['#Viral', '#Tendencia', '#Noticias'])
    
    return ' '.join(hashtags[:8])  # Máximo 8 hashtags

# ═══════════════════════════════════════════════════════════════
# GESTIÓN DE HISTORIAL ANTI-DUPLICADOS
# ═══════════════════════════════════════════════════════════════

def cargar_historial():
    """Carga historial de publicaciones"""
    default = {
        'urls': [],
        'urls_normalizadas': [],
        'hashes': [],
        'timestamps': [],
        'titulos': [],
        'descripciones': [],
        'estadisticas': {
            'total_publicadas': 0,
            'ultimas_24h': 0
        }
    }
    
    h = cargar_json(HISTORIAL_PATH, default)
    
    # Asegurar que existan todas las claves
    for k in default:
        if k not in h:
            h[k] = default[k]
    
    limpiar_historial_antiguo(h)
    return h

def limpiar_historial_antiguo(h):
    """Limpia entradas antiguas del historial"""
    try:
        ahora = datetime.now()
        indices_validos = []
        
        for i, ts in enumerate(h.get('timestamps', [])):
            try:
                fecha = datetime.fromisoformat(ts)
                if (ahora - fecha).days < 5:  # Mantener 5 días
                    indices_validos.append(i)
            except:
                continue
        
        for key in ['urls', 'urls_normalizadas', 'hashes', 'timestamps', 'titulos', 'descripciones']:
            if key in h and isinstance(h[key], list):
                h[key] = [h[key][i] for i in indices_validos if i < len(h[key])]
        
        # Contar publicaciones últimas 24h
        count_24h = 0
        for ts in h.get('timestamps', []):
            try:
                fecha = datetime.fromisoformat(ts)
                if (ahora - fecha).total_seconds() < 86400:
                    count_24h += 1
            except:
                continue
        
        h['estadisticas']['ultimas_24h'] = count_24h
        
    except Exception as e:
        log(f"Error limpiando historial: {e}", 'error')

def noticia_ya_publicada(h, url, titulo, desc=""):
    """Verifica si una noticia ya fue publicada (múltiples métodos)"""
    if not h:
        return False, "sin_historial"
    
    url_norm = normalizar_url(url)
    hash_titulo = generar_hash(titulo)
    
    log(f"   🔍 Verificando: {titulo[:50]}...", 'debug')
    
    # 1. Título genérico
    if es_titulo_generico(titulo):
        return True, "titulo_generico"
    
    # 2. URL normalizada exacta
    if url_norm in h.get('urls_normalizadas', []):
        return True, "url_duplicada"
    
    # 3. Hash exacto de título
    if hash_titulo in h.get('hashes', []):
        return True, "hash_duplicado"
    
    # 4. Similitud de títulos
    for titulo_hist in h.get('titulos', []):
        sim = calcular_similitud(titulo, titulo_hist)
        if sim >= UMBRAL_SIMILITUD_TITULO:
            return True, f"similitud_titulo_{sim:.2f}"
    
    # 5. Similitud de contenido/descripción
    if desc:
        for desc_hist in h.get('descripciones', []):
            sim = calcular_similitud(desc[:200], desc_hist[:200])
            if sim >= UMBRAL_SIMILITUD_CONTENIDO:
                return True, f"similitud_contenido_{sim:.2f}"
    
    return False, "nuevo"

def guardar_historial(h, url, titulo, desc=""):
    """Guarda noticia en historial"""
    url_norm = normalizar_url(url)
    hash_t = generar_hash(titulo)
    
    h['urls'].append(url)
    h['urls_normalizadas'].append(url_norm)
    h['hashes'].append(hash_t)
    h['timestamps'].append(datetime.now().isoformat())
    h['titulos'].append(titulo)
    h['descripciones'].append(desc[:500] if desc else "")
    h['estadisticas']['total_publicadas'] += 1
    
    # Limitar tamaño
    for key in ['urls', 'urls_normalizadas', 'hashes', 'timestamps', 'titulos', 'descripciones']:
        if len(h[key]) > MAX_TITULOS_HISTORIA:
            h[key] = h[key][-MAX_TITULOS_HISTORIA:]
    
    guardar_json(HISTORIAL_PATH, h)
    return h

# ═══════════════════════════════════════════════════════════════
# FUENTES DE NOTICIAS (Sin Google News)
# ═══════════════════════════════════════════════════════════════

def obtener_newsapi():
    """Obtiene noticias de NewsAPI"""
    if not NEWS_API_KEY:
        return []
    
    noticias = []
    
    # Queries optimizadas para viralidad LATAM
    queries = [
        'Mexico politics crisis corruption',
        'Argentina Milei economy protest',
        'Colombia Petro violence peace',
        'Chile Boric protest economy',
        'Peru political crisis Dina Boluarte',
        'Venezuela Maduro opposition election',
        'Brazil Lula Bolsonaro politics',
        'Latin America crisis economy inflation',
        'LATAM celebrity scandal famous',
        'Latin America soccer football scandal'
    ]
    
    for query in queries:
        try:
            r = requests.get(
                'https://newsapi.org/v2/everything',
                params={
                    'apiKey': NEWS_API_KEY,
                    'q': query,
                    'language': 'es',
                    'sortBy': 'publishedAt',
                    'pageSize': 5
                },
                timeout=15
            ).json()
            
            if r.get('status') == 'ok':
                for art in r.get('articles', []):
                    titulo = art.get('title', '')
                    if titulo and '[Removed]' not in titulo:
                        desc = art.get('description', '')
                        noticias.append({
                            'titulo': limpiar_texto(titulo),
                            'descripcion': limpiar_texto(desc),
                            'url': art.get('url', ''),
                            'imagen': art.get('urlToImage'),
                            'fuente': f"NewsAPI:{art.get('source', {}).get('name', 'Unknown')}",
                            'fecha': art.get('publishedAt'),
                            'puntaje': calcular_puntaje_viral(titulo, desc)
                        })
        except:
            continue
    
    log(f"NewsAPI: {len(noticias)} noticias", 'info')
    return noticias

def obtener_newsdata():
    """Obtiene noticias de NewsData.io"""
    if not NEWSDATA_API_KEY:
        return []
    
    noticias = []
    categorias = ['world', 'politics', 'business', 'entertainment', 'sports', 'technology']
    
    for cat in categorias:
        try:
            r = requests.get(
                'https://newsdata.io/api/1/news',
                params={
                    'apikey': NEWSDATA_API_KEY,
                    'language': 'es',
                    'category': cat,
                    'size': 10
                },
                timeout=15
            ).json()
            
            if r.get('status') == 'success':
                for art in r.get('results', []):
                    titulo = art.get('title', '')
                    if titulo:
                        desc = art.get('description', '')
                        noticias.append({
                            'titulo': limpiar_texto(titulo),
                            'descripcion': limpiar_texto(desc),
                            'url': art.get('link', ''),
                            'imagen': art.get('image_url'),
                            'fuente': f"NewsData:{art.get('source_id', 'Unknown')}",
                            'fecha': art.get('pubDate'),
                            'puntaje': calcular_puntaje_viral(titulo, desc)
                        })
        except:
            continue
    
    log(f"NewsData: {len(noticias)} noticias", 'info')
    return noticias

def obtener_gnews():
    """Obtiene noticias de GNews"""
    if not GNEWS_API_KEY:
        return []
    
    noticias = []
    topicos = ['world', 'nation', 'business', 'technology', 'entertainment', 'sports']
    
    for topic in topicos:
        try:
            r = requests.get(
                'https://gnews.io/api/v4/top-headlines',
                params={
                    'apikey': GNEWS_API_KEY,
                    'lang': 'es',
                    'max': 10,
                    'topic': topic
                },
                timeout=15
            ).json()
            
            for art in r.get('articles', []):
                titulo = art.get('title', '')
                if titulo:
                    desc = art.get('description', '')
                    noticias.append({
                        'titulo': limpiar_texto(titulo),
                        'descripcion': limpiar_texto(desc),
                        'url': art.get('url', ''),
                        'imagen': art.get('image'),
                        'fuente': f"GNews:{art.get('source', {}).get('name', 'Unknown')}",
                        'fecha': art.get('publishedAt'),
                        'puntaje': calcular_puntaje_viral(titulo, desc)
                    })
        except:
            continue
    
    log(f"GNews: {len(noticias)} noticias", 'info')
    return noticias

def obtener_rss_latam():
    """Obtiene noticias de RSS LATAM optimizados"""
    feeds = [
        # México
        'https://www.infobae.com/arc/outboundfeeds/rss/mundo/',
        'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada',
        'http://feeds.bbci.co.uk/mundo/rss.xml',
        'https://feeds.france24.com/es/',
        # LATAM específicos
        'https://www.clarin.com/rss/mundo/',
        'https://www.lanacion.com.ar/feed/',
        'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/america/portada',
        'https://www.elespectador.com/feed/',
        'https://www.eluniversal.com.mx/feed/',
        'https://www.eltiempo.com/feed/'
    ]
    
    noticias = []
    
    for feed_url in feeds:
        try:
            r = requests.get(feed_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code != 200:
                continue
            
            feed = feedparser.parse(r.content)
            if not feed or not feed.entries:
                continue
            
            fuente = feed.feed.get('title', 'RSS')[:20]
            
            for entry in feed.entries[:8]:
                titulo = entry.get('title', '')
                if not titulo:
                    continue
                
                # Limpiar título de sufijos
                titulo = re.sub(r'\s*-\s*[^-]*$', '', titulo)
                
                link = entry.get('link', '')
                if not link:
                    continue
                
                desc = entry.get('summary', '') or entry.get('description', '')
                desc = re.sub(r'<[^>]+>', '', desc)
                
                # Extraer imagen
                imagen = None
                if 'media_content' in entry:
                    imagen = entry.media_content[0].get('url')
                elif 'links' in entry:
                    for link_data in entry.links:
                        if link_data.get('type', '').startswith('image/'):
                            imagen = link_data.get('href')
                            break
                
                noticias.append({
                    'titulo': limpiar_texto(titulo),
                    'descripcion': limpiar_texto(desc),
                    'url': link,
                    'imagen': imagen,
                    'fuente': f"RSS:{fuente}",
                    'fecha': entry.get('published'),
                    'puntaje': calcular_puntaje_viral(titulo, desc)
                })
                
        except:
            continue
    
    log(f"RSS LATAM: {len(noticias)} noticias", 'info')
    return noticias

# ═══════════════════════════════════════════════════════════════
# PUBLICACIÓN EN FACEBOOK
# ═══════════════════════════════════════════════════════════════

def publicar_facebook(titulo, texto, imagen_path, hashtags):
    """Publica en Facebook con imagen"""
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales Facebook", 'error')
        return False
    
    # Construir mensaje final
    mensaje = f"{texto}\n\n{hashtags}\n\n🔥 Noticias Virales LATAM 24/7\n📲 Síguenos para más contenido viral"
    
    # Truncar si es necesario
    if len(mensaje) > 2200:
        lineas = texto.split('\n')
        texto_corto = ""
        for linea in lineas:
            if len(texto_corto + linea + "\n") < 1800:
                texto_corto += linea + "\n"
            else:
                break
        mensaje = f"{texto_corto.rstrip()}\n\n[...]\n\n{hashtags}\n\n🔥 Noticias Virales LATAM 24/7"
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
        
        with open(imagen_path, 'rb') as f:
            files = {'file': ('imagen.jpg', f, 'image/jpeg')}
            data = {
                'message': mensaje,
                'access_token': FB_ACCESS_TOKEN
            }
            
            r = requests.post(url, files=files, data=data, timeout=60)
            resultado = r.json()
            
            if 'id' in resultado:
                log(f"✅ Publicado ID: {resultado['id']}", 'exito')
                return True
            else:
                error = resultado.get('error', {}).get('message', 'Unknown')
                log(f"❌ Error Facebook: {error}", 'error')
                return False
                
    except Exception as e:
        log(f"❌ Excepción publicando: {e}", 'error')
        return False

# ═══════════════════════════════════════════════════════════════
# CONTROL DE TIEMPO
# ═══════════════════════════════════════════════════════════════

def verificar_tiempo():
    """Verifica si ha pasado el tiempo mínimo entre publicaciones"""
    estado = cargar_json(ESTADO_PATH, {'ultima_publicacion': None})
    ultima = estado.get('ultima_publicacion')
    
    if not ultima:
        return True
    
    try:
        minutos = (datetime.now() - datetime.fromisoformat(ultima)).total_seconds() / 60
        if minutos < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"⏱️ Esperando... Última hace {minutos:.0f} min", 'info')
            return False
    except:
        pass
    
    return True

# ═══════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def main():
    print("\n" + "="*60)
    print("🚀 BOT NOTICIAS VIRALES LATAM 24/7 - V1.0")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Verificar credenciales
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales Facebook", 'error')
        return False
    
    if not verificar_tiempo():
        return False
    
    # Cargar historial
    historial = cargar_historial()
    log(f"📊 Historial: {len(historial.get('urls', []))} URLs | "
        f"24h: {historial.get('estadisticas', {}).get('ultimas_24h', 0)} posts", 'info')
    
    # Recolectar noticias de todas las fuentes
    todas_noticias = []
    
    if NEWS_API_KEY:
        todas_noticias.extend(obtener_newsapi())
    
    if NEWSDATA_API_KEY and len(todas_noticias) < 20:
        todas_noticias.extend(obtener_newsdata())
    
    if GNEWS_API_KEY and len(todas_noticias) < 30:
        todas_noticias.extend(obtener_gnews())
    
    # Siempre intentar RSS como fallback
    if len(todas_noticias) < 20:
        rss_noticias = obtener_rss_latam()
        if rss_noticias:
            todas_noticias.extend(rss_noticias)
    
    # Deduplicación inicial
    urls_vistas = set()
    titulos_vistos = {}
    noticias_unicas = []
    
    for noticia in todas_noticias:
        url_norm = normalizar_url(noticia.get('url', ''))
        titulo = noticia.get('titulo', '')
        
        if url_norm in urls_vistas:
            continue
        
        # Verificar duplicados temporales
        duplicado = False
        for t_existente in titulos_vistos.keys():
            if calcular_similitud(titulo, t_existente) > 0.85:
                duplicado = True
                break
        
        if duplicado:
            continue
        
        urls_vistas.add(url_norm)
        titulos_vistos[titulo] = url_norm
        noticias_unicas.append(noticia)
    
    log(f"📰 Total únicas: {len(noticias_unicas)} noticias", 'viral')
    
    if not noticias_unicas:
        log("ERROR: No se encontraron noticias", 'error')
        return False
    
    # Ordenar por puntaje viral
    noticias_unicas.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
    
    # Seleccionar mejor noticia válida
    seleccionada = None
    contenido_final = None
    intentos = 0
    max_intentos = min(50, len(noticias_unicas))
    
    for i, noticia in enumerate(noticias_unicas[:max_intentos]):
        url = noticia.get('url', '')
        titulo = noticia.get('titulo', '')
        desc = noticia.get('descripcion', '')
        
        if not url or not titulo:
            continue
        
        intentos += 1
        
        # Verificar duplicados en historial
        duplicada, razon = noticia_ya_publicada(historial, url, titulo, desc)
        if duplicada:
            log(f"   [{i+1}] ❌ Duplicada: {razon}", 'debug')
            continue
        
        # Verificar puntaje mínimo
        if noticia.get('puntaje', 0) < 5:
            log(f"   [{i+1}] ❌ Puntaje bajo ({noticia.get('puntaje', 0)})", 'debug')
            continue
        
        log(f"\n📝 NOTICIA SELECCIONADA: {titulo[:60]}...")
        log(f"   Fuente: {noticia['fuente']} | Puntaje viral: {noticia.get('puntaje', 0)}")
        
        # Extraer contenido
        contenido, _ = extraer_contenido(url)
        
        if contenido and len(contenido) >= 150:
            log(f"   ✅ Contenido extraído: {len(contenido)} chars", 'exito')
            seleccionada = noticia
            contenido_final = contenido
            break
        else:
            # Usar descripción como fallback
            if len(desc) >= 100:
                log(f"   ✅ Usando descripción: {len(desc)} chars", 'exito')
                seleccionada = noticia
                contenido_final = desc
                break
            else:
                log(f"   ⚠️ Contenido insuficiente, probando siguiente...", 'advertencia')
    
    if not seleccionada:
        log("ERROR: No hay noticias válidas después de filtrar", 'error')
        return False
    
    # Construir publicación viral
    publicacion = construir_publicacion_viral(
        seleccionada['titulo'], 
        contenido_final, 
        seleccionada['fuente']
    )
    hashtags = generar_hashtags_virales(seleccionada['titulo'], contenido_final)
    
    # Generar imagen con IA
    log("🎨 Generando imagen viral con IA...", 'imagen')
    imagen_path = None
    
    # Intentar generar imagen con IA
    imagen_path = generar_imagen_ia(seleccionada['titulo'], contenido_final)
    
    # Si falla, usar imagen de la noticia
    if not imagen_path and seleccionada.get('imagen'):
        log("   Intentando imagen original...", 'debug')
        # Aquí podrías descargar la imagen original si quieres
    
    # Si todo falla, crear imagen de respaldo
    if not imagen_path:
        log("   Creando imagen de respaldo...", 'advertencia')
        imagen_path = crear_imagen_backup(seleccionada['titulo'])
    
    if not imagen_path:
        log("ERROR: No se pudo generar imagen", 'error')
        return False
    
    # Publicar en Facebook
    exito = publicar_facebook(
        seleccionada['titulo'],
        publicacion,
        imagen_path,
        hashtags
    )
    
    # Limpiar imagen temporal
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
    except:
        pass
    
    if exito:
        # Guardar en historial
        historial = guardar_historial(
            historial, 
            seleccionada['url'], 
            seleccionada['titulo'], 
            seleccionada.get('descripcion', '')
        )
        
        # Actualizar estado
        guardar_json(ESTADO_PATH, {
            'ultima_publicacion': datetime.now().isoformat()
        })
        
        total = historial.get('estadisticas', {}).get('total_publicadas', 0)
        log(f"✅ ÉXITO - Total histórico: {total} noticias virales publicadas", 'exito')
        return True
    else:
        log("❌ Publicación fallida", 'error')
        return False

if __name__ == "__main__":
    try:
        exit(0 if main() else 1)
    except Exception as e:
        log(f"Error crítico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
