import sqlite3
from urllib.parse import quote

import pandas as pd
import requests

INDICADORES = ["IPCA", "Selic", "Câmbio", "PIB Total"]
ANOS = ["2026", "2027"]


def buscar(indicador):
    """Pede ao Banco Central as projeções de um indicador."""
    anos = "%20or%20".join(f"DataReferencia%20eq%20'{a}'" for a in ANOS)
    url = (
        "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
        f"?$filter=Indicador%20eq%20'{quote(indicador)}'%20and%20({anos})%20and%20baseCalculo%20eq%200"
        "&$top=400&$format=json&$select=Indicador,Data,DataReferencia,Mediana"
    )
    resposta = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (focus-tracker)"}, timeout=60)
    resposta.raise_for_status()
    return pd.DataFrame(resposta.json()["value"])


# 1) Busca os dados e salva tudo numa tabela "focus" dentro do banco focus.db
dados = pd.concat([buscar(i) for i in INDICADORES])
banco = sqlite3.connect("focus.db")
dados.to_sql("focus", banco, if_exists="replace", index=False)
print("Linhas salvas no banco:", len(dados))

# 2) Três consultas em SQL
consultas = {
    "Última projeção de cada indicador para 2026": """
        SELECT Indicador, Data, Mediana
        FROM focus
        WHERE DataReferencia = '2026'
          AND Data = (SELECT MAX(Data) FROM focus)
        ORDER BY Indicador;
    """,
    "Maior e menor projeção de IPCA 2026 no período": """
        SELECT MIN(Mediana) AS menor, MAX(Mediana) AS maior
        FROM focus
        WHERE Indicador = 'IPCA' AND DataReferencia = '2026';
    """,
    "Média das projeções por indicador e ano": """
        SELECT Indicador, DataReferencia AS ano, ROUND(AVG(Mediana), 2) AS media
        FROM focus
        GROUP BY Indicador, DataReferencia
        ORDER BY Indicador, ano;
    """,
}

for titulo, sql in consultas.items():
    print("\n" + titulo)
    print(pd.read_sql(sql, banco).to_string(index=False))

banco.close()
