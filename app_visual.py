import streamlit as st
import time
import pandas as pd
import numpy as np
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import yfinance as yf
import feedparser
import json
import os
import plotly.graph_objects as go

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
        estado_inicial = {"saldo_usdt": 1000.0, "portafolio": {}, "historial": []}
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
            if "historial" not in estado:
                estado["historial"] = []
            portafolio_limpio = {}
            for par in ['BTC-USD', 'ETH-USD', 'SOL-USD']:
                if par in estado.get("portafolio", {}):
                    portafolio_limpio[par] = estado["portafolio"][par]
                else:
                    portafolio_limpio[par] = {"comprado": False, "tipo_posicion": None, "precio_entrada": 0.0, "precio_maximo_alcanzado": 0.0, "cantidad": 0.0}
            estado["portafolio"] = portafolio_limpio
            return estado
        except json.JSONDecodeError:
            return {"saldo_usdt": 1000.0, "historial": [], "portafolio": {
                par: {"comprado": False, "tipo_posicion": None, "precio_entrada": 0.0, "precio_maximo_alcanzado": 0.0, "cantidad": 0.0} for par in ['BTC-USD', 'ETH-USD', 'SOL-USD']
            }}

def guardar_saldo_simulado(estado):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(estado, f, indent=4)
    except Exception as e:
        st.sidebar.error(f"Error al guardar estado: {e}")

datos_simulador = cargar_saldo_simulado()

# --- FUNCIONES DE CÁLCULO TÉCNICO E HISTÓRICO ---
def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=30)
def obtener_datos_historicos_yahoo(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(period="1y", interval="1d")
        
        if df.empty:
            return pd.DataFrame()
            
        df = df.reset_index()
        df.columns = df.columns.str.lower()
        df = df.ffill().bfill()
        
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
        df['RSI'] = calcular_rsi(df['close'], 14)
        
        df['div_alcista'] = (df['close'] < df['close'].shift(2)) & (df['RSI'] > df['RSI'].shift(2)) & (df['RSI'] < 40)
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
url_feed = "https://newsbtc.com"
titulares_reales = []
try:
    feed = feedparser.parse(url_feed)
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
        
        tiene_div_alcista = bool(ultima_vela['div_alcista'])
        tiene_div_bajista = bool(ultima_vela['div_bajista'])

        st.subheader(f"🪙 {par.replace('-','/')}")
        st.metric(label="Precio en Vivo (Yahoo)", value=f"${precio_real:,.2f} USD")
        
        st.write(f"📊 **RSI (14 días):** {rsi_actual:.2f}")
        if ema50 > ema200:
            st.markdown("📈 Estructura Macro: **Cruce Alcista (Cruz de Oro)**")
        else:
            st.markdown("📉 Estructura Macro: **Cruce Bajista (Cruz de la Muerte)**")
            
        df_reciente = df_historico.tail(60)
        fig = go.Figure()
        
        eje_x = df_reciente.iloc[:, 0]
        
        fig.add_trace(go.Candlestick(
            x=eje_x, open=df_reciente['open'], high=df_reciente['high'],
            low=df_reciente['low'], close=df_reciente['close'], name='Velas'
        ))
        fig.add_trace(go.Scatter(x=eje_x, y=df_reciente['EMA_50'], line=dict(color='orange', width=1.5), name='EMA 50'))
        fig.add_trace(go.Scatter(x=eje_x, y=df_reciente['EMA_200'], line=dict(color='blue', width=1.5), name='EMA 200'))
        fig.update_layout(xaxis_rangeslider_visible=False, height=250, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

# --- MOTOR DE EJECUCIÓN AUTÓNOMA (COMPRA/VENTA SIMULADA) ---
if bot_activo:
    st.markdown("---")
    st.header("⚡ Registro de Operaciones en Tiempo Real")
    
    for par in criptomonedas:
        df_historico = obtener_datos_historicos_yahoo(par)
        if df_historico.empty:
            continue
            
        ultima_vela = df_historico.iloc[-1]
        precio_real = float(ultima_vela['close'])
        ema50 = ultima_vela['EMA_50']
        ema200 = ultima_vela['EMA_200']
        
        tiene_div_alcista = bool(ultima_vela['div_alcista'])
        tiene_div_bajista = bool(ultima_vela['div_bajista'])
        
        patron_alcista = (precio_real > ema50 and ema50 > ema200) or tiene_div_alcista
        patron_bajista = (precio_real < ema50 and ema50 < ema200) or tiene_div_bajista
        
        posicion = datos_simulador["portafolio"][par]
        
        # LÓGICA DE COMPRA (LONG)
        if not posicion["comprado"] and patron_alcista:
            if datos_simulador["saldo_usdt"] >= capital_operacion:
                cantidad_comprada = (capital_operacion * (1 - comision_broker)) / precio_real
                datos_simulador["saldo_usdt"] -= capital_operacion
                
                datos_simulador["portafolio"][par] = {
                    "comprado": True,
                    "tipo_posicion": "LONG",
                    "precio_entrada": precio_real,
                    "precio_maximo_alcanzado": precio_real,
                    "cantidad": cantidad_comprada
                }
                guardar_saldo_simulado(datos_simulador)
                st.success(f"🚀 **Orden de COMPRA ejecutada:** {par} a ${precio_real:,.2f} USD")
                st.rerun()
                
        # LÓGICA DE VENTA (TRAILING STOP)
        elif posicion["comprado"] and posicion["tipo_posicion"] == "LONG":
            if precio_real > posicion["precio_maximo_alcanzado"]:
                datos_simulador["portafolio"][par]["precio_maximo_alcanzado"] = precio_real
                guardar_saldo_simulado(datos_simulador)
            
            precio_stop_trailing = posicion["precio_maximo_alcanzado"] * (1 - (porcentaje_trailing / 100))
            
            if precio_real <= precio_stop_trailing or patron_bajista:
                retorno_usdt = (posicion["cantidad"] * precio_real) * (1 - comision_broker)
                ganancia_perdida = retorno_usdt - capital_operacion
                datos_simulador["saldo_usdt"] += retorno_usdt
                
                nuevo_registro = {
                    "Par": par.replace("-", "/"),
                    "Tipo": "LONG",
                    "Precio Entrada": posicion["precio_entrada"],
                    "Precio Venta": precio_real,
                    "Resultado (USDT)": round(ganancia_perdida, 2),
