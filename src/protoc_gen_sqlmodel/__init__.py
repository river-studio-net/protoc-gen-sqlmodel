from protobuf.plugin import run

from .plugin import generate


def main():
    run("protoc-gen-sqlmodel", "0.4.1", generate)
