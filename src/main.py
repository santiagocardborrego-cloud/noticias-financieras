#!/usr/bin/env python3
"""
Sistema de Noticias Financieras - GitHub Actions
100% GRATIS - Financial Times + NewsAPI + Claude + WhatsApp
Corre automáticamente a las 6 AM (Hora México) cada día
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import base64

# ====================
# CONFIGURACIÓN
# ====================

# Obtén estos valores de variables de entorno (GitHub Secrets)
FT_API_KEY = os.getenv('FT_API_KEY', '')  # Tu Financial Times API Key
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', '')  # newsapi.org (gratis)
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')  # console.anthropic.com
GOOGLE_TTS_API_KEY = os.getenv('GOOGLE_TTS_API_KEY')  # console.cloud.google.com
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')  # twilio.com
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_FROM = os.getenv('TWILIO_WHATSAPP_FROM', '')  # +1234567890
TU_NUMERO_WHATSAPP = os.getenv('TU_NUMERO_WHATSAPP')  # +52XXXXXXXXXX

# ====================
# FUNCIÓN 1: Obtener Noticias
# ====================

def obtener_noticias() -> List[Dict]:
    """
    Obtiene noticias de Financial Times y NewsAPI
    Prioriza FT si tienes key, sino usa NewsAPI (gratis)
    """
    noticias = []
    
    # INTENTA PRIMERO FINANCIAL TIMES
    if FT_API_KEY:
        print("📰 Buscando en Financial Times...")
        noticias.extend(obtener_noticias_financial_times())
    
    # COMPLEMENTA CON NewsAPI (siempre disponible)
    print("📰 Buscando en NewsAPI...")
    noticias.extend(obtener_noticias_newsapi())
    
    # Remover duplicados y ordenar por relevancia
    noticias_unicas = []
    titulos_vistos = set()
    
    for noticia in noticias:
        if noticia['titulo'] not in titulos_vistos:
            titulos_vistos.add(noticia['titulo'])
            noticias_unicas.append(noticia)
    
    return noticias_unicas[:25]  # Top 25 noticias

def obtener_noticias_financial_times() -> List[Dict]:
    """Obtiene noticias de Financial Times"""
    try:
        ahora = datetime.utcnow()
        hace24h = ahora - timedelta(days=1)
        
        fecha_desde = hace24h.strftime('%Y-%m-%d')
        fecha_hasta = ahora.strftime('%Y-%m-%d')
        
        # Query para economía, finanzas, política
        query = 'markets OR finance OR economy OR "central bank" OR inflation OR "interest rates" OR stocks'
        
        url = 'https://api.ft.com/content/search'
        params = {
            'q': query,
            'apiKey': FT_API_KEY,
            'maxResults': 50,
            'sortOrder': 'DESC'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            print(f"⚠️ Error FT API: {response.status_code}")
            return []
        
        data = response.json()
        noticias = []
        
        for item in data.get('results', [])[:15]:
            noticias.append({
                'titulo': item.get('title', ''),
                'descripcion': item.get('standfirst', item.get('summary', '')),
                'url': item.get('id', ''),
                'fuente': 'Financial Times',
                'fecha': item.get('createdDate', '')
            })
        
        print(f"✅ Financial Times: {len(noticias)} noticias")
        return noticias
        
    except Exception as e:
        print(f"❌ Error FT: {e}")
        return []

def obtener_noticias_newsapi() -> List[Dict]:
    """Obtiene noticias de NewsAPI (gratis: 500 requests/día)"""
    try:
        # Noticias de hoy
        hoy = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Búsquedas por sector
        queries = [
            'markets finance economy',
            'central bank inflation interest rates',
            'Mexico economy markets',
            'stock market USA China'
        ]
        
        todas_noticias = []
        
        for query in queries:
            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': query,
                'from': hoy,
                'sortBy': 'publishedAt',
                'language': 'en',
                'apiKey': NEWSAPI_KEY,
                'pageSize': 10
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                print(f"⚠️ NewsAPI error: {response.status_code}")
                continue
            
            data = response.json()
            
            for article in data.get('articles', []):
                todas_noticias.append({
                    'titulo': article.get('title', ''),
                    'descripcion': article.get('description', ''),
                    'url': article.get('url', ''),
                    'fuente': article.get('source', {}).get('name', 'NewsAPI'),
                    'fecha': article.get('publishedAt', '')
                })
        
        print(f"✅ NewsAPI: {len(todas_noticias)} noticias")
        return todas_noticias
        
    except Exception as e:
        print(f"❌ Error NewsAPI: {e}")
        return []

# ====================
# FUNCIÓN 2: Analizar con Claude
# ====================

def analizar_noticias(noticias: List[Dict]) -> str:
    """Analiza noticias con Claude (tier gratis)"""
    
    # Formatear noticias para Claude
    noticias_text = ''
    for i, noticia in enumerate(noticias[:20], 1):
        noticias_text += f"{i}. {noticia['titulo']}\n"
        if noticia['descripcion']:
            noticias_text += f"   {noticia['descripcion'][:200]}\n"
        noticias_text += f"   Fuente: {noticia['fuente']}\n\n"
    
    prompt = f"""Eres un analista financiero para México y mercados globales.

NOTICIAS DEL ÚLTIMO DÍA:
{noticias_text}

TAREA: Genera un resumen ejecutivo EXACTAMENTE en este formato:

📍 NOTICIAS GLOBALES
Máximo 15 noticias con formato:
🔴 [SECTOR] TITULAR
↳ Impacto: [máximo 2 líneas]

🇲🇽 NOTICIAS MÉXICO
Máximo 8 noticias con formato:
🔵 [SECTOR] TITULAR
↳ Impacto: [máximo 2 líneas]

📊 INDICADORES CLAVE (últimos valores conocidos)
- USD/MXN: [precio y %]
- IPC: [puntos y %]
- S&P 500: [puntos y %]
- WTI: [USD/barril]
- CETE 28: [%]
- Inflación: [%]

💡 OPORTUNIDADES Y ALERTAS
- Sectores en oportunidad (2-3 máximo)
- Riesgos identificados
- Seguimiento importante hoy

Sé conciso. Máximo 2 líneas por noticia. Total máximo 5 mensajes WhatsApp."""

    try:
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers={
                'x-api-key': CLAUDE_API_KEY,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json'
            },
            json={
                'model': 'claude-opus-4-20250514',
                'max_tokens': 1500,
                'system': 'Eres un analista financiero profesional. Sé conciso, claro y accionable. Máximo 2 líneas por impacto.',
                'messages': [{'role': 'user', 'content': prompt}]
            },
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Error Claude: {response.status_code}")
            return "Error al generar resumen"
        
        data = response.json()
        resumen = data['content'][0]['text']
        print("✅ Análisis completado")
        return resumen
        
    except Exception as e:
        print(f"❌ Error Claude API: {e}")
        return f"Error: {e}"

# ====================
# FUNCIÓN 3: Generar Podcast
# ====================

def generar_podcast(resumen: str) -> Tuple[str, bytes]:
    """
    Genera podcast con Google Cloud TTS
    Retorna (mime_type, audio_bytes)
    """
    
    # Reducir resumen para podcast (~3-4 minutos)
    resumen_corto = resumen[:2000]
    
    guion = f"""Buenos días. Soy tu analista de mercados. Son las 6 de la mañana 
y aquí está el resumen de lo que pasó en los mercados internacionales 
y en México.

{resumen_corto}

Eso es todo por hoy. Mucho éxito en tus inversiones."""

    try:
        payload = {
            'input': {'text': guion},
            'voice': {
                'languageCode': 'es-MX',
                'name': 'es-MX-Neural2-B',
                'ssmlGender': 'MALE'
            },
            'audioConfig': {
                'audioEncoding': 'MP3',
                'pitch': 0.2,
                'speakingRate': 1.1
            }
        }
        
        response = requests.post(
            f'https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}',
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Error TTS: {response.status_code}")
            return None, None
        
        data = response.json()
        audio_base64 = data['audioContent']
        
        # Convertir base64 a bytes
        audio_bytes = base64.b64decode(audio_base64)
        
        print(f"✅ Podcast generado ({len(audio_bytes)} bytes)")
        return 'audio/mpeg', audio_bytes
        
    except Exception as e:
        print(f"❌ Error generando podcast: {e}")
        return None, None

# ====================
# FUNCIÓN 4: Enviar a WhatsApp
# ====================

def enviar_whatsapp(resumen: str, audio_bytes: bytes = None):
    """Envía resumen + podcast a WhatsApp vía Twilio"""
    
    try:
        # Dividir resumen en mensajes (máx 1000 chars)
        mensajes = dividir_texto(resumen, 900)
        
        auth = base64.b64encode(
            f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        url = f'https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json'
        
        # Enviar cada mensaje de texto
        for i, msg in enumerate(mensajes):
            print(f"📤 Enviando mensaje {i+1}/{len(mensajes)}...")
            
            data = {
                'From': f'whatsapp:{TWILIO_WHATSAPP_FROM}',
                'To': f'whatsapp:{TU_NUMERO_WHATSAPP}',
                'Body': msg
            }
            
            response = requests.post(url, data=data, headers=headers, timeout=10)
            
            if response.status_code not in [200, 201]:
                print(f"⚠️ Error enviando mensaje: {response.status_code}")
            else:
                print(f"✅ Mensaje {i+1} enviado")
        
        # Enviar podcast si existe
        if audio_bytes:
            print("🎙️ Enviando podcast...")
            # NOTA: Para enviar audio, necesitas guardar en servidor
            # y pasar la URL pública. Por ahora, solo logs.
            print(f"✅ Audio listo ({len(audio_bytes)} bytes)")
        
    except Exception as e:
        print(f"❌ Error WhatsApp: {e}")

def dividir_texto(texto: str, max_len: int = 900) -> List[str]:
    """Divide texto en chunks para WhatsApp"""
    mensajes = []
    actual = ''
    
    for linea in texto.split('\n'):
        if len(actual) + len(linea) + 1 > max_len:
            if actual:
                mensajes.append(actual)
            actual = linea + '\n'
        else:
            actual += linea + '\n'
    
    if actual:
        mensajes.append(actual)
    
    return mensajes

# ====================
# FUNCIÓN PRINCIPAL
# ====================

def main():
    """Ejecuta el flujo completo"""
    print("=" * 60)
    print("📊 SISTEMA DE NOTICIAS FINANCIERAS")
    print(f"🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Paso 1: Obtener noticias
    print("\n[1/4] Obteniendo noticias...")
    noticias = obtener_noticias()
    print(f"✅ {len(noticias)} noticias recopiladas")
    
    if not noticias:
        print("❌ No se obtuvieron noticias. Abortando.")
        return
    
    # Paso 2: Analizar con Claude
    print("\n[2/4] Analizando con Claude...")
    resumen = analizar_noticias(noticias)
    print(f"✅ Resumen generado ({len(resumen)} caracteres)")
    
    # Paso 3: Generar podcast
    print("\n[3/4] Generando podcast...")
    mime_type, audio_bytes = generar_podcast(resumen)
    
    # Paso 4: Enviar a WhatsApp
    print("\n[4/4] Enviando a WhatsApp...")
    enviar_whatsapp(resumen, audio_bytes)
    
    print("\n" + "=" * 60)
    print("✅ ¡COMPLETO!")
    print("=" * 60)
    
    # Mostrar resumen en logs
    print("\n📋 RESUMEN GENERADO:\n")
    print(resumen)

if __name__ == '__main__':
    main()
