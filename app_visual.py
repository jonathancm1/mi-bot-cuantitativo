import streamlit as st
import time
import pandas as pd
import numpy as np
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import urllib.request
import feedparser
import json
import os

# --- CONFIGURACIÓN DE INTERFAZ PROFESIONAL ---
st.set_page_config(page_title="Algoritmo Cuantitativo Cloud 24/7", page_icon="🤖", layout="wide")

# Descarga segura del diccionario VADER para análisis de texto
import nltk
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)

sia = SentimentIntensityAnalyzer()
DB_FILE = "estado_simulador_app.json"

# --- GESTIÓN ROBUSTA DE BASE DE DATOS LOCAL (JSON) ---
def cargar_saldo_simulado():
    if not os.path.exists(DB_FILE):
        estado_inicial = {"saldo_usdt": 1000.0, "portafolio": {}}
        for par in ['BTC-USD', 'ETH-USD', 'SOL-USD']:
            estado_inicial["portafolio"][par] = {
                "comprado": False, 
                "tipo_posicion": None, 
                "precio_entrada": 0.0, 
                "precio_maximo_alcanzado": 0.0, 
                "cantidad": 0.0
            }
        with open(DB_FILE, "w") as f:
            json.dump(estado_inicial, f, indent=4)
        return estado_inicial
    
    with open(DB_FILE, "r") as f:
        try:
            estado = json.load(f)
            portafolio_limpio = {}
            for par in ['BTC-USD', 'ETH-USD', 'SOL-USD']:
                if par in estado.get("portafolio", {}):
                    portafolio_limpio[par] = estado["portafolio"][par]
                else:
                    portafolio_limpio[par] = {"comprado": False, "tipo_posicion": None, "precio_entrada": 0.0, "precio_maximo_alcanzado": 0.0, "cantidad": 0.0}
            estado["portafolio"] = portafolio_limpio
            return estado
        except json.JSONDecodeError:
            return {"saldo_usdt": 1000.0, "portafolio": {
                par: {"comprado": False, "tipo_posicion": None, "precio_entrada": 0.0, "precio_maximo_alcanzado": 0.0, "cantidad": 0.0} for par in ['BTC-USD', 'ETH-USD', 'SOL-USD']
            }}

def guardar_saldo_simulado(estado):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(estado, f, indent=4)
    except Exception as e:
        st.sidebar.error(f"Error al guardar estado: {e}")

datos_simulador = cargar_saldo_simulado()

# --- FUNCIONES DE CÁLCULO TÉCNICO E HISTÓRICO VIA YAHOO FINANCE ---
def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=30)
def obtener_datos_historicos_yahoo(ticker):
    try:
        url = f"https://yahoo.com{ticker}?range=1y&interval=1d"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive'
        }
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            
        result = data['chart']['result']
        timestamps = result['timestamp']
        indicators = result['indicators']['quote']
        
        df = pd.DataFrame({
            'timestamp': pd.to_datetime(timestamps, unit='s'),
            'open': indicators['open'],
            'high': indicators['high'],
            'low': indicators['low'],
            'close': indicators['close'],
            'volume': indicators['volume']
        })
        df = df.ffill().bfill()
        
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        df['RSI'] = calcular_rsi(df['close'], 14)
        
        # MOTOR CUANTITATIVO: DETECCIÓN MATEMÁTICA DE DIVERGENCIAS DEL RSI (Últimas sesiones)
        # Alcista: Precio hace mínimos más bajos pero el RSI hace mínimos más altos (Fuerza alcista oculta)
        df['div_alcista'] = (df['close'] < df['close'].shift(2)) & (df['RSI'] > df['RSI'].shift(2)) & (df['RSI'] < 40)
        # Bajista: Precio hace máximos más altos pero el RSI hace máximos más bajos (Agotamiento de compras)
        df['div_bajista'] = (df['close'] > df['close'].shift(2)) & (df['RSI'] < df['RSI'].shift(2)) & (df['RSI'] > 60)
        
        return df
    except Exception as e:
        return pd.DataFrame()

# --- INTERFAZ ---
st.title("🤖 Servidor Cuantitativo Autónomo 24/7 (Inmune a Bloqueos)")
st.markdown("---")

# --- PANEL DE CONTROL ---
st.sidebar.header("🛡️ Parámetros del Sistema")
capital_operacion = st.sidebar.number_input("Capital por Operación (USDT)", min_value=6.0, value=50.0, step=5.0)
comision_broker = st.sidebar.slider("Comisión Estándar (%)", min_value=0.05, max_value=0.20, value=0.10, step=0.01) / 100
porcentaje_trailing = st.sidebar.slider("Porcentaje de Trailing Stop (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.1)

bot_activo = st.sidebar.toggle("🟢 Activar Algoritmo Autónomo", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Balance del Simulador")
st.sidebar.metric(label="Saldo Disponible", value=f"${datos_simulador['saldo_usdt']:.2f} USDT")

if st.sidebar.button("🔄 Reiniciar Simulador"):
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    st.rerun()

# --- MÓDULO DE SENTIMIENTO ---
url_feed = "https://yahoo.com"
titulares_reales = []
try:
    headers_rss = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    req_rss = urllib.request.Request(url_feed, headers=headers_rss)
    with urllib.request.urlopen(req_rss, timeout=8) as response:
        feed = feedparser.parse(response.read())
        for entrada in feed.entries[:5]: 
            if hasattr(entrada, 'title'):
                titulares_reales.append(entrada.title.strip())
except: pass

if not titulares_reales:
    titulares_reales = ["Market volatility stabilizes as global trading volume increases"]

scores_totales = sum([sia.polarity_scores(t)['compound'] for t in titulares_reales])
score_promedio = scores_totales / len(titulares_reales) if titulares_reales else 0.0

# --- EVALUACIÓN EN TIEMPO REAL ---
st.header("📉 Análisis de Tendencias Históricas y Decisiones en la Nube")

criptomonedas = ['BTC-USD', 'ETH-USD', 'SOL-USD']
cols = st.columns(3)
necesita_recarga = False

for i, par in enumerate(criptomonedas):
    with cols[i]:
        df_historico = obtener_datos_historicos_yahoo(par)
        
        if df_historico.empty:
            st.error(f"Error al conectar con las nubes de datos para {par}")
            continue
            
        ultima_vela = df_historico.iloc[-1]
        precio_real = float(ultima_vela['close'])
        ema50 = ultima_vela['EMA_50']
        ema200 = ultima_vela['EMA_200']
        rsi_actual = ultima_vela['RSI']
        
        # Filtros de patrones de divergencias calculados
        tiene_div_alcista = bool(ultima_vela['div_alcista'])
        tiene_div_bajista = bool(ultima_vela['div_bajista'])
        
        # LÓGICA FILTRADA: Para operar LONG exige Tendencia Alcista + Sentimiento O tener una Divergencia Alcista activa
        patron_alcista = (precio_real > ema50 and ema50 > ema200) or tiene_div_alcista
        # Para operar SHORT exige Tendencia Bajista + Pánico O tener una Divergencia Bajista activa
        patron_bajista = (precio_real < ema50 and ema50 < ema200) or tiene_div_bajista

        st.subheader(f"🪙 {par.replace('-','/')}")
        st.metric(label="Precio en Vivo (Yahoo)", value=f"${precio_real:,.2f} USD")
        
        st.write(f"📊 **RSI (14 días):** {rsi_actual:.2f}")
        if ema50 > ema200:
            st.markdown("📈 Estructura Macro: **Cruce Alcista (Cruz de Oro)**")
        else:
            st.markdown("📉 Estructura Macro: **Cruce Bajista (Cruz de la Muerte)**")
            
        # Alertas visuales de divergencias en el panel
        if tiene_div_alcista: 
            st.info("✨ ¡Divergencia Alcista RSI Confirmada!")
        if tiene_div_bajista: 
            st.error("⚠️ ¡Divergencia Bajista RSI Confirmada!")

        pos = datos_simulador["portafolio"].get(par, {"comprado": False, "tipo_posicion": None, "precio_entrada": 0.0, "precio_maximo_alcanzado": 0.0, "cantidad": 0.0})
        nombre_activo = par.split('-')[0]
        
        # --- LÓGICA DE TRADING EN LA NUBE ---
        if not pos["comprado"]:
            if bot_activo:
                if patron_alcista and score_promedio >= 0.02:
                    st.success(f"🚀 SEÑAL OPERACIÓN COMPRA (LONG) EN {nombre_activo}")
                    if datos_simulador["saldo_usdt"] >= capital_operacion:
                        datos_simulador["saldo_usdt"] -= capital_operacion
                        cantidad = (capital_operacion / precio_real) * (1 - comision_broker)
                        pos.update({"comprado": True, "tipo_posicion": "LONG", "precio_entrada": precio_real, "precio_maximo_alcanzado": precio_real, "cantidad": cantidad})
                        guardar_saldo_simulado(datos_simulador)
                        necesita_recarga = True
                
                elif patron_bajista and score_promedio <= -0.02:
                    st.error(f"📉 SEÑAL OPERACIÓN CORTO (SHORT) EN {nombre_activo}")
                    if datos_simulador["saldo_usdt"] >= capital_operacion:
                        datos_simulador["saldo_usdt"] -= capital_operacion
                        cantidad = (capital_operacion / precio_real) * (1 - comision_broker)
