# 💬 Chat gRPC — Nós Simétricos

Chat em tempo real implementado com **gRPC bidirecional**, onde cada participante é um nó igual — sem distinção fixa de cliente ou servidor. Mensagens podem ser enviadas e recebidas ao mesmo tempo usando threads.

---

## 📋 Pré-requisitos

- Python **3.8** ou superior
- pip

Verifique sua versão do Python:
```bash
python --version
```

---

## 📁 Estrutura do projeto

```
grpc-chat/
├── chat.proto           # Contrato gRPC (definição das mensagens e serviço)
├── generate.py          # Script para gerar os arquivos Python do proto
├── node.py              # Lógica do nó (servidor + cliente simultâneos)
├── requirements.txt     # Dependências do projeto
└── README.md
```

> **Atenção:** Os arquivos `chat_pb2.py` e `chat_pb2_grpc.py` **não existem ainda** — eles são gerados pelo `generate.py` no passo 3.

---

## 🚀 Como rodar

### 1. Clone ou baixe o projeto

Coloque todos os arquivos em uma mesma pasta, por exemplo `grpc-chat/`, e acesse ela no terminal:

```bash
cd grpc-chat
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Gere os arquivos Python a partir do `.proto`

```bash
python generate.py
```

Após rodar, dois novos arquivos serão criados na pasta:
- `chat_pb2.py` — classes das mensagens
- `chat_pb2_grpc.py` — classes do serviço gRPC

> Só é necessário rodar este passo **uma vez**, ou novamente caso o `chat.proto` seja modificado.

### 4. Inicie os nós

Abra **dois terminais** na mesma pasta e rode um comando em cada um:

**Terminal 1:**
```bash
python node.py Alice 50051 localhost 50052
```

**Terminal 2:**
```bash
python node.py Bob 50052 localhost 50051
```

Aguarde a mensagem de confirmação de conexão e comece a digitar!

---

## 🌐 Rodar em máquinas diferentes (rede local ou remota)

Se cada pessoa estiver em um computador diferente, substitua `localhost` pelo IP da outra máquina.

**Máquina A (IP: `192.168.1.10`):**
```bash
python node.py Alice 50051 192.168.1.20 50052
```

**Máquina B (IP: `192.168.1.20`):**
```bash
python node.py Bob 50052 192.168.1.10 50051
```

> Para descobrir seu IP local, use `ipconfig` (Windows) ou `ifconfig` / `ip a` (Linux/Mac).

---

## ⚙️ Entendendo os argumentos

```bash
python node.py <nome> <porta_local> <host_peer> <porta_peer>
```

| Argumento | Descrição | Exemplo |
|---|---|---|
| `nome` | Seu nome exibido no chat | `Alice` |
| `porta_local` | Porta onde **seu** servidor vai escutar | `50051` |
| `host_peer` | Endereço do **outro** nó | `localhost` |
| `porta_peer` | Porta onde o servidor do **outro** nó escuta | `50052` |

As portas `50051` e `50052` são apenas uma convenção — você pode usar qualquer valor entre `1024` e `65535`, desde que as duas pontas estejam de acordo.

---

## ⌨️ Comandos durante o chat

| Comando | Ação |
|---|---|
| `/sair` | Encerra o nó |
| `/quit` | Encerra o nó |
| `/exit` | Encerra o nó |
| `Ctrl+C` | Encerra forçadamente |

---

## 🔧 Solução de problemas

**"Peer ainda não disponível, aguardando..."**
O nó tenta se conectar por até 30 segundos. Certifique-se de que o outro terminal também está rodando.

**"Não foi possível conectar ao peer"**
Verifique se o IP e as portas estão corretos e se não há firewall bloqueando a conexão.

**Erro ao rodar `generate.py`**
Confirme que as dependências foram instaladas corretamente com `pip install -r requirements.txt`.

**Porta já em uso**
Escolha outra porta: `python node.py Alice 50055 localhost 50056`.

---

## 🛠️ Tecnologias utilizadas

- [gRPC](https://grpc.io/) — framework de comunicação remota
- [Protocol Buffers](https://protobuf.dev/) — serialização binária das mensagens
- [Python `threading`](https://docs.python.org/3/library/threading.html) — concorrência para envio e recebimento simultâneos
- [Python `queue`](https://docs.python.org/3/library/queue.html) — comunicação segura entre threads
