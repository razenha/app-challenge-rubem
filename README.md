# Stark Bank Backend Challenge

## Visão geral

A aplicação simula o backend interno de uma empresa que usa o Stark Bank como provedor de pagamentos. A cada 3 horas, ela gera invoices a cada aleatórias via SDK do Stark Bank; quando uma invoice é paga e creditada, recebe um webhook e enfileira uma transferência do valor líquido recebido (descontando eventuais fees) para uma conta de destino específica.

## Pré-requisitos

- Python 3.14
- PostgreSQL
- Redis
- Credenciais Stark Bank **sandbox** (`project_id` + chave privada `.pem`)

## Setup

 - Copiar o .env.example para .env e preencher com as credenciais de acesso a API do Stark Bank e as URLs do Redis e PostgreSQL. 
 - Executar *make venv* para criar o virtualenv e instalar as dependências.
 - Executar *make db_setup* para criar o database, as tabelas e o seeds com os dados essenciais da aplicação.
 - Executar *make test* para rodar os testes.

## Iniciar app

### Local

Em dois terminais:

```bash
# terminal 1 — servidor Flask
make run

# terminal 2 — worker Huey (jobs periódicos + jobs enfileirados)
make worker
```

### Docker

```bash
docker compose -f docker/docker-compose.yml --env-file .env up --build
```

O compose sobe `web` e `worker`; Postgres e Redis devem rodar separadamente. Em Linux/WSL, use `host.docker.internal` no `DATABASE_URL`/`REDIS_URL` (o `.env.example` traz o template comentado).

Caso queria forcar a execução do job de criar invoices aleatórias a cada 3 horas, execute:

```bash
make run_create_invoices_job
```


## Endpoints

| Método | Path       | Descrição                                  |
|--------|------------|--------------------------------------------|
| POST   | `/webhook` | Recebe eventos do Stark Bank (invoice/transfer) |
| GET    | `/health`  | Liveness check — retorna `{"status":"ok"}`  |

## Testes

Atualmente 39 testes e cobertura 89%. Os testes focam em cenários de negócio (webhook de invoice criado/creditado/pago, jobs de criação de invoice e envio de transfer), usando um banco Postgres de teste real (sem mocks do DB) e mocks apenas da SDK do Stark Bank. Os testes usam a ENV TEST_DATABASE_URL.

## Arquitetura

```
          ┌─────────────┐   webhook    ┌──────────────┐
          │  Stark Bank │ ───────────▶ │  web (Flask) │
          │     API     │ ◀─────────── │   Gunicorn   │
          └─────────────┘   SDK call   └──────┬───────┘
                 ▲                            │
                 │ SDK call                   ▼
          ┌──────┴───────┐              ┌──────────┐
          │ worker (Huey)│ ──────────▶  │ Postgres │
          │  consumer    │ ◀──────────  └──────────┘
          └──────┬───────┘    Peewee
                 │
                 ▼
            ┌─────────┐
            │  Redis  │  (fila Huey + schedule)
            └─────────┘
```

- **web (Flask + Gunicorn)** — recebe webhooks, valida assinatura, aplica a transição de status e enfileira trabalho assíncrono.
- **worker (Huey)** — executa o job periódico de criação de invoices (cron) e o job assíncrono de envio de transfer.
- **Postgres (Peewee)** — persistência de invoices, transfers, destinos e log de requests.
- **Redis** — broker/fila do Huey.

## Fluxo de execução

1. **Geração** — o job periódico `create_invoices` dispara via scheduled jobs do Huey. Gera entre 8 e 12 invoices com valores aleatórios, gera uma chave identificadora (correlation_id), persiste localmente  e envia as invoices para a API do Stark Bank via SDK, com a correlation_id enviada no campo tag.
2. **Pagamento** — o pagador paga a invoice; o Stark Bank entrega webhook `invoice.credited`. No ambiente sandbox, parte das invoices enviadas são pagas automaticamente.
3. **Atualização de estado** — o handler do webhook procura a invoice local (via `correlation_id` propagado), valida a transição de status da invoice e persiste o novo estado dentro de uma transação.
4. **Repasse** — ao receber que a invoice foi paga e o valor creditado (invoice com status `CREDITED`), enfileira a task (`send_transfer`) para transferiir  com o valor líquido recebido (`amount − fee`).
5. **Envio do repasse** — o worker consome a task, cria a transferência via `starkbank.transfer.create` para a conta de destino padrão e persiste o retorno.

## Decisões técnicas e motivações

### Flask + Peewee

Decidi usar o Flask como framework e o Peewee para persistência por serem libs mais leves. A app tem poucos models e apenas um endpoint (além do endpoint de heathcheck).

### Jobs assíncronos Huey

Mesmo para um projeto relativamente pequeno, acredito na necessidade de ter uma ferramenta de jobs assíncronos. O app deve solicitar via API a transferência do valor pago da invoice ao receber o webhook de invoice com status `CREDITED`, decidi colocar a chamada da API em um job assíncrono para diminuir o tempo de resposta do webhook, evitar falhar a chamada do webhook por problemas na chamada de API e ser mais tolerante a falhar, com a possibilidade de fazer retry. 

A escolha do huey foi por ele ser uma lib mais enxuta, com suporte nativo a periodic tasks via `crontab`. Algo como celery ou então Kafka seria um overkill para esse projeto.

### Strategy pattern para webhooks

Cada evento enviado via webhook (`invoice.created`, `invoice.credited`, `transfer.success`…) é resolvido por uma classe dedicada em `app/services/webhooks/strategies/`. O objetivo do uso desse pattern é  seperação de responsabilidades (cada classe lida com um tipo de evento) e diminuir esforço e a quantidade de alterações caso preciso adicionar novos tipos de evento (basta criar uma nova classe strategy e adicionar o mapeamento no `StarkbankWebhookEventFactory`)

### Transição de status 

As transições de status validadas nos modelos (`Invoice` e `Transfer`). Se um webhook chegar fora de ordem (por exemplo `paid` após `credited`) ou com algum status que não seria compatível (`canceled` depois de `paid`), o sistema rejeita a transição em vez de corromper o estado silenciosamente. 

É gerado uma exception para constar no log e possívels ferramentas de APM, além de retornar um status code de erro para a API do Stark Bank. Como a API do Stark Bank tem um mecanismo de retry para os events  enviados via webhook, se for algum caso de apenas atraso no envio de um status anterior (ex. a invoice foi paga e creditada, mas por algum motivo o envio do status `paid` atrasou e foi enviado o  `credited` antes do `paid`), o próprio mecanismo de retry vai fazer com que a situação seja corrigida eventualmente. Caso seja uma inconsistência mesmo e não apenas atraso, a situação pode ser monitorada através de logs e APM.

### `api_log` para auditoria

Toda a comunicação com a API do Stark Bank é registrada (método, path, body, status, duração) na `api_log` para fiz de auditoria/troubleshooting

### Tratamento de dados pessoais de identificação

A classe `PiiSanitizer` tem uma funcionalidade de mascarar dados pessoais de identificação. Atualmente, é usado nos logs da aplicação e na `api_log`, garantindo que dados pessoais recebidos pela aplicação possam facilmente ser tratados.

### Uso da `correlation_id` no model `Invoice`

Na API do Stark Bank, a `Transfer` tem um `external_id`, permitindo que o client gere uma chave de identificação que possa ser usado para relacionar o `Transfer` enviado via webhook com o que está no banco de dados. Isso não acontece com a `Invoice`. Inicialmente, o estava enviando as invoices via API, salvando o `id` retornando pela chamada da API no campo `stark_id` e usando esse campo para relacionar as invoices no momento da chamada do webhook. O problema é que pode eventualmente acontecer de o Stark Bank processar e retornar o webhook de `created` antes da thread que fez a chamada da API original ter preenchido e transacionado no banco o `stark_id`. Para resolver isso, simulei com campo como o `external_id` do Transfer usando o campo tags da `invoice`. Criei um campo `correlation_id` como uuid e envio esse campo na chamada da API de criação de invoice dentro do atributo de tags. Ao receber o webhook com um evento de invoice, uso essa correlation_id, que é enviada na tag, para identificar a invoice no banco de dados da app.