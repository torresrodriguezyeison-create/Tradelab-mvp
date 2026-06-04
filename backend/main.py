from fastapi import FastAPI, UploadFile
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
async def run_backtest(file: UploadFile, capital: float = 10000):
    content = await file.read()
    df = pd.read_csv(io.StringIO(content.decode('utf-8')))
    
    df['MA_Fast'] = df['Close'].rolling(10).mean()
    df['MA_Slow'] = df['Close'].rolling(30).mean()
    df['Signal'] = 0
    df.loc[df['MA_Fast'] > df['MA_Slow'], 'Signal'] = 1
    df.loc[df['MA_Fast'] < df['MA_Slow'], 'Signal'] = -1
    
    df['Returns'] = df['Close'].pct_change() * df['Signal'].shift(1)
    total_return = (df['Returns'] + 1).prod() - 1
    
    return {
        "total_return": round(total_return * 100, 2),
        "final_capital": round(capital * (1 + total_return), 2),
        "trades": int(df['Signal'].diff().abs().sum() / 2)
    }
