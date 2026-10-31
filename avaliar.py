import csv
import sys
import time
from collections import Counter
from pathlib import Path

from classificador import MODELO, classificar

ARQUIVO_CHAMADOS = "chamados.csv"
PAUSA_SEGUNDOS = 4  # respeita o limite de chamadas por minuto do plano gratuito


def carregar_chamados(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def main():
    # nome da rodada, ex.: python avaliar.py v1
    versao = sys.argv[1] if len(sys.argv) > 1 else "v1"
    chamados = carregar_chamados(ARQUIVO_CHAMADOS)
    resultados = []

    for i, chamado in enumerate(chamados, start=1):
        try:
            resposta = classificar(chamado["texto"])
            prevista = resposta.fila.value
            justificativa = resposta.justificativa
        except Exception as erro:  # um chamado com erro não derruba a avaliação inteira
            prevista = "ERRO"
            justificativa = str(erro)[:200]

        acertou = prevista == chamado["fila_esperada"]
        resultados.append({
            "id": chamado["id"],
            "texto": chamado["texto"],
            "fila_esperada": chamado["fila_esperada"],
            "fila_prevista": prevista,
            "acertou": acertou,
            "justificativa": justificativa,
        })
        status = "OK  " if acertou else "ERRO"
        print(f"[{i:02}/{len(chamados)}] {status} {chamado['texto'][:50]}")
        time.sleep(PAUSA_SEGUNDOS)

    total = len(resultados)
    acertos = sum(r["acertou"] for r in resultados)
    print(f"\nModelo: {MODELO} | Rodada: {versao}")
    print(f"Acurácia geral: {acertos}/{total} ({acertos / total:.0%})")

    print("\nAcurácia por fila:")
    total_por_fila = Counter(r["fila_esperada"] for r in resultados)
    acertos_por_fila = Counter(r["fila_esperada"] for r in resultados if r["acertou"])
    for fila, quantidade in sorted(total_por_fila.items()):
        print(f"  {fila:<15} {acertos_por_fila[fila]}/{quantidade}")

    erros = [r for r in resultados if not r["acertou"]]
    if erros:
        print("\nErros:")
        for r in erros:
            print(f"  #{r['id']} esperado {r['fila_esperada']}, veio {r['fila_prevista']}: {r['texto']}")

    Path("resultados").mkdir(exist_ok=True)
    saida = Path("resultados") / f"{versao}.csv"
    with open(saida, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=resultados[0].keys())
        escritor.writeheader()
        escritor.writerows(resultados)
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()