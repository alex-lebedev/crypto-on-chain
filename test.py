#!/usr/bin/env python3
import os
import math
import requests
import pandas as pd
import datetime
import matplotlib.pyplot as plt

# ---------------------------------------------
# Configuration: меняем только список активов
# ---------------------------------------------
ASSETS = ["dogecoin", "neo", "solana"]  # идентификаторы CoinCap
HISTORY_DAYS = 90                      # окно в днях

def fetch_coincap_history(asset: str, days: int) -> pd.DataFrame:
    """
    Берёт у CoinCap public API daily history:
      - priceUsd
      - marketCapUsd
      - volumeUsd24Hr
      - supply
    за последние `days` дней.
    """
    end_ts = int(datetime.datetime.utcnow().timestamp() * 1000)
    start_ts = end_ts - days * 24 * 3600 * 1000
    url = (
        f"https://api.coincap.io/v2/assets/{asset}/history"
        f"?interval=d1&start={start_ts}&end={end_ts}"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json().get("data", [])
    df = pd.DataFrame(data)
    # преобразуем типы
    df["date"] = pd.to_datetime(df["time"], unit="ms").dt.floor("d")
    for col in ("priceUsd", "marketCapUsd", "volumeUsd24Hr", "supply"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # оставим только date и нужные колонки
    cols = ["date", "priceUsd", "marketCapUsd", "volumeUsd24Hr", "supply"]
    return df[cols].dropna(subset=["priceUsd"]).set_index("date")

def store_data(df: pd.DataFrame, filename: str):
    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    df.to_csv(filename)
    print(f"[{filename}] saved, rows={len(df)}")

def plot_metrics(asset: str, df: pd.DataFrame):
    """
    Строит столько панелей, сколько доступно метрик (marketCapUsd, volumeUsd24Hr, supply),
    накладывая цену пунктиром.
    """
    available = [col for col in ("marketCapUsd", "volumeUsd24Hr", "supply") if col in df.columns]
    if not available:
        print(f"No metrics to plot for {asset}.")
        return

    n = len(available)
    cols = min(3, n)
    rows = math.ceil(n / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(6*cols, 4*rows), squeeze=False)
    fig.suptitle(f"{asset.capitalize()} — Price, Market Cap, Volume, Supply", fontsize=16)

    def overlay_price(ax):
        ax2 = ax.twinx()
        ax2.plot(df.index, df["priceUsd"], "--", alpha=0.6, label="Price USD")
        ax2.set_ylabel("Price USD")
        ax2.legend(loc="upper right")

    for idx, metric in enumerate(available):
        r, c = divmod(idx, cols)
        ax = axes[r][c]
        ax.plot(df.index, df[metric], linewidth=2, label=metric)
        ax.set_title(metric)
        ax.set_xlabel("Date")
        ax.grid(True)
        overlay_price(ax)
    # спрячем лишние оси
    total = rows * cols
    for idx in range(n, total):
        r, c = divmod(idx, cols)
        axes[r][c].axis("off")

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    out = f"{asset}_onchain_coincap.png"
    plt.savefig(out, dpi=300)
    plt.close(fig)
    print(f"[Plot saved] {out}")

def main():
    for asset in ASSETS:
        df = fetch_coincap_history(asset, HISTORY_DAYS)
        store_data(df, f"{asset}_coincap_history.csv")
        plot_metrics(asset, df)

if __name__ == "__main__":
    main()
