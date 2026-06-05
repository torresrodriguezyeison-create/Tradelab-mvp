from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/backtest")
async def backtest(
    file: UploadFile = File(...),
    capital: float = Form(10000.0),
    ma_fast: int = Form(10),
    ma_slow: int = Form(30),
):
    if ma_fast >= ma_slow:
        return {"error": "ma_fast debe ser menor que ma_slow"}

    content = await file.read()
    try:
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))
    except Exception:
        return {"error": "No se pudo leer el CSV. Verifica el formato."}

    df.columns = [c.strip().lower() for c in df.columns]

    close_col = next((c for c in df.columns if "close" in c), None)
    if close_col is None:
        return {"error": "No se encontró columna 'close' en el CSV."}

    df["close"] = pd.to_numeric(df[close_col], errors="coerce")
    df = df.dropna(subset=["close"]).reset_index(drop=True)

    if len(df) < ma_slow:
        return {"error": f"El CSV necesita al menos {ma_slow} filas de datos."}

    df["ma_fast"] = df["close"].rolling(ma_fast).mean()
    df["ma_slow"] = df["close"].rolling(ma_slow).mean()
    df = df.dropna().reset_index(drop=True)

    balance = capital
    position = None
    entry_price = 0.0
    trades = 0

    for i in range(1, len(df)):
        prev_fast = df["ma_fast"].iloc[i - 1]
        prev_slow = df["ma_slow"].iloc[i - 1]
        curr_fast = df["ma_fast"].iloc[i]
        curr_slow = df["ma_slow"].iloc[i]
        price = df["close"].iloc[i]

        if prev_fast <= prev_slow and curr_fast > curr_slow:
            if position is None:
                position = "long"
                entry_price = price

        elif prev_fast >= prev_slow and curr_fast < curr_slow:
            if position == "long":
                pnl = (price - entry_price) / entry_price
                balance *= 1 + pnl
                position = None
                trades += 1

    if position == "long":
        last_price = df["close"].iloc[-1]
        pnl = (last_price - entry_price) / entry_price
        balance *= 1 + pnl
        trades += 1

    return {
        "profit_pct": round((balance - capital) / capital * 100, 2),
        "final_capital": round(balance, 2),
        "trades": trades,
    }
