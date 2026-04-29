# -*- coding: utf-8 -*-
import os
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from scipy.stats import pearsonr

import config_pipeline as cfg

archivo = cfg.ARCHIVO_COMPARACION_EXCEL
df = pd.read_excel(archivo)
timestamp = datetime.now().strftime("%Y%m%d_%H%M")
graficos_dir = os.path.join(cfg.DIRECTORIO_GRAFICOS_METRICAS, f"corrida_{timestamp}")
excel_salida = f"{cfg.PREFIJO_RESULTADO_COMPARACION}_{timestamp}.xlsx"

columnas_base = ["departamento", "radar_oficial_promedio"]
for c in columnas_base:
    if c not in df.columns:
        raise ValueError(f"Falta la columna requerida: {c}")

experimentos = [c for c in df.columns if c.lower().startswith("experimento_")]
if not experimentos and "radar_prensa_calculado" in df.columns:
    experimentos = ["radar_prensa_calculado"]
if not experimentos:
    raise ValueError("No se encontraron columnas de experimento (ejemplo: experimento_1, experimento_2)")

for col in ["radar_oficial_promedio"] + experimentos:
    df[col] = df[col].astype(str).str.replace(",", ".", regex=False).str.strip()
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["departamento"] = df["departamento"].astype(str).str.strip()

res_metricas = []
res_errores = []

for exp_col in experimentos:
    temp = df[["departamento", "radar_oficial_promedio", exp_col]].copy()
    temp = temp.dropna(subset=["radar_oficial_promedio", exp_col])
    if len(temp) < 2:
        continue

    y_real = temp["radar_oficial_promedio"]
    y_pred = temp[exp_col]

    mae = mean_absolute_error(y_real, y_pred)
    rmse = np.sqrt(mean_squared_error(y_real, y_pred))
    r2 = r2_score(y_real, y_pred)
    pearson_corr, pearson_p = pearsonr(y_real, y_pred)

    base_mape = y_real.replace(0, np.nan)
    mape = np.nanmean(np.abs((y_real - y_pred) / base_mape)) * 100
    sesgo = (y_pred - y_real).mean()

    res_metricas.append(
        {
            "experimento": exp_col,
            "n_departamentos": len(temp),
            "MAE": mae,
            "RMSE": rmse,
            "R2": r2,
            "Pearson": pearson_corr,
            "Pearson_p": pearson_p,
            "MAPE_pct": mape,
            "sesgo_promedio": sesgo,
        }
    )

    temp["experimento"] = exp_col
    temp["error"] = temp[exp_col] - temp["radar_oficial_promedio"]
    temp["error_absoluto"] = temp["error"].abs()
    temp = temp.rename(columns={exp_col: "radar_experimento"})
    res_errores.append(temp[["experimento", "departamento", "radar_experimento", "radar_oficial_promedio", "error", "error_absoluto"]])

if not res_metricas:
    raise ValueError("No hay datos suficientes para calcular métricas en los experimentos")

df_metricas = pd.DataFrame(res_metricas).sort_values("MAE")
df_errores = pd.concat(res_errores, ignore_index=True)

rank_base = df_metricas.copy()
rank_base["rank_MAE"] = rank_base["MAE"].rank(method="min", ascending=True)
rank_base["rank_RMSE"] = rank_base["RMSE"].rank(method="min", ascending=True)
rank_base["rank_MAPE"] = rank_base["MAPE_pct"].rank(method="min", ascending=True)
rank_base["rank_Pearson"] = rank_base["Pearson"].rank(method="min", ascending=False)
rank_base["score_ranking"] = (
    0.35 * rank_base["rank_MAE"]
    + 0.30 * rank_base["rank_RMSE"]
    + 0.20 * rank_base["rank_MAPE"]
    + 0.15 * rank_base["rank_Pearson"]
)
df_ranking = rank_base.sort_values("score_ranking").reset_index(drop=True)

print("\n========== MÉTRICAS POR EXPERIMENTO ==========")
print(df_metricas.to_string(index=False))

print("\n========== TOP 10 ERRORES ABSOLUTOS GLOBALES ==========")
print(df_errores.sort_values("error_absoluto", ascending=False).head(10).to_string(index=False))

print("\n========== RANKING GLOBAL DE EXPERIMENTOS ==========")
print(df_ranking[["experimento", "score_ranking", "MAE", "RMSE", "MAPE_pct", "Pearson"]].to_string(index=False))

os.makedirs(graficos_dir, exist_ok=True)

plt.figure(figsize=(12, 6))
plot_rank = df_ranking[["experimento", "score_ranking"]].copy()
sns.barplot(data=plot_rank, x="experimento", y="score_ranking", color="steelblue")
plt.title("Ranking global de experimentos (menor es mejor)")
plt.xlabel("Experimento")
plt.ylabel("Score ranking")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig(os.path.join(graficos_dir, "ranking_experimentos.png"), dpi=150)
plt.close()

for exp_col in experimentos:
    temp = df_errores[df_errores["experimento"] == exp_col].copy()
    if temp.empty:
        continue

    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=temp, x="radar_oficial_promedio", y="radar_experimento", s=90, color="steelblue")
    min_val = min(temp["radar_oficial_promedio"].min(), temp["radar_experimento"].min())
    max_val = max(temp["radar_oficial_promedio"].max(), temp["radar_experimento"].max())
    plt.plot([min_val, max_val], [min_val, max_val], linestyle="--", color="red")
    plt.title(f"{exp_col}: oficial vs experimento")
    plt.xlabel("Radar oficial promedio")
    plt.ylabel("Radar experimento")
    plt.tight_layout()
    plt.savefig(os.path.join(graficos_dir, f"{exp_col}_scatter.png"), dpi=150)
    plt.close()

    temp_ordenado = temp.sort_values("error", ascending=False)
    plt.figure(figsize=(14, 6))
    sns.barplot(data=temp_ordenado, x="departamento", y="error", palette="coolwarm")
    plt.axhline(0, color="black", linewidth=1)
    plt.title(f"{exp_col}: error por departamento (experimento - oficial)")
    plt.xlabel("Departamento")
    plt.ylabel("Error")
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(os.path.join(graficos_dir, f"{exp_col}_error_departamento.png"), dpi=150)
    plt.close()

with pd.ExcelWriter(excel_salida) as writer:
    df_metricas.to_excel(writer, sheet_name="metricas", index=False)
    df_ranking.to_excel(writer, sheet_name="ranking", index=False)
    df_errores.to_excel(writer, sheet_name="errores", index=False)

print(f"\nArchivo exportado: {excel_salida}")
print(f"Gráficos exportados en: {graficos_dir}")
