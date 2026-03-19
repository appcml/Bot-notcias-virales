# ═══════════════════════════════════════════════════════════════
# GENERACION DE IMAGENES MULTI-API - VERSION CORREGIDA
# ═══════════════════════════════════════════════════════════════

def generar_imagen_gemini(prompt, titulo):
    """Genera imagen usando Gemini API - CORREGIDO"""
    if not GEMINI_API_KEY:
        return None, "No Gemini API key"
    
    try:
        log("Intentando Gemini...", 'imagen')
        
        # Endpoint CORREGIDO para Gemini 2.0 Flash con generación de imagen
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp-image-generation:generateContent?key={GEMINI_API_KEY}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": f"Generate a news thumbnail image: {prompt}"}
                ]
            }],
            "generationConfig": {
                "responseModalities": ["Text", "Image"],
                "temperature": 0.7
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            
            # Buscar imagen en la respuesta
            if 'candidates' in data and len(data['candidates']) > 0:
                candidate = data['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'inlineData' in part:
                            # Decodificar imagen base64
                            img_data = base64.b64decode(part['inlineData']['data'])
                            img_path = f'/tmp/viral_gemini_{generar_hash(titulo)}.jpg'
                            
                            with open(img_path, 'wb') as f:
                                f.write(img_data)
                            
                            if os.path.getsize(img_path) > 10000:
                                log(f"Imagen Gemini generada: {img_path}", 'exito')
                                return img_path, "Gemini"
        
        log(f"Gemini fallo: {response.status_code} - {response.text[:200]}", 'advertencia')
        return None, f"Gemini error: {response.status_code}"
        
    except Exception as e:
        log(f"Error Gemini: {e}", 'error')
        return None, str(e)

def generar_imagen_pollinations(prompt, titulo, seed=None):
    """Genera imagen usando Pollinations.ai - MEJORADO CON RETRY"""
    try:
        log("Usando Pollinations...", 'imagen')
        
        # Prompt mejorado para estilo noticia viral
        prompt_enhanced = (
            f"breaking news thumbnail, viral news style, {prompt}, "
            f"professional news broadcast graphic, dramatic lighting, "
            f"high contrast, cinematic composition, 4k, photorealistic"
        )
        
        prompt_encoded = quote(prompt_enhanced[:1000])  # Limitar longitud
        seed = seed or random.randint(1000, 9999)
        
        # Parámetros optimizados para noticias virales
        url = (
            f"https://image.pollinations.ai/prompt/{prompt_encoded}"
            f"?width=1200&height=630&nologo=true&seed={seed}"
            f"&enhance=true&quality=high&negative=blurry,low quality,text,watermark"
        )
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=60)
        
        if response.status_code == 200:
            img_path = f'/tmp/viral_pollinations_{generar_hash(titulo)}_{seed}.jpg'
            with open(img_path, 'wb') as f:
                f.write(response.content)
            
            # Verificar tamaño mínimo (15KB)
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

def generar_imagen_pollinations_backup(prompt, titulo):
    """Segundo intento con Pollinations con prompt simplificado"""
    try:
        log("Intentando Pollinations con prompt simplificado...", 'imagen')
        
        # Prompt más simple y directo
        prompt_simple = f"news photo: {prompt[:200]}"
        prompt_encoded = quote(prompt_simple)
        seed = random.randint(1000, 9999)
        
        url = (
            f"https://image.pollinations.ai/prompt/{prompt_encoded}"
            f"?width=1200&height=630&nologo=true&seed={seed}"
        )
        
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=45)
        
        if response.status_code == 200:
            img_path = f'/tmp/viral_pollinations2_{generar_hash(titulo)}.jpg'
            with open(img_path, 'wb') as f:
                f.write(response.content)
            
            if os.path.getsize(img_path) > 12000:
                return img_path, "Pollinations-v2"
        
        return None, "Fallback Pollinations fallo"
        
    except Exception as e:
        return None, str(e)

def generar_imagen_inteligente(titulo, contenido, descripcion=""):
    """Intenta generar imagen con múltiples estrategias - CORREGIDO"""
    generador = GeneradorPrompts()
    prompt, analisis = generador.generar(titulo, contenido, descripcion)
    
    # Mejorar el prompt para estilo viral
    prompt = (
        f"viral news thumbnail, breaking news style, dramatic, {prompt}, "
        f"professional photojournalism, news broadcast graphic, high impact"
    )
    
    log(f"Prompt generado: {prompt[:120]}...", 'imagen')
    
    intentos = []
    
    # 1. Intentar Gemini primero (si tiene API key)
    if GEMINI_API_KEY:
        for intento in range(2):  # 2 intentos con diferentes seeds
            img_path, fuente = generar_imagen_gemini(prompt, titulo)
            if img_path:
                return img_path, prompt, fuente, analisis
            time.sleep(1)
        intentos.append("Gemini")
    
    # 2. Pollinations con prompt completo (3 intentos con diferentes seeds)
    for i in range(3):
        seed = random.randint(1000, 9999)
        img_path, fuente = generar_imagen_pollinations(prompt, titulo, seed)
        if img_path:
            return img_path, prompt, fuente, analisis
        time.sleep(1)
    intentos.append("Pollinations-v1")
    
    # 3. Pollinations con prompt simplificado
    img_path, fuente = generar_imagen_pollinations_backup(prompt, titulo)
    if img_path:
        return img_path, prompt, fuente, analisis
    intentos.append("Pollinations-v2")
    
    # 4. Último recurso: Pollinations con prompt mínimo
    try:
        log("Último intento con Pollinations...", 'imagen')
        prompt_minimal = f"breaking news photo about: {titulo[:100]}"
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
    
    log(f"Todas las APIs fallaron: {', '.join(intentos)}", 'error')
    return None, prompt, "Ninguna", analisis

def crear_imagen_backup(titulo, analisis_contexto=None):
    """Crea imagen de respaldo mejorada - SIN 'PERSONAJE:' y con diseño profesional"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import textwrap
        
        # Dimensiones óptimas para Facebook
        width, height = 1200, 630
        
        # Seleccionar color según contexto
        emocion = 'neutral'
        if analisis_contexto:
            emocion = analisis_contexto.get('emocion', 'neutral')
            if analisis_contexto.get('deporte'):
                emocion = 'deporte'
            elif analisis_contexto.get('personaje_principal'):
                emocion = 'politica'
        
        color_fondo = COLORES_BACKUP.get(emocion, COLORES_BACKUP['neutral'])
        
        # Crear imagen con gradiente sutil
        img = Image.new('RGB', (width, height), color_fondo)
        draw = ImageDraw.Draw(img)
        
        # Agregar gradiente sutil en la parte inferior
        for i in range(200):
            alpha = int(255 * (1 - i/200))
            color_gradiente = (
                max(0, color_fondo[0] - 50),
                max(0, color_fondo[1] - 50),
                max(0, color_fondo[2] - 50)
            )
            draw.rectangle([(0, height-200+i), (width, height-200+i+1)], fill=color_gradiente)
        
        # Cargar fuentes con múltiples fallback
        fonts_loaded = False
        font_titulo = font_sub = font_info = None
        
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",  # macOS
            "C:/Windows/Fonts/arialbd.ttf",  # Windows
        ]
        
        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    font_titulo = ImageFont.truetype(font_path, 48)
                    font_sub = ImageFont.truetype(font_path.replace("Bold", "").replace("bd", ""), 24)
                    font_info = ImageFont.truetype(font_path.replace("Bold", "").replace("bd", ""), 20)
                    fonts_loaded = True
                    break
            except:
                continue
        
        if not fonts_loaded:
            font_titulo = ImageFont.load_default()
            font_sub = font_info = font_titulo
        
        # Barra superior blanca (estilo noticiero)
        draw.rectangle([(0, 0), (width, 15)], fill=(255, 255, 255))
        
        # Info de contexto arriba - SIN LA PALABRA "PERSONAJE"
        y_pos = 35
        if analisis_contexto:
            info_lineas = []
            
            # Solo mostrar el nombre, no "PERSONAJE: nombre"
            if analisis_contexto.get('personaje_principal'):
                nombre = PERSONAJES_POLITICOS[analisis_contexto['personaje_principal']]['nombre']
                info_lineas.append(nombre.upper())
            
            if analisis_contexto.get('pais'):
                info_lineas.append(analisis_contexto['pais'].upper())
            
            if analisis_contexto.get('deporte'):
                info_lineas.append(analisis_contexto['deporte'].upper())
            
            if analisis_contexto.get('tipo_evento'):
                evento_esp = {
                    'protesta': 'PROTESTA',
                    'desastre_natural': 'EMERGENCIA',
                    'economica': 'CRISIS ECONÓMICA',
                    'crimen': 'SEGURIDAD'
                }.get(analisis_contexto['tipo_evento'], analisis_contexto['tipo_evento'].upper())
                info_lineas.append(evento_esp)
            
            if info_lineas:
                texto_info = " • ".join(info_lineas)
                # Sombra para el texto de info
                draw.text((52, y_pos+2), texto_info, font=font_info, fill=(0, 0, 0))
                draw.text((50, y_pos), texto_info, font=font_info, fill=(220, 220, 220))
                y_pos = 70
        
        # Preparar título con wrap inteligente
        titulo_limpio = titulo[:140]  # Limitar longitud
        lineas = textwrap.wrap(titulo_limpio, width=28)  # Más ancho para mejor lectura
        if len(lineas) > 4:
            lineas = lineas[:4]
            lineas[-1] = lineas[-1][:25] + "..."
        
        # Calcular posición vertical centrada
        altura_texto = len(lineas) * 55
        y_start = ((height - altura_texto) // 2) - 20
        
        # Dibujar cada línea con sombra y efecto 3D sutil
        for i, linea in enumerate(lineas):
            y = y_start + (i * 55)
            x = 60
            
            # Sombra múltiple para efecto de profundidad
            for offset in [(3, 3), (2, 2), (1, 1)]:
                draw.text((x+offset[0], y+offset[1]), linea, font=font_titulo, fill=(0, 0, 0))
            
            # Texto principal con borde blanco sutil
            draw.text((x-1, y-1), linea, font=font_titulo, fill=(255, 255, 255))
            draw.text((x, y), linea, font=font_titulo, fill=(255, 255, 255))
        
        # Footer con diseño mejorado
        # Línea separadora
        draw.rectangle([(50, height-80), (width-50, height-78)], fill=(255, 255, 255))
        
        # Nombre del medio
        draw.text((50, height-70), "NOTICIAS VIRALES LATAM 24/7", font=font_sub, fill=(255, 255, 255))
        
        # Fecha y hora
        fecha_str = datetime.now().strftime('%d/%m/%Y %H:%M')
        draw.text((50, height-40), f"{fecha_str} | Información que importa", 
                 font=font_info, fill=(200, 200, 200))
        
        # Guardar con alta calidad
        img_path = f'/tmp/viral_backup_{generar_hash(titulo[:50])}.jpg'
        img.save(img_path, 'JPEG', quality=95, optimize=True)
        
        log(f"Imagen backup creada: {img_path}", 'exito')
        return img_path
        
    except Exception as e:
        log(f"Error creando imagen backup: {e}", 'error')
        return None

# Agregar import necesario al inicio del archivo
import time
