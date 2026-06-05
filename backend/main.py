from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yfinance as yf
import pandas as pd
import js2py

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

class BacktestRequest(BaseModel):
    symbol: str
    code: str
    timeframe: str = "1d"

@app.post("/backtest")
def run_backtest(req: BacktestRequest):
    try:
        # 1. Descargar datos: Crypto, Forex, Acciones
        period = "6mo" if req.timeframe == "1d" else "1mo"
        df = yf.download(req.symbol, period=period, interval=req.timeframe)

        if df.empty:
            return {"error": "No hay datos para ese símbolo"}

        df = df.reset_index()
        df['Date'] = pd.to_datetime(df['Date'])

        candles = [{
            "time": int(row.Date.timestamp()),
            "open": float(row.Open),
            "high": float(row.High),
            "low": float(row.Low),
            "close": float(row.Close)
        } for _, row in df.iterrows()]

        # 2. Ejecutar código JS del usuario
        context = js2py.EvalJs()
        context.execute(req.code)

        signals = []
        position = 0
        trades = []
        entry_price = 0

        for i in range(len(candles)):
            signal = context.strategy(candles, i)

            if signal == 1 and position == 0: # COMPRA
                signals.append({"time": candles[i]["time"], "signal": 1})
                entry_price = candles[i]["close"]
                position = 1

            elif signal == -1 and position == 1: # VENTA
                signals.append({"time": candles[i]["time"], "signal": -1})
                profit_pct = (candles[i]["close"] - entry_price) / entry_price * 100
                trades.append(profit_pct)
                position = 0

        # 3. Métricas de backtest
        wins = len([t for t in trades if t > 0])
        total_trades = len(trades)
        win_rate = round(wins / total_trades * 100, 1) if total_trades > 0 else 0
        net_profit = round(sum(trades), 2) if trades else 0

        gross_profit = sum([t for t in trades if t > 0])
        gross_loss = abs(sum([t for t in trades if t < 0]))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss!= 0 else 0

        return {
            "candles": candles[-200:], # Últimas 200 velas para que cargue rápido
            "signals": signals,
            "metrics": {
                "winRate": win_rate,
                "profitFactor": profit_factor,
                "totalTrades": total_trades,
                "netProfit": net_profit
            }
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
def root():
    return {"status": "TradeLab Pro v2.0 API Running"}
