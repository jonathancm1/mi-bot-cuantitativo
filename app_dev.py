import streamlit as st
import time
import pandas as pd
import numpy as np
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import feedparser
import json
import os
import plotly.graph_objects as go
import nltk
import requests
import yfinance as yf

# --- CONECTOR OFICIAL DE BINANCE ---
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
except ImportError:
    pass

# --- CONFIGURACIÓN DE INTERFAZ PROFESIONAL ---
st.set_page_config(page_title="Algoritmo Cuantitativo Cloud 24/7", page_icon="🤖", layout="wide")

@st.cache_resource
def inicializar_analizador_sentimiento():
    try:
        nltk.data.find('sentiment/vader_lexicon.zip')
    except LookupError:
        nltk.download('vader_lexicon', quiet=True)
    return SentimentIntensityAnalyzer()

sia = inicializar_analizador_sentimiento()
DB_FILE = "estado_simulador_app.json"
DB_REAL_FILE = "estado_real_app.json"

# --- GESTIÓN ROBUSTA DE BASE DE DATOS LOCAL (JSON) ---
def cargar_estado(modo_real=False):
    archivo = DB_REAL_FILE if modo_real else DB_FILE
    if not os.path.exists(archivo):
        estado_inicial = {"saldo_usdt": 1000.0, "portafolio": {}, "historial_v2": []}
        for par in ['BTC-USD', 'ETH-USD', 'SOL-USD']:
            estado_inicial["portafolio"][par] = {
                "comprado": False, 
                "tipo_posicion": None, 
                "precio_entrada": 0.0, 
                "precio_maximo_alcanzado": 0.0, 
                "cantidad": 0.0
            }
        with open(archivo, "w") as f:
            json.dump(estado_inicial, f, indent=4)
        return estado_inicial
    
    with open(archivo, "r") as f:
        try:
            estado = json.load(f)
            if "historial_v2" not in estado:
                estado["historial_v2"] = []
            portafolio_limpio = {}
            for par in ['BTC-USD', 'ETH-USD', 'SOL-USD']:
                if par in estado.get("portafolio", {}):
                    portafolio_limpio[par] = estado["portafolio"][par]
                else:
                    portafolio_limpio[par] = {"comprado": False, "tipo_posicion": None, "precio_entrada": 0.0, "precio_maximo_alcanzado": 0.0, "cantidad": 0.0}
            estado["portafolio"] = portafolio_limpio
            return estado
        except json.JSONDecodeError:
            return {"saldo_usdt": 1000.0, "historial_v2": [], "portafolio": {
                par: {"comprado": False, "tipo_posicion": None, "precio_entrada": 0.0, "precio_maximo_alcanzado": 0.0, "cantidad": 0.0} for par in ['BTC-USD', 'ETH-USD', 'SOL-USD']
            }}

# --- PANEL DE CONTROL SIDEBAR ---
st.sidebar.header("🛡️ Parámetros del Sistema")

# SWITCH PROFESIONAL DE ENTORNO REAL / SIMULADOR
entorno_real = st.sidebar.toggle("⚡ OPERAR EN ENTORNO REAL (BINANCE)", value=False)

# CONEXIÓN SEGURA Y AUTENTICACIÓN CON ENTORNO REAL
cliente_binance = None
if entorno_real:
    try:
        api_key = st.secrets["binance"]["api_key"]
        api_secret = st.secrets["binance"]["api_secret"]
        cliente_binance = Client(api_key, api_secret)
        
        balance_spot = cliente_binance.get_asset_balance(asset='USDT')
        saldo_real = float(balance_spot['free']) if balance_spot else 0.0
        
        datos_actuales = cargar_estado(modo_real=True)
        datos_actuales["saldo_usdt"] = saldo_real
    except Exception as e:
        st.sidebar.error("⚠️ Error de conexión con Binance. Verifica tus API Keys en Secrets.")
        entorno_real = False
        datos_actuales = cargar_estado(modo_real=False)
else:
    datos_actuales = cargar_estado(modo_real=False)

capital_operacion = st.sidebar.number_input("Capital por Operación (USDT)", min_value=6.0, value=50.0, step=5.0)
comision_broker = st.sidebar.slider("Comisión Estándar (%)", min_value=0.05, max_value=0.20, value=0.10, step=0.01) / 100
porcentaje_trailing = st.sidebar.slider("Porcentaje de Trailing Stop (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.1)
bot_activo = st.sidebar.toggle("🟢 Activar Algoritmo Autónomo", value=True)

st.sidebar.markdown("---")
if entorno_real:
    st.sidebar.subheader("💰 Balance Billetera Spot REAL")
    st.sidebar.metric(label="Saldo en Binance", value=f"${datos_actuales['saldo_usdt']:.2f} USDT", delta="BINANCE LIVE", delta_color="inverse")
else:
    st.sidebar.subheader("💰 Balance del Simulador")
    st.sidebar.metric(label="Saldo Disponible", value=f"${datos_actuales['saldo_usdt']:.2f} USDT", delta="MODO DEMO", delta_color="normal")

if st.sidebar.button("🔄 Reiniciar Entorno Actual"):
    if not entorno_real:
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.rerun()
    else:
        st.sidebar.warning("No puedes reiniciar el entorno real desde la app.")

def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))

# --- EVALUACIÓN EN TIEMPO REAL AUTÓNOMA ---
st.title("🤖 Servidor Cuantitativo Autónomo 24/7 (Inmune a Bloqueos)")
st.markdown("---")
st.header("📉 Análisis de Tendencias Históricas y Decisiones en la Nube")

@st.fragment(run_every=5)
def mostrar_mercado_y_operar():
    criptomonedas = ['BTC-USD', 'ETH-USD', 'SOL-USD']
    cols_metricas = st.columns(3)
    st.markdown("---")
    st.subheader("📊 Gráficos Técnicos Interactivos (Velas Japonesas)")
    cols_graficos = st.columns(3)
    
    dict_dfs = {}

    for idx, par in enumerate(criptomonedas):
        df_historico = pd.DataFrame()
        
        try:
            ticker_obj = yf.Ticker(par)
            df_historico = ticker_obj.history(period="1d", interval="1m")
            if not df_historico.empty:
                df_historico = df_historico.reset_index()
        except:
            pass

        if df_historico.empty:
            try:
                df_historico = yf.download(par, period="1d", interval="1m", progress=False)
                if not df_historico.empty:
                    df_historico = df_historico.reset_index()
            except:
                pass

        with cols_metricas[idx]:
            st.subheader(f"🪙 {par}")
            if not df_historico.empty:
                df_historico.columns = df_historico.columns.str.lower()
                df_historico = df_historico.ffill().bfill()
                
                precio_real = float(df_historico['close'].iloc[-1])
                df_historico['ema_50'] = df_historico['close'].ewm(span=50, adjust=False).mean()
                df_historico['ema_200'] = df_historico['close'].ewm(span=200, adjust=False).mean()
                df_historico['rsi'] = calcular_rsi(df_historico['close'], 14)
                
                eje_x = 'datetime' if 'datetime' in df_historico.columns else 'date' if 'date' in df_historico.columns else df_historico.index.name
                dict_dfs[par] = (df_historico, eje_x)

                st.write("Precio en Vivo")
                st.markdown(f"### ${precio_real:,.2f} USD")
                st.write(f"📊 RSI (14m): {df_historico['rsi'].iloc[-1]:.2f}")
                
                if df_historico['ema_50'].iloc[-1] > df_historico['ema_200'].iloc[-1]:
                    st.success("📈 Estructura: Cruce Alcista (Golden Cross)")
                else:
                    st.error("📉 Estructura: Cruce Bajista (Death Cross)")

                pos = datos_actuales["portafolio"].get(par, {})
                if pos.get("comprado", False):
                    st.info(f"🔒 Posición LONG Activa\n\nCantidad: {pos['cantidad']:.4f}\n\nEntrada: ${pos['precio_entrada']:,.2f}")
                else:
                    st.write("💤 Sin posiciones activas")
            else:
                st.info(f"Sincronizando flujo de {par}...")

        with cols_graficos[idx]:
            if par in dict_dfs:
                df, x_col = dict_dfs[par]
                fig = go.Figure()
                
                fig.add_trace(go.Candlestick(
                    x=df[x_col] if x_col else df.index,
                    open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                    name='Mercado'
                ))
                fig.add_trace(go.Scatter(x=df[x_col] if x_col else df.index, y=df['ema_50'], name='EMA 50', line=dict(color='orange', width=1.5)))
                fig.add_trace(go.Scatter(x=df[x_col] if x_col else df.index, y=df['ema_200'], name='EMA 200', line=dict(color='red', width=1.5)))
                fig.update_layout(title=f"Tendencia {par}", height=280, margin=dict(l=10, r=10, t=30, b=10), xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.caption("Esperando actualización de velas...")

    # --- BITÁCORA DE TRANSACCIONES ---
    st.markdown("---")
    st.subheader("📋 Bitácora de Transacciones Virtuales en Tiempo Real")
    historial_datos = datos_actuales.get("historial_v2", [])
    if len(historial_datos) > 0:
        st.dataframe(pd.DataFrame(historial_datos), use_container_width=True)
    else:
        st.info("No hay transacciones registradas en este entorno aún.")

    # --- RENDIMIENTO CONSOLIDADO P&L ---
    st.markdown("---")
    st.subheader("📈 Rendimiento Consolidado en Tiempo Real (P&L)")
    cols_pl = st.columns(3)
    for i, par in enumerate(criptomonedas):
        with cols_pl[i]:
            st.markdown(f"**P&L {par}**")
            st.write("🔴 -$0.00 USDT")

# Ejecución de la UI coordinada
mostrar_mercado_y_operar()
