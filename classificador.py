import os
from enum import Enum

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

load_dotenv()

MODELO = "gemini-3.5-flash-lite"


class Fila(str, Enum):
    APLICACOES = "APLICACOES"
    CAMPO = "CAMPO"
    ACESSOS = "ACESSOS"
    REDE = "REDE"
    FORA_DO_ESCOPO = "FORA_DO_ESCOPO"
    PERGUNTAR = "PERGUNTAR"


class Classificacao(BaseModel):
    fila: Fila
    justificativa: str
    pergunta: str  # preenchida só quando a fila for PERGUNTAR


PROMPT = """Você é o analista de triagem de um time de suporte de TI.
Classifique o chamado abaixo em UMA das filas:

- APLICACOES: o próprio sistema ou software está com defeito: erros, travamentos, mensagens de falha, licenças.
- CAMPO: defeito físico em um equipamento: computador, impressora, periféricos, leitor, monitor.
- ACESSOS: senha, conta bloqueada, permissões, MFA, criação de usuário, pedidos repetidos de senha ou falha de autenticação em qualquer sistema.
- REDE: internet, Wi-Fi, cabo ou ponto de rede, VPN que cai, quedas e lentidão de conexão.
- FORA_DO_ESCOPO: assuntos que não são da TI, como RH, pagamento, reembolso e manutenção predial.
- PERGUNTAR: falta informação para escolher uma fila com segurança.

Como decidir:
1. Classifique pela CAUSA provável, não pelo programa citado. Se um aplicativo falha porque a conexão cai, a fila é REDE. Se ele pede senha sem parar, é ACESSOS.
2. Use PERGUNTAR quando o chamado não diz qual sistema, equipamento ou serviço está com problema, ou quando o sintoma pode ter causas de filas diferentes. Urgência não é motivo para pular a pergunta.
3. Se os sintomas apontam claramente para uma fila, escolha a fila. Não pergunte o que já está respondido no chamado.
4. Use apenas o que está escrito. Não presuma o que não foi dito.

Formato:
- Se escolher PERGUNTAR, escreva em "pergunta" uma pergunta curta e objetiva ao usuário. Nas outras filas, deixe "pergunta" vazia.
- Em "justificativa", explique a escolha em uma frase, citando a causa identificada.

Chamado: {texto}"""

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(
        timeout=30_000,
        retry_options=types.HttpRetryOptions(attempts=1),
    ),
)


def classificar(texto: str) -> Classificacao:
    resposta = client.models.generate_content(
        model=MODELO,
        contents=PROMPT.format(texto=texto),
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=Classificacao,
        ),
    )
    return resposta.parsed


if __name__ == "__main__":
    for exemplo in ["A impressora do 2º andar não imprime", "Deu problema aqui"]:
        resultado = classificar(exemplo)
        print(exemplo)
        print(f"  Fila: {resultado.fila.value}")
        print(f"  Por quê: {resultado.justificativa}")
        if resultado.pergunta:
            print(f"  Pergunta: {resultado.pergunta}")