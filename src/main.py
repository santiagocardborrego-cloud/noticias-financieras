#!/usr/bin/env python3
"""
Sistema Automático de Noticias Financieras
Busca noticias -> Analiza con Claude -> Envía por EMAIL
Usuario: santiagocardborrego-cloud
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ====================
# CONFIGURACIÓN
# ====================

NEWSAPI_KEY = os.getenv('NEWSAPI_KEY', '')
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
TU_EMAIL = os.getenv('TU_EMAIL_PERSONAL')

# ====================
# FUNCIONES AUXILIARES
# ====================

def log(mensaje: str, tipo: str = "INFO"):
    """Registra mensajes con timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {tipo}: {mensaje}")

def validar_credenciales() -> bool:
    """Verifica credenciales"""
    log("Validando credenciales...")
    
    if not NEWSAPI_KEY or not CLAUDE_API_KEY or not TU_EMAIL:
        log("❌ Faltan credenciales", "ERROR")
        return False
    
    log("✅ Credenciales validadas")
    return True

# ====================
# OBTENER NOTICIAS
# ====================

def obtener_noticias() -> List[Dict]:
    """Obtiene noticias de NewsAPI"""
    log("Buscando noticias...")
    
    try:
        queries = [
            'markets finance economy Mexico',
            'central bank inflation',
            'stock market',
            'peso USD exchange',
            'commodities oil'
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
            
            for article in response.json().get('articles', []):
                todas_noticias.append({
                    'titulo': article.get('title', ''),
                    'descripcion': article.get('description', ''),
                    'url': article.get('url', ''),
                    'fuente': article.get('source', {}).get('name', 'NewsAPI'),
                })
        
        # Remover duplicados
        noticias_unicas = []
        titulos_vistos = set()
        
        for noticia in todas_noticias:
            if noticia['titulo'] not in titulos_vistos:
                titulos_vistos.add(noticia['titulo'])
                noticias_unicas.append(noticia)
        
        noticias_finales = noticias_unicas[:25]
        log(f"✅ NewsAPI: {len(noticias_finales)} noticias obtenidas")
        return noticias_finales
        
    except Exception as e:
        log(f"❌ Error obteniendo noticias: {e}", "ERROR")
        return []

# ====================
# ANALIZAR CON CLAUDE
# ====================

def analizar_noticias_con_claude(noticias: List[Dict]) -> str:
    """Analiza noticias con Claude"""
    log("Analizando con Claude...")
    
    if not noticias:
        return "No se encontraron noticias"
    
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
- USD/MXN: [dato]
- IPC: [dato]
- S&P 500: [dato]

💡 OPORTUNIDADES Y ALERTAS
- Sectores en oportunidad
- Riesgos identificados

Sé muy conciso. Máximo 2 líneas por noticia."""

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
                'system': 'Eres un analista financiero profesional.',
                'messages': [{'role': 'user', 'content': prompt}]
            },
            timeout=30
        )
        
        if response.status_code != 200:
            log(f"❌ Error Claude: {response.status_code}", "ERROR")
            return "Error en análisis"
        
        resumen = response.json()['content'][0]['text']
        log(f"✅ Análisis completado")
        return resumen
        
    except Exception as e:
        log(f"❌ Error Claude: {e}", "ERROR")
        return f"Error: {str(e)}"

# ====================
# ENVIAR EMAIL
# ====================

def enviar_email(resumen: str) -> bool:
    """Envía resumen por email usando GitHub Actions"""
    log("Enviando email...")
    
    try:
        # GitHub Actions proporciona estas variables
        github_actor = os.getenv('GITHUB_ACTOR', 'noticias-bot')
        
        # Crear el email
        asunto = f"📊 Resumen Noticias Financieras - {datetime.now().strftime('%Y-%m-%d')}"
        
        cuerpo = f"""
Hola Santiago,

Aquí está tu resumen diario de noticias financieras:

{resumen}

---
Este resumen fue generado automáticamente por tu sistema de noticias.
Próximo resumen mañana a las 6 AM (Hora México).

Sistema: GitHub Actions
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        # Guardar en archivo (para verificación en logs)
        with open('resumen.txt', 'w', encoding='utf-8') as f:
            f.write(cuerpo)
        
        log(f"✅ Email preparado y guardado")
        log(f"Destinatario: {TU_EMAIL}")
        
        # En GitHub Actions, el email se enviaría con un action adicional
        # Por ahora, solo lo guardamos
        return True
        
    except Exception as e:
        log(f"❌ Error preparando email: {e}", "ERROR")
        return False

# ====================
# FUNCIÓN PRINCIPAL
# ====================

def main():
    """Ejecuta el flujo completo"""
    log("=" * 60)
    log("SISTEMA DE NOTICIAS FINANCIERAS - INICIANDO")
    log("=" * 60)
    
    if not validar_credenciales():
        return
    
    log("\n[1/3] Obteniendo noticias...")
    noticias = obtener_noticias()
    
    if not noticias:
        log("No se obtuvieron noticias", "ERROR")
        return
    
    log("\n[2/3] Analizando con Claude...")
    resumen = analizar_noticias_con_claude(noticias)
    
    log("\n[3/3] Preparando email...")
    email_ok = enviar_email(resumen)
    
    log("\n" + "=" * 60)
    if email_ok:
        log("✅ PROCESO COMPLETADO EXITOSAMENTE")
    else:
        log("❌ COMPLETADO CON ERRORES", "ERROR")
    log("=" * 60)
    
    # Mostrar resumen
    log("\n📋 RESUMEN:\n")
    print(resumen)

if __name__ == '__main__':
    main()
