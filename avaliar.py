import csv
import sys
import time
from collections import Counter
from pathlib import Path

from google.genai import errors

from classificador import MODELO, classificar

PAUSA_SEGUNDOS = 4  # respeita o limite de chamadas por minuto do plano gratuito
TENTATIVAS = 3


def carregar_chamados(caminho):
    with open(caminho, encoding="utf-8") as arquivo:
        return list(csv.DictReader(arquivo))


def classificar_com_retry(texto):
    """Tenta de novo quando o servidor está ocupado (erros 5xx), esperando mais a cada vez."""
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            return classificar(texto)
        except errors.ServerError:
            if tentativa == TENTATIVAS:
                raise
            espera = 10 * tentativa
            print(f"      servidor ocupado, nova tentativa em {espera}s...")
            time.sleep(espera)


def main():
    # uso: python avaliar.py <rodada> [arquivo]
    versao = sys.argv[1] if len(sys.argv) > 1 else "v1"
    arquivo_chamados = sys.argv[2] if len(sys.argv) > 2 else "chamados.csv"
    chamados = carregar_chamados(arquivo_chamados)
    resultados = []

    for i, chamado in enumerate(chamados, start=1):
        try:
            resposta = classificar_com_retry(chamado["texto"])
            prevista = resposta.fila.value
            justificativa = resposta.justificativa
        except Exception as erro:
            prevista = "FALHA_API"
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
        status = "OK  " if acertou else ("API " if prevista == "FALHA_API" else "ERRO")
        print(f"[{i:02}/{len(chamados)}] {status} {chamado['texto'][:50]}")
        time.sleep(PAUSA_SEGUNDOS)

    # falha de API não é erro do modelo: fica fora da acurácia
    respondidos = [r for r in resultados if r["fila_prevista"] != "FALHA_API"]
    falhas_api = len(resultados) - len(respondidos)
    acertos = sum(r["acertou"] for r in respondidos)

    print(f"\nModelo: {MODELO} | Rodada: {versao} | Arquivo: {arquivo_chamados}")
    print(f"Acurácia: {acertos}/{len(respondidos)} ({acertos / len(respondidos):.0%})")
    if falhas_api:
        print(f"Falhas de API (fora da conta): {falhas_api}")

    print("\nAcurácia por fila:")
    total_por_fila = Counter(r["fila_esperada"] for r in respondidos)
    acertos_por_fila = Counter(r["fila_esperada"] for r in respondidos if r["acertou"])
    for fila, quantidade in sorted(total_por_fila.items()):
        print(f"  {fila:<15} {acertos_por_fila[fila]}/{quantidade}")

    erros_modelo = [r for r in respondidos if not r["acertou"]]
    if erros_modelo:
        print("\nErros do modelo:")
        for r in erros_modelo:
            print(f"  #{r['id']} esperado {r['fila_esperada']}, veio {r['fila_prevista']}: {r['texto']}")

    Path("resultados").mkdir(exist_ok=True)
    saida = Path("resultados") / f"{versao}_{Path(arquivo_chamados).stem}.csv"
    with open(saida, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=resultados[0].keys())
        escritor.writeheader()
        escritor.writerows(resultados)
    print(f"\nResultados salvos em {saida}")


if __name__ == "__main__":
    main()