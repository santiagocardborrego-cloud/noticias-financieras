#!/usr/bin/env python3
"""
Sistema Automático de Noticias Financieras (SIN PODCAST)
Busca noticias -> Analiza con Claude -> Envía a WhatsApp
Ejecutado por GitHub Actions a las 6 AM (Hora México)
Usuario: santiagocardborrego-cloud

NOTA: Esta versión NO genera podcast de audio.
Solo envía el resumen de texto a WhatsApp (más simple).
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict

# ====================
# CONFIGURACIÓN
# ====================

# Obtener credenciales de variables de entorno (GitHub Secrets)
NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', '')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_FROM = os.getenv('TWILIO_WHATSAPP_FROM', '')
TU_NUMERO_WHATSAPP = os.getenv('TU_NUMERO_WHATSAPP')

# Configuración
ZONA_HORARIA = "America/Mexico_City"
EMAIL_USUARIO = "santiago.cardborrego@gmail.com"

# ====================
# FUNCIONES AUXILIARES
# ====================

def log(mensaje: str, tipo: str = "INFO"):
    """Registra mensajes en logs con timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {tipo}: {mensaje}")

def validar_credenciales() -> bool:
    """Verifica que todas las credenciales estén disponibles"""
    log("Validando credenciales...")
    
    credenciales_requeridas = {
        'NEWSAPI_KEY': NEWSAPI_KEY,
        'CLAUDE_API_KEY': CLAUDE_API_KEY,
        'TWILIO_ACCOUNT_SID': TWILIO_ACCOUNT_SID,
        'TWILIO_AUTH_TOKEN': TWILIO_AUTH_TOKEN,
        'TWILIO_WHATSAPP_FROM': TWILIO_WHATSAPP_FROM,
        'TU_NUMERO_WHATSAPP': TU_NUMERO_WHATSAPP,
    }
    
    faltantes = [k for k, v in credenciales_requeridas.items() if not v]
    
    if faltantes:
        log(f"❌ Credenciales faltantes: {', '.join(faltantes)}", "ERROR")
        return False
    
    log("✅ Todas las credenciales validadas")
    return True

# ====================
# FUNCIÓN 1: OBTENER NOTICIAS
# ====================

def obtener_noticias() -> List[Dict]:
    """
    Obtiene noticias de NewsAPI
    Busca últimas 24 horas de noticias sobre mercados y finanzas
    """
    log("Buscando noticias en NewsAPI...")
    
    try:
        ahora = datetime.utcnow()
        hace24h = ahora - timedelta(days=1)
        
        # Búsquedas por categoría
        queries = [
            'markets finance economy Mexico',
            'central bank inflation interest rates',
            'stock market USA China',
            'peso USD exchange rate',
            'commodities oil gold'
        ]
        
        todas_noticias = []
        
        for query in queries:
            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': query,
                'sortBy': 'publishedAt',
                'language': 'en',
                'apiKey': NEWSAPI_KEY,
                'pageSize': 10
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                log(f"⚠️ Error NewsAPI ({query}): {response.status_code}", "WARN")
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
        
        # Remover duplicados
        noticias_unicas = []
        titulos_vistos = set()
        
        for noticia in todas_noticias:
            if noticia['titulo'] not in titulos_vistos:
                titulos_vistos.add(noticia['titulo'])
                noticias_unicas.append(noticia)
        
        noticias_finales = noticias_unicas[:25]  # Top 25
        log(f"✅ NewsAPI: {len(noticias_finales)} noticias obtenidas")
        return noticias_finales
        
    except Exception as e:
        log(f"❌ Error obteniendo noticias: {e}", "ERROR")
        return []

# ====================
# FUNCIÓN 2: ANALIZAR CON CLAUDE
# ====================

def analizar_noticias_con_claude(noticias: List[Dict]) -> str:
    """
    Analiza noticias con Claude API (tier gratis)
    Genera resumen profesional para WhatsApp
    """
    log("Analizando noticias con Claude...")
    
    if not noticias:
        log("No hay noticias para analizar", "WARN")
        return "No se encontraron noticias relevantes"
    
    # Formatear noticias para Claude
    noticias_text = ''
    for i, noticia in enumerate(noticias[:20], 1):
        noticias_text += f"{i}. {noticia['titulo']}\n"
        if noticia['descripcion']:
            noticias_text += f"   {noticia['descripcion'][:150]}\n"
        noticias_text += f"   Fuente: {noticia['fuente']}\n\n"
    
    prompt = f"""Eres un analista financiero especializado en mercados mexicanos y globales.

NOTICIAS DEL ÚLTIMO DÍA:
{noticias_text}

TAREA: Genera un resumen ejecutivo EXACTAMENTE en este formato:

📍 NOTICIAS GLOBALES
Máximo 15 noticias. Formato:
🔴 [SECTOR] TITULAR
↳ Impacto: [máximo 2 líneas]

🇲🇽 NOTICIAS MÉXICO
Máximo 8 noticias. Formato:
🔵 [SECTOR] TITULAR  
↳ Impacto: [máximo 2 líneas]

📊 INDICADORES CLAVE
- USD/MXN: [último dato disponible]
- IPC: [último dato disponible]
- S&P 500: [último dato disponible]
- CETE 28: [último dato disponible]

💡 OPORTUNIDADES Y ALERTAS
- Sectores en oportunidad (máximo 3)
- Riesgos identificados
- Seguimiento importante hoy

Sé muy conciso. Máximo 2 líneas por noticia. 
Total máximo: 5 mensajes para WhatsApp (máximo 4,000 caracteres)."""

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
                'system': 'Eres un analista financiero profesional. Sé conciso, claro y accionable.',
                'messages': [{'role': 'user', 'content': prompt}]
            },
            timeout=30
        )
        
        if response.status_code != 200:
            log(f"❌ Error Claude API: {response.status_code}", "ERROR")
            return "Error al generar análisis"
        
        data = response.json()
        resumen = data['content'][0]['text']
        log(f"✅ Análisis completado ({len(resumen)} caracteres)")
        return resumen
        
    except Exception as e:
        log(f"❌ Error en Claude API: {e}", "ERROR")
        return f"Error: {str(e)}"

# ====================
# FUNCIÓN 3: ENVIAR A WHATSAPP
# ====================

def enviar_whatsapp(resumen: str) -> bool:
    """
    Envía resumen a WhatsApp usando Twilio
    (SIN PODCAST - Solo texto)
    """
    log("Enviando a WhatsApp...")
    
    try:
        # Dividir resumen en mensajes (máx 1000 chars)
        mensajes = dividir_texto(resumen, 900)
        
        # Preparar autenticación Twilio
        import base64
        auth = base64.b64encode(
            f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()
        ).decode()
        
        headers = {
            'Authorization': f'Basic {auth}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        url = f'https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json'
        
        # Enviar mensajes de texto
        for i, msg in enumerate(mensajes, 1):
            log(f"Enviando mensaje {i}/{len(mensajes)}...")
            
            data = {
                'From': f'whatsapp:{TWILIO_WHATSAPP_FROM}',
                'To': f'whatsapp:{TU_NUMERO_WHATSAPP}',
                'Body': msg
            }
            
            response = requests.post(url, data=data, headers=headers, timeout=10)
            
            if response.status_code not in [200, 201]:
                log(f"⚠️ Error enviando mensaje {i}: {response.status_code}", "WARN")
                continue
            
            log(f"✅ Mensaje {i} enviado")
        
        log(f"✅ Todos los {len(mensajes)} mensajes enviados a WhatsApp")
        return True
        
    except Exception as e:
        log(f"❌ Error en WhatsApp: {e}", "ERROR")
        return False

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
    """Ejecuta el flujo completo (SIN PODCAST)"""
    log("=" * 60)
    log("SISTEMA DE NOTICIAS FINANCIERAS - INICIANDO")
    log("=" * 60)
    
    # Validar credenciales
    if not validar_credenciales():
        log("Abortando: Credenciales incompletas", "ERROR")
        return
    
    # Paso 1: Obtener noticias
    log("\n[1/2] Obteniendo noticias...")
    noticias = obtener_noticias()
    
    if not noticias:
        log("No se obtuvieron noticias. Abortando.", "ERROR")
        return
    
    # Paso 2: Analizar con Claude
    log("\n[2/2] Analizando con Claude...")
    resumen = analizar_noticias_con_claude(noticias)
    
    # Paso 3: Enviar a WhatsApp (SIN PODCAST)
    log("\n[3/3] Enviando a WhatsApp...")
    whatsapp_ok = enviar_whatsapp(resumen)
    
    # Resumen final
    log("\n" + "=" * 60)
    if whatsapp_ok:
        log("✅ PROCESO COMPLETADO EXITOSAMENTE")
    else:
        log("❌ COMPLETADO CON ERRORES", "ERROR")
    log("=" * 60)
    
    # Mostrar resumen
    log("\n📋 RESUMEN ENVIADO:\n")
    print(resumen)

if __name__ == '__main__':
    main()
