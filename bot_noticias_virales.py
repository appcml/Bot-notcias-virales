#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BOT NOTICIAS VIRALES LATAM 24/7 - V3.2
Generacion de imagenes contextualizadas con analisis semantico
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
from urllib.parse import urlparse, quote

# CONFIGURACION
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
NEWSDATA_API_KEY = os.getenv('NEWSDATA_API_KEY')
GNEWS_API_KEY = os.getenv('GNEWS_API_KEY')
FB_PAGE_ID = os.getenv('FB_PAGE_ID')
FB_ACCESS_TOKEN = os.getenv('FB_ACCESS_TOKEN')

HISTORIAL_PATH = os.getenv('HISTORIAL_PATH', 'data/historial_viral.json')
ESTADO_PATH = os.getenv('ESTADO_PATH', 'data/estado_bot_viral.json')

TIEMPO_ENTRE_PUBLICACIONES = 55
MAX_TITULOS_HISTORIA = 300
UMBRAL_SIMILITUD_TITULO = 0.85
UMBRAL_SIMILITUD_CONTENIDO = 0.75

# Colores para imagenes de backup (formato RGB tuples - SIN rgba)
COLORES_BACKUP = {
    'urgente': (220, 20, 60),      # Crimson
    'negativa': (139, 0, 0),       # DarkRed
    'positiva': (34, 139, 34),     # ForestGreen
    'neutral': (25, 25, 112),      # MidnightBlue
    'deporte': (255, 140, 0),      # DarkOrange
    'politica': (75, 0, 130)       # Indigo
}

# ═══════════════════════════════════════════════════════════════
# BANCO DE DATOS VISUAL CONTEXTUALIZADO
# ═══════════════════════════════════════════════════════════════

PERSONAJES_POLITICOS = {
    'trump': {
        'nombre': 'Donald Trump',
        'atributos': 'blonde hair, red tie, suit, distinctive facial features',
        'escenarios': {
            'default': 'press conference, serious expression',
            'victoria': 'celebrating, raised fist, crowd cheering',
            'controversia': 'defensive posture, media surrounding',
            'judicial': 'courthouse, serious face, legal documents',
            'campaña': 'rally, red cap, supporters'
        }
    },
    'biden': {
        'nombre': 'Joe Biden',
        'atributos': 'white hair, blue suit, aviator sunglasses',
        'escenarios': {
            'default': 'oval office, presidential setting',
            'debate': 'podium, serious debate stance',
            'crisis': 'emergency meeting, concerned expression'
        }
    },
    'amlo': {
        'nombre': 'Andres Manuel Lopez Obrador',
        'atributos': 'gray hair, casual suit, morning conference style',
        'escenarios': {
            'default': 'mañanera podium, mexican flag background',
            'protesta': 'addressing crowd, passionate gesture',
            'crisis': 'serious expression, emergency setting'
        }
    },
    'milei': {
        'nombre': 'Javier Milei',
        'atributos': 'wild hair, sideburns, chainsaw, aggressive expression',
        'escenarios': {
            'default': 'chainsaw in hand, economic reform symbolism',
            'congreso': 'argentine congress, intense debate',
            'crisis': 'shouting, passionate gesture, dollar bills flying'
        }
    },
    'petro': {
        'nombre': 'Gustavo Petro',
        'atributos': 'glasses, formal suit, serious demeanor',
        'escenarios': {
            'default': 'colombian presidential palace, formal setting',
            'protesta': 'street protest, raised fist',
            'paz': 'peace agreement signing, handshake'
        }
    },
    'boric': {
        'nombre': 'Gabriel Boric',
        'atributos': 'young, beard, casual formal style',
        'escenarios': {
            'default': 'la moneda palace, chilean flag',
            'reforma': 'constitutional convention, debate',
            'crisis': 'student protest background, concerned'
        }
    },
    'maduro': {
        'nombre': 'Nicolas Maduro',
        'atributos': 'mustache, military uniform, red beret',
        'escenarios': {
            'default': 'miraflores palace, military backdrop',
            'crisis': 'economic chaos, bolivar bills, protest',
            'internacional': 'diplomatic meeting, controversial'
        }
    },
    'lula': {
        'nombre': 'Lula da Silva',
        'atributos': 'white beard, worker style, red star',
        'escenarios': {
            'default': 'planalto palace, brazilian flag',
            'trabajador': 'factory visit, worker uniform',
            'justicia': 'courthouse, legal battle imagery'
        }
    },
    'zelensky': {
        'nombre': 'Volodimir Zelensky',
        'atributos': 'green military shirt, beard, tired expression',
        'escenarios': {
            'default': 'bunker, military maps, ukrainian flag',
            'guerra': 'destroyed city background, determined',
            'diplomacia': 'international summit, pleading expression'
        }
    },
    'putin': {
        'nombre': 'Vladimir Putin',
        'atributos': 'serious face, suit, kremlin background',
        'escenarios': {
            'default': 'kremlin, long table, power pose',
            'guerra': 'military command center, maps',
            'tension': 'nuclear threat symbolism, red phone'
        }
    },
    'bolsonaro': {
        'nombre': 'Jair Bolsonaro',
        'atributos': 'gray hair, military background, controversial',
        'escenarios': {
            'default': 'brasilia, military supporters',
            'crisis': 'amazon fire background, controversy',
            'electoral': 'election dispute, ballot boxes'
        }
    }
}

EVENTOS_DEPORTIVOS = {
    'futbol': {
        'elementos': 'soccer ball, stadium, goal net, green field',
        'emociones': {
            'gol': 'player celebrating, crowd going wild, scoreboard',
            'lesion': 'medical staff, stretcher, concerned teammates',
            'traspaso': 'signing contract, new jersey, press conference',
            'final': 'trophy, confetti, champagne celebration',
            'derrota': 'player crying, head in hands, empty stadium'
        }
    },
    'basquet': {
        'elementos': 'basketball, court, hoop, jersey',
        'emociones': {
            'canasta': 'dunking, hanging on rim, crowd explosion',
            'victoria': 'team celebrating, trophy lift',
            'lesion': 'knee pain, medical timeout'
        }
    },
    'tenis': {
        'elementos': 'tennis racket, court, net, white outfit',
        'emociones': {
            'punto': 'fist pump, intense focus',
            'victoria': 'falling to knees, grand slam trophy',
            'derrota': 'broken racket, frustration'
        }
    },
    'beisbol': {
        'elementos': 'baseball bat, diamond, glove, stadium lights',
        'emociones': {
            'homerun': 'bat flip, rounding bases, fireworks',
            'strikeout': 'pitcher celebration, batter disappointment'
        }
    },
    'boxeo': {
        'elementos': 'boxing gloves, ring, ropes, spotlight',
        'emociones': {
            'nocaut': 'knockout punch, referee counting, fallen opponent',
            'victoria': 'belt raised, blood and sweat'
        }
    }
}

EVENTOS_CRISIS = {
    'protesta': {
        'elementos': 'crowd with signs, smoke, police line, raised fists',
        'intensidad': {
            'alta': 'tear gas, fire, chaos, running people',
            'media': 'peaceful march, banners, chanting',
            'baja': 'sit-in, signs, organized demonstration'
        }
    },
    'desastre_natural': {
        'elementos': 'flooded streets, destroyed buildings, rescue teams',
        'tipo': {
            'terremoto': 'collapsed buildings, cracks in ground, panic',
            'huracan': 'flying debris, flooded streets, strong winds',
            'incendio': 'forest fire, smoke clouds, firefighters',
            'inundacion': 'submerged cars, rescue boats, rain'
        }
    },
    'economica': {
        'elementos': 'stock market charts, crashing graphs, worried traders',
        'tipo': {
            'inflacion': 'empty wallets, rising prices, supermarket shelves',
            'devaluacion': 'falling currency, exchange house, worried people',
            'crisis_bancaria': 'closed banks, ATM lines, protests'
        }
    },
    'crimen': {
        'elementos': 'police tape, forensic team, flashing lights',
        'tipo': {
            'narco': 'seized drugs, armed police, luxury cars',
            'homicidio': 'crime scene, evidence markers, detectives',
            'secuestro': 'ransom note, tactical team, rescue operation'
        }
    }
}

BANDERAS_SIMBOLOS = {
    'mexico': 'green white red flag, eagle snake cactus',
    'argentina': 'light blue white flag, sun of may',
    'colombia': 'yellow blue red flag',
    'chile': 'red white blue flag, star',
    'peru': 'red white red flag',
    'venezuela': 'yellow blue red flag, stars',
    'brasil': 'green yellow flag, blue globe',
    'eeuu': 'stars and stripes, american flag',
    'ucrania': 'blue yellow flag',
    'rusia': 'white blue red flag'
}

# ═══════════════════════════════════════════════════════════════
# ANALISIS SEMANTICO AVANZADO
# ═══════════════════════════════════════════════════════════════

class AnalizadorNoticias:
    def __init__(self):
        self.personajes = PERSONAJES_POLITICOS
        self.deportes = EVENTOS_DEPORTIVOS
        self.crisis = EVENTOS_CRISIS
        self.banderas = BANDERAS_SIMBOLOS
    
    def analizar(self, titulo, contenido, descripcion=""):
        texto_completo = f"{titulo} {descripcion} {contenido[:500]}".lower()
        
        resultado = {
            'personaje_principal': None,
            'tipo_evento': None,
            'deporte': None,
            'pais': None,
            'emocion': 'neutral',
            'escenario': 'default',
            'elementos_extra': []
        }
        
        # Detectar personaje politico
        for key, data in self.personajes.items():
            if key in texto_completo or data['nombre'].lower() in texto_completo:
                resultado['personaje_principal'] = key
                resultado['escenario'] = self._detectar_escenario_personaje(key, texto_completo)
                break
        
        # Detectar deporte
        for key, data in self.deportes.items():
            if key in texto_completo:
                resultado['deporte'] = key
                resultado['emocion'] = self._detectar_emocion_deporte(texto_completo)
                break
        
        # Detectar crisis
        for key, data in self.crisis.items():
            if key in texto_completo or any(s in texto_completo for s in self._get_sinonimos_crisis(key)):
                resultado['tipo_evento'] = key
                resultado['intensidad'] = self._detectar_intensidad(texto_completo)
                break
        
        # Detectar pais
        for key in self.banderas.keys():
            if key in texto_completo:
                resultado['pais'] = key
                break
        
        if not resultado['deporte']:
            resultado['emocion'] = self._detectar_emocion_general(texto_completo)
        
        return resultado
    
    def _detectar_escenario_personaje(self, personaje_key, texto):
        escenarios = self.personajes[personaje_key]['escenarios']
        palabras_clave = {
            'victoria': ['gana', 'triunfo', 'victoria', 'electo', 'ganador', 'celebra'],
            'controversia': ['escandalo', 'polemica', 'critica', 'denuncia', 'juicio', 'impeachment'],
            'judicial': ['tribunal', 'corte', 'juez', 'sentencia', 'fiscal', 'investigacion'],
            'campaña': ['campaña', 'rally', 'votantes', 'eleccion', 'urnas'],
            'crisis': ['crisis', 'emergencia', 'urgente', 'grave', 'escandalo']
        }
        for escenario, palabras in palabras_clave.items():
            if any(p in texto for p in palabras):
                return escenario if escenario in escenarios else 'default'
        return 'default'
    
    def _detectar_emocion_deporte(self, texto):
        emociones = {
            'gol': ['gol', 'anota', 'marcador', 'triunfo', 'victoria'],
            'lesion': ['lesion', 'lesionado', 'medico', 'ambulancia', 'retirado'],
            'traspaso': ['fichaje', 'traspaso', 'contrato', 'millones', 'nuevo equipo'],
            'final': ['final', 'campeon', 'trofeo', 'titulo', 'copa'],
            'derrota': ['derrota', 'perdio', 'eliminado', 'fracaso', 'llanto']
        }
        for emocion, palabras in emociones.items():
            if any(p in texto for p in palabras):
                return emocion
        return 'default'
    
    def _detectar_intensidad(self, texto):
        alta = ['violento', 'muertos', 'heridos', 'grave', 'emergencia', 'masacre']
        media = ['protesta', 'marcha', 'manifestacion', 'bloqueo']
        if any(p in texto for p in alta):
            return 'alta'
        elif any(p in texto for p in media):
            return 'media'
        return 'baja'
    
    def _detectar_emocion_general(self, texto):
        positivas = ['celebra', 'triunfo', 'exito', 'logro', 'avance', 'paz']
        negativas = ['tragedia', 'crisis', 'muerte', 'violencia', 'guerra', 'corrupcion']
        urgentes = ['urgente', 'alerta', 'emergencia', 'ultima hora', 'breaking']
        if any(p in texto for p in urgentes):
            return 'urgente'
        elif any(p in texto for p in negativas):
            return 'negativa'
        elif any(p in texto for p in positivas):
            return 'positiva'
        return 'neutral'
    
    def _get_sinonimos_crisis(self, tipo):
        sinonimos = {
            'protesta': ['manifestacion', 'marcha', 'disturbios', 'disturbio', 'bloqueo', 'huelga'],
            'desastre_natural': ['terremoto', 'sismo', 'huracan', 'inundacion', 'incendio', 'tsunami'],
            'economica': ['crisis economica', 'recesion', 'inflacion', 'devaluacion', 'quiebra'],
            'crimen': ['asesinato', 'homicidio', 'secuestro', 'narco', 'trafico', 'robo']
        }
        return sinonimos.get(tipo, [])

# ═══════════════════════════════════════════════════════════════
# GENERADOR DE PROMPTS
# ═══════════════════════════════════════════════════════════════

class GeneradorPrompts:
    def __init__(self):
        self.analizador = AnalizadorNoticias()
    
    def generar(self, titulo, contenido, descripcion=""):
        analisis = self.analizador.analizar(titulo, contenido, descripcion)
        
        if analisis['personaje_principal']:
            return self._prompt_personaje(analisis, titulo)
        elif analisis['deporte']:
            return self._prompt_deporte(analisis, titulo)
        elif analisis['tipo_evento']:
            return self._prompt_crisis(analisis, titulo)
        else:
            return self._prompt_generico(analisis, titulo)
    
    def _prompt_personaje(self, analisis, titulo):
        personaje = PERSONAJES_POLITICOS[analisis['personaje_principal']]
        escenario_key = analisis['escenario']
        escenario_desc = personaje['escenarios'].get(escenario_key, personaje['escenarios']['default'])
        atributos = personaje['atributos']
        nombre = personaje['nombre']
        
        contexto_pais = ""
        if analisis['pais']:
            bandera = BANDERAS_SIMBOLOS.get(analisis['pais'], '')
            contexto_pais = f", {bandera} in background"
        
        emocion_desc = self._get_emocion_desc(analisis['emocion'])
        
        return (
            f"breaking news photography of {nombre}, {atributos}, "
            f"{escenario_desc}{contexto_pais}, {emocion_desc}, "
            f"professional photojournalism, dramatic lighting, news broadcast quality, "
            f"high detail, 4k, front page newspaper style"
        )
    
    def _prompt_deporte(self, analisis, titulo):
        deporte_data = EVENTOS_DEPORTIVOS[analisis['deporte']]
        emocion_key = analisis['emocion']
        escena = deporte_data['emociones'].get(emocion_key, f"intense {analisis['deporte']} action")
        elementos = deporte_data['elementos']
        
        contexto = ""
        if analisis['pais']:
            contexto = f", {BANDERAS_SIMBOLOS.get(analisis['pais'], '')} visible"
        
        return (
            f"sports breaking news photography, {escena}, {elementos}{contexto}, "
            f"dynamic action shot, professional sports photography, "
            f"stadium atmosphere, dramatic moment, high energy, 4k, ESPN style"
        )
    
    def _prompt_crisis(self, analisis, titulo):
        crisis_data = EVENTOS_CRISIS[analisis['tipo_evento']]
        
        if analisis['tipo_evento'] == 'desastre_natural':
            subtipo = self._detectar_subtipo_desastre(titulo)
            escena = crisis_data['tipo'].get(subtipo, crisis_data['elementos'])
        elif analisis['tipo_evento'] == 'economica':
            subtipo = self._detectar_subtipo_economia(titulo)
            escena = crisis_data['tipo'].get(subtipo, crisis_data['elementos'])
        elif analisis['tipo_evento'] == 'crimen':
            subtipo = self._detectar_subtipo_crimen(titulo)
            escena = crisis_data['tipo'].get(subtipo, crisis_data['elementos'])
        else:
            intensidad = analisis.get('intensidad', 'media')
            escena = crisis_data['intensidad'].get(intensidad, crisis_data['elementos'])
        
        contexto = ""
        if analisis['pais']:
            contexto = f", location: {analisis['pais']}, {BANDERAS_SIMBOLOS.get(analisis['pais'], '')}"
        
        return (
            f"breaking news documentary photography, {escena}{contexto}, "
            f"photojournalism style, urgent atmosphere, dramatic lighting, "
            f"news front page quality, high impact, 4k, Reuters style"
        )
    
    def _prompt_generico(self, analisis, titulo):
        estilos = {
            'urgente': 'breaking news red alert style, urgent typography elements',
            'negativa': 'dramatic shadows, serious tone, documentary style',
            'positiva': 'bright lighting, celebration atmosphere, hopeful',
            'neutral': 'professional newsroom style, balanced composition'
        }
        
        contexto = ""
        if analisis['pais']:
            contexto = f", {BANDERAS_SIMBOLOS.get(analisis['pais'], '')} in composition"
        
        tema = self._extraer_tema_principal(titulo)
        
        return (
            f"breaking news illustration, {tema}{contexto}, "
            f"{estilos.get(analisis['emocion'], estilos['neutral'])}, "
            f"professional news broadcast graphic, high quality, 4k"
        )
    
    def _get_emocion_desc(self, emocion):
        descripciones = {
            'urgente': 'intense serious expression, urgent atmosphere',
            'negativa': 'concerned expression, serious demeanor',
            'positiva': 'celebrating, triumphant expression',
            'neutral': 'professional demeanor, neutral expression'
        }
        return descripciones.get(emocion, descripciones['neutral'])
    
    def _detectar_subtipo_desastre(self, texto):
        texto = texto.lower()
        if any(p in texto for p in ['terremoto', 'sismo', 'temblor']):
            return 'terremoto'
        elif any(p in texto for p in ['huracan', 'ciclon', 'tormenta']):
            return 'huracan'
        elif any(p in texto for p in ['incendio', 'fuego', 'bosque']):
            return 'incendio'
        elif any(p in texto for p in ['inundacion', 'lluvia', 'desbordamiento']):
            return 'inundacion'
        return 'default'
    
    def _detectar_subtipo_economia(self, texto):
        texto = texto.lower()
        if any(p in texto for p in ['inflacion', 'precios', 'supermercado']):
            return 'inflacion'
        elif any(p in texto for p in ['devaluacion', 'dolar', 'cambio']):
            return 'devaluacion'
        elif any(p in texto for p in ['banco', 'quiebra', 'corralito']):
            return 'crisis_bancaria'
        return 'default'
    
    def _detectar_subtipo_crimen(self, texto):
        texto = texto.lower()
        if any(p in texto for p in ['narco', 'droga', 'cartel', 'trafico']):
            return 'narco'
        elif any(p in texto for p in ['secuestro', 'rapto', 'rescate']):
            return 'secuestro'
        return 'homicidio'
    
    def _extraer_tema_principal(self, titulo):
        stop_words = {'el', 'la', 'de', 'y', 'en', 'un', 'una', 'los', 'las', 'del', 'al', 'con'}
        palabras = [p for p in titulo.lower().split() if p not in stop_words and len(p) > 3]
        return ' '.join(palabras[:5]) if palabras else "breaking news"

# ═══════════════════════════════════════════════════════════════
# FUNCIONES UTILITARIAS
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
# EXTRACCION Y GENERACION DE IMAGENES
# ═══════════════════════════════════════════════════════════════

def extraer_contenido(url):
    if not url: 
        return None, None
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=12)
        soup = BeautifulSoup(r.content, 'html.parser')
        for elem in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            elem.decompose()
        article = soup.find('article')
        if article:
            parrafos = article.find_all('p')
            if len(parrafos) >= 2:
                texto = ' '.join([limpiar_texto(p.get_text()) for p in parrafos if len(p.get_text()) > 30])
                if len(texto) > 200:
                    return texto[:1500], None
        for clase in ['article-content', 'entry-content', 'post-content', 'content']:
            elem = soup.find(class_=lambda x: x and clase in x.lower())
            if elem:
                parrafos = elem.find_all('p')
                if len(parrafos) >= 2:
                    texto = ' '.join([limpiar_texto(p.get_text()) for p in parrafos if len(p.get_text()) > 30])
                    if len(texto) > 200:
                        return texto[:1500], None
        return None, None
    except:
        return None, None

def generar_imagen_contextual(titulo, contenido, descripcion=""):
    """Intenta generar imagen con Pollinations.ai"""
    generador = GeneradorPrompts()
    prompt = generador.generar(titulo, contenido, descripcion)
    
    log(f"Prompt: {prompt[:100]}...", 'imagen')
    
    try:
        prompt_encoded = quote(prompt)
        seed = random.randint(1000, 9999)
        url = f"https://image.pollinations.ai/prompt/{prompt_encoded}?width=1200&height=630&nologo=true&seed={seed}&enhance=true"
        
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=50)
        
        if response.status_code == 200:
            img_path = f'/tmp/viral_{generar_hash(titulo)}_{seed}.jpg'
            with open(img_path, 'wb') as f:
                f.write(response.content)
            
            if os.path.getsize(img_path) > 15000:
                log(f"Imagen IA generada: {img_path}", 'exito')
                return img_path, prompt
            else:
                os.remove(img_path)
                log("Imagen muy pequeña, usando backup", 'advertencia')
                return None, prompt
        log(f"Error HTTP {response.status_code} de Pollinations", 'error')
        return None, prompt
    except Exception as e:
        log(f"Error generando imagen: {e}", 'error')
        return None, prompt

def crear_imagen_backup(titulo, analisis_contexto=None):
    """Crea imagen de respaldo cuando la IA falla - CORREGIDO"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Seleccionar color segun contexto
        emocion = 'neutral'
        if analisis_contexto:
            emocion = analisis_contexto.get('emocion', 'neutral')
            if analisis_contexto.get('deporte'):
                emocion = 'deporte'
            elif analisis_contexto.get('personaje_principal'):
                emocion = 'politica'
        
        color_fondo = COLORES_BACKUP.get(emocion, COLORES_BACKUP['neutral'])
        
        # Crear imagen
        img = Image.new('RGB', (1200, 630), color=color_fondo)
        draw = ImageDraw.Draw(img)
        
        # Cargar fuentes
        try:
            font_titulo = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
            font_contexto = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        except:
            try:
                font_titulo = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 40)
                font_sub = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 22)
                font_contexto = font_sub
            except:
                font_titulo = ImageFont.load_default()
                font_sub = font_contexto = font_titulo
        
        # Barra superior e inferior (blanco RGB)
        draw.rectangle([(0, 0), (1200, 12)], fill=(255, 255, 255))
        draw.rectangle([(0, 618), (1200, 630)], fill=(255, 255, 255))
        
        # Info de contexto arriba
        y_pos = 30
        if analisis_contexto:
            info_lineas = []
            if analisis_contexto.get('personaje_principal'):
                nombre = PERSONAJES_POLITICOS[analisis_contexto['personaje_principal']]['nombre']
                info_lineas.append(f"PERSONAJE: {nombre}")
            if analisis_contexto.get('pais'):
                info_lineas.append(f"PAIS: {analisis_contexto['pais'].upper()}")
            if analisis_contexto.get('deporte'):
                info_lineas.append(f"DEPORTE: {analisis_contexto['deporte'].upper()}")
            if analisis_contexto.get('tipo_evento'):
                info_lineas.append(f"EVENTO: {analisis_contexto['tipo_evento'].upper()}")
            
            if info_lineas:
                texto_info = " | ".join(info_lineas)
                # Color gris claro (RGB) - CORREGIDO
                draw.text((50, y_pos), texto_info, font=font_contexto, fill=(200, 200, 200))
                y_pos = 60
        
        # Titulo centrado con wrap
        import textwrap
        titulo_wrapped = textwrap.fill(titulo[:130], width=30)
        lineas = titulo_wrapped.split('\n')
        y_start = ((630 - len(lineas) * 48) // 2) + (y_pos // 2)
        
        # Dibujar cada linea con sombra
        for i, linea in enumerate(lineas):
            y = y_start + (i * 48)
            # Sombra (negro RGB)
            draw.text((52, y+2), linea, font=font_titulo, fill=(0, 0, 0))
            # Texto (blanco RGB)
            draw.text((50, y), linea, font=font_titulo, fill=(255, 255, 255))
        
        # Footer - CORREGIDO (sin rgba)
        draw.text((50, 560), "NOTICIAS VIRALES LATAM 24/7", font=font_sub, fill=(255, 255, 255))
        draw.text((50, 590), f"{datetime.now().strftime('%d/%m/%Y %H:%M')} | Informacion que importa", 
                 font=font_contexto, fill=(180, 180, 180))
        
        # Guardar
        img_path = f'/tmp/viral_backup_{generar_hash(titulo[:50])}.jpg'
        img.save(img_path, 'JPEG', quality=90)
        
        log(f"Imagen backup creada: {img_path}", 'exito')
        return img_path
        
    except Exception as e:
        log(f"Error creando imagen backup: {e}", 'error')
        return None

# ═══════════════════════════════════════════════════════════════
# PUBLICACION
# ═══════════════════════════════════════════════════════════════

def dividir_parrafos_viral(texto):
    if not texto:
        return []
    oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', texto) if len(o.strip()) > 15]
    if len(oraciones) < 2:
        return [texto[:250] + "..."] if len(texto) > 80 else []
    parrafos = []
    actual = []
    palabras = 0
    for i, oracion in enumerate(oraciones[:10]):
        actual.append(oracion)
        palabras += len(oracion.split())
        if palabras >= 20 or i == len(oraciones) - 1 or len(actual) >= 2:
            if len(' '.join(actual).split()) >= 8:
                parrafos.append(' '.join(actual))
            actual = []
            palabras = 0
    return parrafos[:4]

def construir_publicacion_viral(titulo, contenido, fuente):
    titulo_limpio = limpiar_texto(titulo)
    parrafos = dividir_parrafos_viral(contenido)
    if len(parrafos) < 2:
        oraciones = [o.strip() for o in re.split(r'(?<=[.!?])\s+', contenido) if len(o.strip()) > 15]
        parrafos = [' '.join(oraciones[i:i+2]) for i in range(0, min(5, len(oraciones)), 2)]
    
    CTAS = [
        "QUE OPINAS? Dejalo en los comentarios!",
        "COMPARTE si crees que esto debe saberse",
        "Siguenos para mas noticias virales de LATAM",
        "ULTIMO MINUTO - Informacion en constante actualizacion"
    ]
    
    lineas = [titulo_limpio, "", "-" * 20, ""]
    for i, parrafo in enumerate(parrafos):
        lineas.append(parrafo)
        if i < len(parrafos) - 1:
            lineas.append("")
    lineas.extend(["", "-" * 20, "", random.choice(CTAS), "", f"Fuente: {fuente}", "Noticias Virales LATAM 24/7"])
    return '\n'.join(lineas)

def generar_hashtags_virales(titulo, contenido):
    txt = f"{titulo} {contenido}".lower()
    hashtags = ['#NoticiasVirales', '#LATAM', '#UltimaHora']
    temas = {
        r'mexico': '#Mexico', r'argentina': '#Argentina', r'colombia': '#Colombia',
        r'chile': '#Chile', r'peru': '#Peru', r'venezuela': '#Venezuela', r'brasil': '#Brasil',
        r'trump': '#Trump', r'biden': '#Biden', r'politica': '#Politica',
        r'futbol': '#Futbol', r'deporte': '#Deportes', r'economia': '#Economia'
    }
    for patron, hashtag in temas.items():
        if re.search(patron, txt) and hashtag not in hashtags:
            hashtags.append(hashtag)
    hashtags.extend(['#Viral', '#Tendencia'])
    return ' '.join(hashtags[:7])

# ═══════════════════════════════════════════════════════════════
# HISTORIAL
# ═══════════════════════════════════════════════════════════════

def cargar_historial():
    default = {
        'urls': [], 'urls_normalizadas': [], 'hashes': [], 'timestamps': [],
        'titulos': [], 'descripciones': [],
        'estadisticas': {'total_publicadas': 0, 'ultimas_24h': 0}
    }
    h = cargar_json(HISTORIAL_PATH, default)
    for k in default:
        if k not in h:
            h[k] = default[k]
    limpiar_historial_antiguo(h)
    return h

def limpiar_historial_antiguo(h):
    try:
        ahora = datetime.now()
        indices_validos = []
        for i, ts in enumerate(h.get('timestamps', [])):
            try:
                fecha = datetime.fromisoformat(ts)
                if (ahora - fecha).days < 7:
                    indices_validos.append(i)
            except:
                continue
        for key in ['urls', 'urls_normalizadas', 'hashes', 'timestamps', 'titulos', 'descripciones']:
            if key in h and isinstance(h[key], list):
                h[key] = [h[key][i] for i in indices_validos if i < len(h[key])]
        count_24h = sum(1 for ts in h.get('timestamps', []) if (ahora - datetime.fromisoformat(ts)).total_seconds() < 86400)
        h['estadisticas']['ultimas_24h'] = count_24h
    except Exception as e:
        log(f"Error limpiando historial: {e}", 'error')

def noticia_ya_publicada(h, url, titulo, desc=""):
    if not h:
        return False, "sin_historial"
    url_norm = normalizar_url(url)
    hash_titulo = generar_hash(titulo)
    if es_titulo_generico(titulo):
        return True, "titulo_generico"
    if url_norm in h.get('urls_normalizadas', []):
        return True, "url_duplicada"
    if hash_titulo in h.get('hashes', []):
        return True, "hash_duplicado"
    for titulo_hist in h.get('titulos', []):
        sim = calcular_similitud(titulo, titulo_hist)
        if sim >= UMBRAL_SIMILITUD_TITULO:
            return True, f"similitud_titulo_{sim:.2f}"
    if desc:
        for desc_hist in h.get('descripciones', []):
            sim = calcular_similitud(desc[:150], desc_hist[:150])
            if sim >= UMBRAL_SIMILITUD_CONTENIDO:
                return True, f"similitud_contenido_{sim:.2f}"
    return False, "nuevo"

def guardar_historial(h, url, titulo, desc=""):
    url_norm = normalizar_url(url)
    hash_t = generar_hash(titulo)
    h['urls'].append(url)
    h['urls_normalizadas'].append(url_norm)
    h['hashes'].append(hash_t)
    h['timestamps'].append(datetime.now().isoformat())
    h['titulos'].append(titulo)
    h['descripciones'].append(desc[:400] if desc else "")
    h['estadisticas']['total_publicadas'] += 1
    for key in ['urls', 'urls_normalizadas', 'hashes', 'timestamps', 'titulos', 'descripciones']:
        if len(h[key]) > MAX_TITULOS_HISTORIA:
            h[key] = h[key][-MAX_TITULOS_HISTORIA:]
    guardar_json(HISTORIAL_PATH, h)
    return h

# ═══════════════════════════════════════════════════════════════
# FUENTES
# ═══════════════════════════════════════════════════════════════

def obtener_newsapi():
    if not NEWS_API_KEY:
        return []
    noticias = []
    queries = ['Trump', 'Biden', 'Mexico AMLO', 'Argentina Milei', 'Colombia Petro', 'Chile Boric', 'Venezuela Maduro', 'Ucrania Zelensky']
    for query in queries:
        try:
            r = requests.get('https://newsapi.org/v2/everything', 
                           params={'apiKey': NEWS_API_KEY, 'q': query, 'language': 'es', 'sortBy': 'publishedAt', 'pageSize': 3},
                           timeout=10).json()
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
    if not NEWSDATA_API_KEY:
        return []
    noticias = []
    for cat in ['world', 'politics', 'business', 'entertainment', 'sports']:
        try:
            r = requests.get('https://newsdata.io/api/1/news',
                           params={'apikey': NEWSDATA_API_KEY, 'language': 'es', 'category': cat, 'size': 8},
                           timeout=10).json()
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
    if not GNEWS_API_KEY:
        return []
    noticias = []
    for topic in ['world', 'nation', 'business', 'technology', 'entertainment', 'sports']:
        try:
            r = requests.get('https://gnews.io/api/v4/top-headlines',
                           params={'apikey': GNEWS_API_KEY, 'lang': 'es', 'max': 8, 'topic': topic},
                           timeout=10).json()
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
    feeds = [
        'https://www.infobae.com/arc/outboundfeeds/rss/mundo/',
        'https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional/portada',
        'http://feeds.bbci.co.uk/mundo/rss.xml',
        'https://www.clarin.com/rss/mundo/',
        'https://www.lanacion.com.ar/feed/'
    ]
    noticias = []
    for feed_url in feeds:
        try:
            r = requests.get(feed_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
            if r.status_code != 200:
                continue
            feed = feedparser.parse(r.content)
            if not feed or not feed.entries:
                continue
            fuente = feed.feed.get('title', 'RSS')[:20]
            for entry in feed.entries[:6]:
                titulo = entry.get('title', '')
                if not titulo:
                    continue
                titulo = re.sub(r'\s*-\s*[^-]*$', '', titulo)
                link = entry.get('link', '')
                if not link:
                    continue
                desc = entry.get('summary', '') or entry.get('description', '')
                desc = re.sub(r'<[^>]+>', '', desc)
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
    log(f"RSS: {len(noticias)} noticias", 'info')
    return noticias

# ═══════════════════════════════════════════════════════════════
# PUBLICACION FACEBOOK
# ═══════════════════════════════════════════════════════════════

def publicar_facebook(titulo, texto, imagen_path, hashtags):
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales Facebook", 'error')
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
        with open(imagen_path, 'rb') as f:
            files = {'file': ('imagen.jpg', f, 'image/jpeg')}
            data = {'message': mensaje, 'access_token': FB_ACCESS_TOKEN}
            r = requests.post(url, files=files, data=data, timeout=50)
            resultado = r.json()
            if 'id' in resultado:
                log(f"Publicado ID: {resultado['id']}", 'exito')
                return True
            else:
                log(f"Error Facebook: {resultado.get('error', {}).get('message', 'Unknown')}", 'error')
                return False
    except Exception as e:
        log(f"Excepcion publicando: {e}", 'error')
        return False

def verificar_tiempo():
    estado = cargar_json(ESTADO_PATH, {'ultima_publicacion': None})
    ultima = estado.get('ultima_publicacion')
    run_number = os.getenv('GITHUB_RUN_NUMBER')
    if run_number:
        return True
    if not ultima:
        return True
    try:
        minutos = (datetime.now() - datetime.fromisoformat(ultima)).total_seconds() / 60
        if minutos < TIEMPO_ENTRE_PUBLICACIONES:
            log(f"Esperando... Ultima hace {minutos:.0f} min", 'info')
            return False
    except:
        pass
    return True

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("\n" + "="*60)
    print("BOT NOTICIAS VIRALES LATAM 24/7 - V3.2")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    if not FB_PAGE_ID or not FB_ACCESS_TOKEN:
        log("ERROR: Faltan credenciales Facebook", 'error')
        return False
    
    if not verificar_tiempo():
        return True
    
    historial = cargar_historial()
    stats = historial.get('estadisticas', {})
    log(f"Historial: {len(historial.get('urls', []))} URLs | 24h: {stats.get('ultimas_24h', 0)} posts", 'info')
    
    todas_noticias = []
    if NEWS_API_KEY:
        todas_noticias.extend(obtener_newsapi())
    if NEWSDATA_API_KEY and len(todas_noticias) < 25:
        todas_noticias.extend(obtener_newsdata())
    if GNEWS_API_KEY and len(todas_noticias) < 35:
        todas_noticias.extend(obtener_gnews())
    if len(todas_noticias) < 25:
        rss = obtener_rss_latam()
        if rss:
            todas_noticias.extend(rss)
    
    urls_vistas = set()
    titulos_vistos = {}
    noticias_unicas = []
    for noticia in todas_noticias:
        url_norm = normalizar_url(noticia.get('url', ''))
        titulo = noticia.get('titulo', '')
        if url_norm in urls_vistas:
            continue
        duplicado = False
        for t_existente in titulos_vistos.keys():
            if calcular_similitud(titulo, t_existente) > 0.88:
                duplicado = True
                break
        if duplicado:
            continue
        urls_vistas.add(url_norm)
        titulos_vistos[titulo] = url_norm
        noticias_unicas.append(noticia)
    
    log(f"Total unicas: {len(noticias_unicas)} noticias", 'info')
    if not noticias_unicas:
        log("ERROR: No se encontraron noticias", 'error')
        return False
    
    noticias_unicas.sort(key=lambda x: (x.get('puntaje', 0), x.get('fecha', '')), reverse=True)
    
    seleccionada = None
    contenido_final = None
    analizador = AnalizadorNoticias()
    
    for i, noticia in enumerate(noticias_unicas[:40]):
        url = noticia.get('url', '')
        titulo = noticia.get('titulo', '')
        desc = noticia.get('descripcion', '')
        if not url or not titulo:
            continue
        duplicada, razon = noticia_ya_publicada(historial, url, titulo, desc)
        if duplicada:
            continue
        if noticia.get('puntaje', 0) < 8:
            continue
        
        log(f"\nNOTICIA: {titulo[:55]}...")
        contenido, _ = extraer_contenido(url)
        if contenido and len(contenido) >= 120:
            seleccionada = noticia
            contenido_final = contenido
            break
        elif len(desc) >= 80:
            seleccionada = noticia
            contenido_final = desc
            break
    
    if not seleccionada:
        log("ERROR: No hay noticias validas", 'error')
        return False
    
    log("Analizando contexto...", 'imagen')
    contexto = analizador.analizar(seleccionada['titulo'], contenido_final, seleccionada.get('descripcion', ''))
    log(f"Contexto: Personaje={contexto.get('personaje_principal')}, Pais={contexto.get('pais')}", 'imagen')
    
    publicacion = construir_publicacion_viral(seleccionada['titulo'], contenido_final, seleccionada['fuente'])
    hashtags = generar_hashtags_virales(seleccionada['titulo'], contenido_final)
    
    log("Generando imagen...", 'imagen')
    imagen_path, prompt_usado = generar_imagen_contextual(seleccionada['titulo'], contenido_final, seleccionada.get('descripcion', ''))
    
    if not imagen_path:
        log("IA fallo, creando imagen backup...", 'advertencia')
        imagen_path = crear_imagen_backup(seleccionada['titulo'], contexto)
    
    if not imagen_path:
        log("ERROR: No se pudo generar ninguna imagen", 'error')
        return False
    
    if prompt_usado:
        log(f"Prompt usado: {prompt_usado[:80]}...", 'imagen')
    
    exito = publicar_facebook(seleccionada['titulo'], publicacion, imagen_path, hashtags)
    
    try:
        if os.path.exists(imagen_path):
            os.remove(imagen_path)
    except:
        pass
    
    if exito:
        historial = guardar_historial(historial, seleccionada['url'], seleccionada['titulo'], seleccionada.get('descripcion', ''))
        estado = {
            'ultima_publicacion': datetime.now().isoformat(),
            'github_run_number': os.getenv('GITHUB_RUN_NUMBER'),
            'ultima_noticia': seleccionada['titulo'][:50]
        }
        guardar_json(ESTADO_PATH, estado)
        total = historial.get('estadisticas', {}).get('total_publicadas', 0)
        log(f"EXITO - Total: {total} noticias publicadas", 'exito')
        return True
    else:
        log("Publicacion fallida", 'error')
        return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        log(f"Error critico: {e}", 'error')
        import traceback
        traceback.print_exc()
        exit(1)
