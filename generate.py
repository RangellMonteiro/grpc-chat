"""
generate.py — Gera os arquivos Python a partir do chat.proto

Uso:
  python generate.py
"""

from grpc_tools import protoc

protoc.main([
    "grpc_tools.protoc",
    "-I.",                    # diretório onde está o .proto
    "--python_out=.",         # gera chat_pb2.py
    "--grpc_python_out=.",    # gera chat_pb2_grpc.py
    "chat.proto"
])

print("Arquivos gerados: chat_pb2.py e chat_pb2_grpc.py")