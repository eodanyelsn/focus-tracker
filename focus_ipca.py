"""
focus_ipca.py — Busca as projeções de IPCA do Boletim Focus na API do Banco Central,
salva o histórico em CSV e gera o gráfico nas cores da Legacy Research.

Roda sozinho toda segunda-feira pelo GitHub Actions (.github/workflows/atualizar-focus.yml).
"""
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # gera a imagem sem precisar de tela (o GitHub roda sem monitor)
import matplotlib.dates
import matplotlib.pyplot as plt
import pandas as pd
import requests

# Anos que aparecem no gráfico: o ano atual e o próximo (muda sozinho na virada do ano)
ANO = date.today().year
ANOS = [str(ANO), str(ANO + 1)]

PASTA_GRAFICOS = Path("graficos")
PASTA_DADOS = Path("dados")

# Cores da Legacy
FUNDO = "#000000"
TEXTO = "#FFFFFF"
GRADE = "#333333"
CORES = ["#00C8FF", "#3D6BFF"]  # azul fluorescente e azul royal


def buscar_dados():
    """Pede ao Banco Central as projeções de IPCA para os anos de ANOS."""
    anos_filtro = "%20or%20".join(f"DataReferencia%20eq%20'{a}'" for a in ANOS)
    url = (
        "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
        f"?$filter=Indicador%20eq%20'IPCA'%20and%20({anos_filtro})%20and%20baseCalculo%20eq%200"
        "&$orderby=Data%20desc"
        "&$top=400"
        "&$format=json"
        "&$select=Data,DataReferencia,Mediana"
    )
    headers = {"User-Agent": "Mozilla/5.0 (focus-tracker; Legacy Research)"}
    resposta = requests.get(url, headers=headers, timeout=60)
    resposta.raise_for_status()

    df = pd.DataFrame(resposta.json()["value"])
    df["Data"] = pd.to_datetime(df["Data"])
    return df.sort_values("Data")


def gerar_grafico(df):
    """Desenha uma linha por ano, com a meta de inflação, e salva o PNG."""
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(FUNDO)
    ax.set_facecolor(FUNDO)

    # Meta de inflação (3%) e intervalo de tolerância (1,5% a 4,5%)
    ax.axhspan(1.5, 4.5, color="#FFFFFF", alpha=0.06)
    ax.axhline(3.0, color="#AAAAAA", linestyle="--", linewidth=1.2)
    ax.text(df["Data"].iloc[0], 3.0, " Meta 3%", color="#AAAAAA", va="bottom", fontsize=10)
    ax.text(df["Data"].iloc[0], 4.5, " Teto 4,5%", color="#777777", va="bottom", fontsize=9)

    # Uma linha para cada ano
    for ano, cor in zip(ANOS, CORES):
        dados = df[df["DataReferencia"] == ano]
        if dados.empty:
            continue
        ax.plot(dados["Data"], dados["Mediana"], color=cor, linewidth=2.5, label=f"IPCA {ano}")
        ultimo = dados.iloc[-1]
        ax.annotate(f"{ultimo['Mediana']:.2f}%", (ultimo["Data"], ultimo["Mediana"]),
                    xytext=(8, 0), textcoords="offset points",
                    color=cor, fontweight="bold", va="center")

    data_txt = df["Data"].max().strftime("%d/%m/%Y")
    ax.set_title(f"IPCA – projeções do Focus (mediana, %) · atualizado em {data_txt}",
                 color=TEXTO, fontsize=13, fontweight="bold")
    ax.set_ylabel("%", color=TEXTO)
    ax.tick_params(colors=TEXTO)
    for borda in ax.spines.values():
        borda.set_color(GRADE)
    ax.grid(color=GRADE, linewidth=0.6)
    ax.margins(x=0.08)
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d/%m"))
    ax.legend(facecolor=FUNDO, edgecolor=GRADE, labelcolor=TEXTO, loc="lower left")
    fig.text(0.99, 0.01, "Legacy Research · Fonte: Focus/BCB", color="#888888", ha="right", fontsize=9)

    plt.tight_layout()
    PASTA_GRAFICOS.mkdir(exist_ok=True)
    caminho = PASTA_GRAFICOS / "ipca_focus.png"
    plt.savefig(caminho, dpi=200, facecolor=FUNDO)
    plt.close(fig)
    return caminho


def salvar_dados(df):
    """Guarda a tabela em CSV, para ter o histórico no repositório."""
    PASTA_DADOS.mkdir(exist_ok=True)
    caminho = PASTA_DADOS / "focus_ipca.csv"
    df.to_csv(caminho, index=False)
    return caminho


if __name__ == "__main__":
    tabela = buscar_dados()
    print("Dados salvos em", salvar_dados(tabela))
    print("Gráfico salvo em", gerar_grafico(tabela))
