import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()  # lê o arquivo .env e carrega a chave

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(
        timeout=30_000,  # desiste depois de 30 segundos (valor em milissegundos)
        retry_options=types.HttpRetryOptions(attempts=1),  # tenta uma vez só
    ),
)

resposta = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents="Responda apenas: conexão funcionando",
)
print(resposta.text)