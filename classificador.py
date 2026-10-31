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

- APLICACOES: erros e falhas em sistemas, softwares, e-mail, Office e Teams.
- CAMPO: problemas físicos de hardware: computador, impressora, periféricos, equipamentos.
- ACESSOS: senhas, contas bloqueadas, permissões, MFA, criação de usuários, erro de autenticação.
- REDE: internet, Wi-Fi, rede local e quedas de conexão.
- FORA_DO_ESCOPO: assuntos que não são da TI, como RH, financeiro e manutenção predial.
- PERGUNTAR: o chamado não tem informação suficiente para escolher uma fila com segurança.

Regras:
- Use apenas o que está escrito no chamado. Não presuma o que não foi dito.
- Se escolher PERGUNTAR, escreva em "pergunta" uma pergunta curta e objetiva ao usuário.
  Nas outras filas, deixe "pergunta" vazia.
- Em "justificativa", explique a escolha em uma frase.

Chamado: {texto}"""

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=30_000),
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