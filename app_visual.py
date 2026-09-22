import streamlit as st
import ccxt
import time
import pandas as pd
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import urllib.request
import feedparser
import json
import os

# Configuración inicial de la página de tu App Privada
st.set_page_config(page_title="Mi Bot Cuantitativo Privado", page_icon="🤖", layout="wide")

# Asegurar la descarga de lexicon para VADER
import nltk
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)

sia = SentimentIntensityAnalyzer()

DB_FILE = "estado_simulador_app.json"

def cargar_saldo_simulado():
    if not os.path.exists(DB_FILE):
        estado_inicial = {"saldo_usdt": 1000.0, "portafolio": {}}
        for par in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']:
            estado_inicial["portafolio"][par] = {"comprado": False, "precio_compra": 0.0, "cantidad": 0.0}
        with open(DB_FILE, "w") as f:
            json.dump(estado_inicial, f, indent=4)
        return estado_inicial
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            estado_inicial = {"saldo_usdt": 1000.0, "portafolio": {}}
            for par in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']:
                estado_inicial["portafolio"][par] = {"comprado": False, "precio_compra": 0.0, "cantidad": 0.0}
            return estado_inicial

def guardar_saldo_simulado(estado):
    with open(DB_FILE, "w") as f:
        json.dump(estado, f, indent=4)

# Cargar el saldo al iniciar la app
datos_simulador = cargar_saldo_simulado()

# Conexión local simulada/segura a Binance via CCXT
exchange = ccxt.binance({'enableRateLimit': True})

# --- TITULO DE TU APLICACIÓN ---
st.title("🤖 Mi Sistema de Trading Cuantitativo Autónomo")
st.markdown("---")

# --- BARRA LATERAL DE CONFIGURACIÓN Y CONTROL PRIVADO ---
st.sidebar.header("🛡️ Panel de Control")
capital_operacion = st.sidebar.number_input("Capital por Operación (USDT)", min_value=6.0, value=50.0, step=5.0)
comision_broker = st.sidebar.slider("Comisión del Broker (%)", min_value=0.05, max_value=0.20, value=0.10, step=0.01) / 100

# Interruptor general de seguridad de tu app
bot_activo = st.sidebar.toggle("🟢 Activar Operaciones Automáticas", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Balance del Simulador")
st.sidebar.metric(label="Saldo Disponible (USDT)", value=f"${datos_simulador['saldo_usdt']:.2f}")

# Botón rápido para reiniciar el saldo a $1000 si deseas volver a empezar
if st.sidebar.button("🔄 Reiniciar Simulador"):
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    st.rerun()

if not bot_activo:
    st.sidebar.warning("⚠️ El bot se encuentra PAUSADO. Órdenes congeladas en Binance.")

# --- SECCIÓN 1: MONITOR DE PRENSA E IA EN TIEMPO REAL ---
st.header("🌍 Monitoreo de Prensa Mundial e IA")

url_feed = "https://yahoo.com"
titulares_reales = []

try:
    req = urllib.request.Request(url_feed, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    html = urllib.request.urlopen(req, timeout=5).read()
    feed = feedparser.parse(html)
    if feed.entries:
        for entrada in feed.entries[:5]: 
            titulares_reales.append(entrada.title.strip())
except:
    pass

if not titulares_reales:
    titulares_reales = [
        "Federal Reserve signals potential interest rate adjustments next quarter",
        "Institutional crypto adoption reaches new historic milestone this month",
        "Global tech stocks rally drives market optimism to yearly highs",
        "New regulatory framework provides clarity for digital asset trading",
        "Global trading volume increases as market volatility stabilizes"
    ]

datos_noticias = []
scores_totales = 0

for texto in titulares_reales:
    score = sia.polarity_scores(texto)['compound']
    scores_totales += score
    if score >= 0.05: etiqueta = "🟢 Positivo"
    elif score <= -0.05: etiqueta = "🔴 Pánico / Negativo"
    else: etiqueta = "⚪ Neutro"
    datos_noticias.append({"Estatus": etiqueta, "Impacto IA": f"{score:+.2f}", "Titular de Noticia": texto})

score_promedio = scores_totales / len(titulares_reales) if titulares_reales else 0.0

st.metric(label="📊 Impacto de Sentimiento Global Calculado por la IA", value=f"{score_promedio:+.4f}")
st.table(pd.DataFrame(datos_noticias))

# --- SECCIÓN 2: EVALUACIÓN DE TENDENCIAS EN VIVO Y MATRIZ DE DECISIONES ---
st.header("📈 Evaluación de Tendencias Macro y Ejecución")

criptomonedas = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
cols = st.columns(3)

for i, par in enumerate(criptomonedas):
    with cols[i]:
        try:
            # 1. Descarga del precio exacto en tiempo real
            ticker = exchange.fetch_ticker(par)
            precio_real = float(ticker['last'])
            
            # 2. Descarga del Historial de 1 Año (365 velas diarias)
            tendencia_macro = "⚪ Indefinida"
            try:
                ohlcv_anual = exchange.fetch_ohlcv(par, timeframe='1d', limit=365)
                precios_cierre_anual = [float(vela[4]) for vela in ohlcv_anual if vela and len(vela) >= 5]
                
                if len(precios_cierre_anual) >= 200:
                    sma_200_anual = sum(precios_cierre_anual[-200:]) / 200
                    if precio_real > sma_200_anual:
                        tendencia_macro = "🟢 ALCISTA (Seguro operar)"
                    else:
                        tendencia_macro = "🔴 BAJISTA (Alto riesgo)"
                else:
                    sma_200_anual = precio_real
            except:
                sma_200_anual = precio_real
                tendencia_macro = "⚠️ Error de datos anuales"
                
            costo_op = precio_real * comision_broker
            
            st.subheader(f"🪙 {par}")
            st.metric(label="Precio en Vivo (USD)", value=f"${precio_real:,.2f}")
            st.write(f"• **Tendencia Macro (1 Año):** {tendencia_macro}")
            st.write(f"• **Media Anual (SMA 200):** ${sma_200_anual:,.2f}")
            st.write(f"• **Costo de Comisión:** ${costo_op:.4f} USD")
            
            if par in datos_simulador["portafolio"]:
                pos = datos_simulador["portafolio"][par]
            else:
                pos = {"comprado": False, "precio_compra": 0.0, "cantidad": 0.0}
                datos_simulador["portafolio"][par] = pos
            
            nombre_activo = par.split('/')[0]
            
            if not pos["comprado"]:
                if "ALCISTA" in tendencia_macro and score_promedio >= 0.10:
                    st.success("🟢 ACCIÓN: COMPRA SEGURA 🚀")
                    if bot_activo:
                        if datos_simulador["saldo_usdt"] >= capital_operacion:
                            datos_simulador["saldo_usdt"] -= capital_operacion
                            cantidad_comprada = (capital_operacion / precio_real) * (1 - comision_broker)
                            
                            pos.update({
                                "comprado": True,
                                "precio_compra": precio_real,
                                "cantidad": cantidad_comprada
                            })
                            guardar_saldo_simulado(datos_simulador)
                            st.info(f"✅ ¡Compra Virtual ejecutada! Adquiridos: {cantidad_comprada:.4f} {nombre_activo}")
                            st.rerun()
                        else:
                            st.warning("⚠️ Saldo insuficiente para ejecutar la orden en el simulador.")
                elif "BAJISTA" in tendencia_macro:
                    st.warning("🔴 ACCIÓN: BLOQUEADO (Tendencia Anual Bajista - Alto Riesgo)")
                elif score_promedio <= -0.10:
                    st.error("🔴 ACCIÓN: EVITAR MERCADO (PÁNICO EN NOTICIAS)")
                else:
                    st.info("⚖️ ACCIÓN: ESPERAR (Rango Lateral / Sin confirmación)")
                else:
                    st.info(f"💼 Posición Activa: {pos['cantidad']:.4f} {nombre_activo} a ${pos['precio_compra']:,.2f}")
                
                    # --- NUEVA LÓGICA DE TRAILING STOP AUTOMÁTICA (OPCIÓN B - 2%) ---
                    # Si no existía el registro del precio máximo, lo inicializamos con el precio de compra
                if "precio_maximo_alcanzado" not in pos or pos["precio_maximo_alcanzado"] == 0.0:
                    pos["precio_maximo_alcanzado"] = pos["precio_compra"]
                
                # Si el precio actual es más alto que el máximo registrado, actualizamos el pico
                if precio_real > pos["precio_maximo_alcanzado"]:
                    pos["precio_maximo_alcanzado"] = precio_real
                    guardar_saldo_simulado(datos_simulador)
                
                # Calculamos el rendimiento actual basado en la compra inicial
                rendimiento = (precio_real - pos["precio_compra"]) / pos["precio_compra"]
                st.write(f"• **Rendimiento actual:** {rendimiento * 100:+.2f}%")
                
                # El suelo de protección móvil se coloca un 2% abajo del precio más alto alcanzado
                suelo_proteccion_movil = pos["precio_maximo_alcanzado"] * 0.98
                st.write(f"• **Precio Máximo Alcanzado:** ${pos['precio_maximo_alcanzado']:,.2f}")
                st.write(f"• **Suelo de Protección Móvil (2%):** ${suelo_proteccion_movil:,.2f}")
                
                # CONDICIÓN DE VENTA: Si el precio cae por debajo del suelo móvil O cruza la tendencia anual hacia abajo
                if precio_real <= suelo_proteccion_movil or precio_real < sma_200_anual:
                    if precio_real <= suelo_proteccion_movil:
                        st.error("🚨 VENTA POR TRAILING STOP: Cortando caída y asegurando racha.")
                    else:
                        st.error("🚨 VENTA POR CAMBIO DE TENDENCIA: Mercado se volvió Bajista a nivel anual.")
                        
                    if bot_activo:
                        valor_venta = pos["cantidad"] * precio_real * (1 - comision_broker)
                        datos_simulador["saldo_usdt"] += valor_venta
                        # Limpiamos la posición por completo para la siguiente operación
                        pos.update({"comprado": False, "precio_compra": 0.0, "cantidad": 0.0, "precio_maximo_alcanzado": 0.0})
                        guardar_saldo_simulado(datos_simulador)
                        st.rerun()

        except Exception as e:
            st.error(f"Error en el par {par}: {str(e)}")

        except Exception as e:
            st.error(f"Error en el par {par}: {str(e)}")
