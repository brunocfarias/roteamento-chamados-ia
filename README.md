# Roteamento de chamados com IA

> Classificador em Python que lê um chamado de suporte e indica a fila certa usando o **Gemini**, ou faz uma pergunta ao usuário quando falta informação. Medido com conjuntos de avaliação, com a evolução do prompt documentada versão a versão.

**Autor:** Bruno de Campos Farias · **Stack:** Python · Gemini API (`google-genai`) · Pydantic

## De onde veio este projeto

Este projeto é a continuação de um [case de Product Discovery](https://github.com/brunocfarias/discovery-triagem-chamados-ia). Lá, validei com 5 analistas de suporte a ideia de uma IA que fizesse a triagem completa dos chamados. Os dados mostraram outra coisa: a dor real não era o tempo de triagem, e sim o **chamado que cai na fila errada**. A IA também errava justamente nos chamados vagos, como "meu sistema não abre".

A decisão foi pivotar para uma IA focada só em **roteamento**. Este repositório é a construção e a medição desse pivô.

## Como funciona

```
Chamado ──> Prompt com as regras de triagem ──> Gemini ──> JSON validado
                                                          ├─ fila
                                                          ├─ justificativa
                                                          └─ pergunta (se faltar informação)
```

| Fila | Quando |
| --- | --- |
| `APLICACOES` | O sistema ou software está com defeito |
| `CAMPO` | Defeito físico em um equipamento |
| `ACESSOS` | Senha, bloqueio, permissão, MFA, autenticação |
| `REDE` | Internet, Wi-Fi, cabo, VPN que cai |
| `FORA_DO_ESCOPO` | Não é da TI: RH, financeiro, predial |
| `PERGUNTAR` | Falta informação para decidir com segurança |

Decisões técnicas:

- **Saída estruturada:** a resposta segue um schema Pydantic, e a fila é um `Enum`. O modelo não consegue inventar uma fila que não existe, e o código recebe um objeto pronto, sem tratar texto livre.
- **`temperature=0`:** o mesmo chamado gera a mesma resposta, o que é essencial para medir e comparar versões.
- **Justificativa obrigatória:** cada classificação explica a causa identificada. Foi lendo as justificativas que descobri por que o modelo errava.
- **Modelo lite e versão fixa:** classificar texto curto não precisa de um modelo grande. A versão é fixa (nada de `-latest`) para que os resultados não mudem sem eu mexer em nada.
- **Retry com backoff:** quando a API responde 503 (servidor ocupado), o avaliador espera 10s, depois 20s, e tenta de novo. Falhas de API são contadas à parte e não entram na acurácia, porque não são erro do modelo.

## Como avaliei

Três conjuntos de chamados fictícios, cada um com a fila correta definida antes do teste:

| Conjunto | Chamados | Papel |
| --- | --- | --- |
| [`chamados.csv`](chamados.csv) | 30 | Base: chamados bem escritos, 5 por fila |
| [`chamados_dificeis.csv`](chamados_dificeis.csv) | 12 | Realistas: erros de digitação, informação misturada, pistas que confundem |
| [`chamados_testes.csv`](chamados_testes.csv) | 15 | **Teste final:** escritos depois do prompt pronto e nunca usados para ajustá-lo |

O [`avaliar.py`](avaliar.py) roda um conjunto inteiro, calcula a acurácia geral e por fila, lista os erros e salva tudo em [`resultados/`](resultados/).

## Resultados

| Versão | Base | Difíceis | Teste final |
| --- | --- | --- | --- |
| v1 | 28/29 (97%)* | **8/12 (67%)** | — |
| v2 | 30/30 (100%) | 12/12 (100%) | **15/15 (100%)** |

\* 1 chamado ficou fora da conta por falha da API (503).

### O que a v1 ensinou

Com chamados bem escritos, a v1 parecia pronta: 97%. Com chamados parecidos com os reais, caiu para **67%**, abaixo da meta de 70% definida no discovery. Os erros seguiam padrões:

| Padrão | Exemplo | O que o modelo fez |
| --- | --- | --- |
| Classificou pelo programa citado, não pela causa | "a net cai e o Teams trava nas calls" | Focou no Teams, não na rede |
| Não percebeu que faltava informação | "o sistema ta lento" | Mandou para APLICACOES sem saber qual sistema |
| Fronteira entre filas pouco clara | "cabo de rede não funciona" | Tratou como defeito de equipamento |

O erro em "meu sistema não abre, preciso urgente" foi o mesmo ponto fraco que os analistas apontaram no discovery.

### O que mudou na v2

Em vez de criar uma regra para cada chamado que errou, o que seria decorar a prova, o prompt ganhou **princípios gerais**:

1. **Classificar pela causa provável, não pelo programa citado.**
2. **Perguntar quando o chamado não diz qual sistema ou equipamento tem problema**, ou quando o sintoma pode ter causas diferentes. Urgência não dispensa a pergunta.
3. **Decidir quando os sintomas são claros**, sem perguntar o que já foi respondido.
4. **Fronteiras explícitas entre as filas**, como "cabo e ponto de rede são REDE".

O prompt completo está em [`classificador.py`](classificador.py), e cada versão está no histórico de commits.

### Como ler os 100%

A v2 foi escrita olhando os erros dos conjuntos base e difícil, então os 100% neles mostram que os problemas conhecidos foram corrigidos, não que o modelo é perfeito. Por isso existe o **teste final**: 15 chamados inéditos, escritos com base na minha experiência em suporte, que o prompt nunca viu.

Mesmo assim, 15 de 15 é uma amostra pequena. Ela permite afirmar, com segurança razoável, que a acurácia real fica **acima de 80%**, não que ela é 100%. E chamados reais costumam ser mais bagunçados: textos longos, dois problemas no mesmo chamado, e-mails encaminhados.

## Próximos passos

1. **Validar com chamados reais anonimizados**, em volume, com dados pessoais mascarados antes do envio ao modelo.
2. **Usar as filas reais de um time**, que têm outras fronteiras e nomes.
3. **Medir o custo e o tempo por chamado**, para estimar a operação em escala.
4. **Integrar a uma ferramenta de chamados**, sugerindo a fila e a pergunta para o analista confirmar com um clique, mantendo o humano na decisão.

## Como rodar

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1   |   Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

Crie um arquivo `.env` com sua chave do [Google AI Studio](https://aistudio.google.com/apikey):

```
GEMINI_API_KEY=sua_chave
```

```bash
python classificador.py                              # testa dois exemplos
python avaliar.py v2 chamados.csv                    # avalia um conjunto
python listar_modelos.py                             # lista os modelos disponíveis para a sua chave
```

## Estrutura

```
├── classificador.py          # prompt, schema da resposta e chamada ao Gemini
├── avaliar.py                # roda um conjunto, mede a acurácia e salva os resultados
├── chamados.csv              # conjunto base
├── chamados_dificeis.csv     # conjunto realista
├── chamados_testes.csv       # teste final inédito
├── resultados/               # saída de cada rodada
├── teste_conexao.py          # teste inicial da API
└── listar_modelos.py         # modelos disponíveis
```
