"""
node.py — Nó de chat gRPC (servidor + cliente simultâneos)

Cada instância deste script age como um nó simétrico:
  • Sobe um servidor gRPC na porta LOCAL_PORT
  • Conecta-se como cliente ao outro nó em PEER_HOST:PEER_PORT
  • Usa threads para enviar e receber mensagens ao mesmo tempo

Uso:
  # Terminal 1 — Nó A (escuta em 50051, fala com 50052)
  python node.py Alice 50051 localhost 50052

  # Terminal 2 — Nó B (escuta em 50052, fala com 50051)
  python node.py Bob 50052 localhost 50051
"""

import sys
import threading
import time
import queue
from concurrent import futures

import grpc

# Módulos gerados pelo protoc a partir de chat.proto
import chat_pb2
import chat_pb2_grpc

# ---------------------------------------------------------------------------
# 1. IMPLEMENTAÇÃO DO SERVIÇO gRPC (lado servidor)
# ---------------------------------------------------------------------------

class ChatServicer(chat_pb2_grpc.ChatServiceServicer):
    """
    Implementa o método Chat definido no .proto.
    É instanciado pelo servidor gRPC e chamado quando o nó remoto abre um stream.
    """

    def __init__(self, node_name: str, incoming_queue: queue.Queue):
        self.node_name = node_name
        # Fila compartilhada onde as mensagens recebidas serão depositadas
        self.incoming = incoming_queue

    def Chat(self, request_iterator, context):
        """
        RPC bidirecional — este método roda em uma thread gerenciada pelo gRPC.

        request_iterator : iterador das mensagens que chegam do peer
        context          : metadados e controle do stream

        Como o gRPC bidirecional em Python funciona na prática:
          • O loop for consome o request_iterator (mensagens recebidas).
          • Para enviar de volta ao peer a partir desta mesma conexão seria
            necessário yield dentro deste gerador — mas aqui adotamos a
            arquitetura simétrica: cada nó abre seu próprio stream de saída
            (ver seção CLIENTE abaixo), então este lado só recebe.
          • Mensagens recebidas são empurradas para a incoming_queue e
            impressas pela thread de recepção.
        """
        for msg in request_iterator:
            # Deposita a mensagem na fila para ser exibida
            self.incoming.put(msg)
            # yield vazio para manter o stream bidirecional aberto
            # (o peer não espera resposta aqui; ele lê seu próprio stream de saída)
        # Quando o peer fechar o stream, o for termina — nada a fazer.
        return iter([])   # retorna stream vazio (sem mensagens de volta por este canal)


# ---------------------------------------------------------------------------
# 2. THREAD DO SERVIDOR
# ---------------------------------------------------------------------------

def run_server(node_name: str, local_port: int, incoming_queue: queue.Queue):
    """
    Sobe o servidor gRPC em background.
    ThreadPoolExecutor(10) suporta até 10 conexões simultâneas.
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(
        ChatServicer(node_name, incoming_queue), server
    )
    server.add_insecure_port(f"[::]:{local_port}")
    server.start()
    print(f"[{node_name}] Servidor gRPC ouvindo na porta {local_port}...")
    server.wait_for_termination()


# ---------------------------------------------------------------------------
# 3. GERADOR DE MENSAGENS DE SAÍDA (lado cliente)
# ---------------------------------------------------------------------------

def outgoing_message_generator(outgoing_queue: queue.Queue, node_name: str):
    """
    Gerador que alimenta o stream de saída do cliente gRPC.
    Fica bloqueado em outgoing_queue.get() até haver uma mensagem para enviar.
    Quando recebe o sentinel None, encerra o stream.
    """
    while True:
        text = outgoing_queue.get()   # bloqueia até o usuário digitar algo
        if text is None:              # sentinel de encerramento
            break
        yield chat_pb2.ChatMessage(sender=node_name, text=text)


# ---------------------------------------------------------------------------
# 4. THREAD DO CLIENTE (conecta ao peer e abre o stream de saída)
# ---------------------------------------------------------------------------

def run_client(node_name: str, peer_host: str, peer_port: int,
               outgoing_queue: queue.Queue):
    """
    Tenta conectar ao servidor do peer em loop (o peer pode demorar a subir).
    Uma vez conectado, abre o stream bidirecional e fica enviando mensagens
    da outgoing_queue.
    """
    target = f"{peer_host}:{peer_port}"
    print(f"[{node_name}] Tentando conectar ao peer em {target}...")

    channel = grpc.insecure_channel(target)
    stub = chat_pb2_grpc.ChatServiceStub(channel)

    # Espera o peer subir (tenta por até 30 s)
    connected = False
    for _ in range(30):
        try:
            grpc.channel_ready_future(channel).result(timeout=1)
            connected = True
            break
        except grpc.FutureTimeoutError:
            print(f"[{node_name}] Peer ainda não disponível, aguardando...")
            time.sleep(1)

    if not connected:
        print(f"[{node_name}] Não foi possível conectar ao peer. Encerrando.")
        sys.exit(1)

    print(f"[{node_name}] Conectado ao peer {target}. Pode começar a digitar!\n")

    # Abre o stream bidirecional passando o gerador como fonte de mensagens
    # O gRPC irá iterar o gerador em background e enviar cada item pelo canal
    response_stream = stub.Chat(
        outgoing_message_generator(outgoing_queue, node_name)
    )

    # Consome a stream de resposta (no nosso design simétrico, o peer não
    # envia respostas por este canal — mas precisamos iterar para manter
    # o stream aberto e detectar erros de conexão)
    try:
        for _ in response_stream:
            pass
    except grpc.RpcError as e:
        print(f"[{node_name}] Stream encerrado: {e.code()}")


# ---------------------------------------------------------------------------
# 5. THREAD DE RECEPÇÃO — exibe mensagens da incoming_queue
# ---------------------------------------------------------------------------

def receive_loop(node_name: str, incoming_queue: queue.Queue):
    """
    Fica em loop exibindo mensagens que chegam via fila.
    Roda em thread separada para não bloquear a leitura do teclado.
    """
    while True:
        msg = incoming_queue.get()
        if msg is None:
            break
        # \r limpa a linha atual (onde o usuário está digitando) antes de
        # imprimir, para não misturar o input com a mensagem recebida
        print(f"\r[{msg.sender}]: {msg.text}")
        print(f"[{node_name}] >> ", end="", flush=True)


# ---------------------------------------------------------------------------
# 6. MAIN — orquestra tudo
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 5:
        print("Uso: python node.py <nome> <porta_local> <host_peer> <porta_peer>")
        sys.exit(1)

    node_name  = sys.argv[1]
    local_port = int(sys.argv[2])
    peer_host  = sys.argv[3]
    peer_port  = int(sys.argv[4])

    incoming_queue = queue.Queue()   # mensagens recebidas → tela
    outgoing_queue = queue.Queue()   # mensagens do teclado → peer

    # --- Thread 1: servidor gRPC (recebe conexões do peer) ---
    t_server = threading.Thread(
        target=run_server,
        args=(node_name, local_port, incoming_queue),
        daemon=True   # encerra junto com o processo principal
    )
    t_server.start()

    # Pequena pausa para o servidor subir antes de o cliente conectar
    time.sleep(0.5)

    # --- Thread 2: cliente gRPC (conecta ao peer e envia mensagens) ---
    t_client = threading.Thread(
        target=run_client,
        args=(node_name, peer_host, peer_port, outgoing_queue),
        daemon=True
    )
    t_client.start()

    # --- Thread 3: exibe mensagens recebidas ---
    t_recv = threading.Thread(
        target=receive_loop,
        args=(node_name, incoming_queue),
        daemon=True
    )
    t_recv.start()

    # --- Loop principal: lê input do usuário e enfileira para envio ---
    try:
        while True:
            print(f"[{node_name}] >> ", end="", flush=True)
            text = input()
            if text.lower() in ("/quit", "/sair", "/exit"):
                break
            if text.strip():
                outgoing_queue.put(text)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        print(f"\n[{node_name}] Encerrando...")
        outgoing_queue.put(None)   # sinaliza fim do stream de saída
        incoming_queue.put(None)   # sinaliza fim da thread de recepção


if __name__ == "__main__":
    main()