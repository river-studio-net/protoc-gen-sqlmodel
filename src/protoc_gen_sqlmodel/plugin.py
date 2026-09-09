#!/usr/bin/env python3
"""
This plugin parses protobuf files into SQLModel classes.
The plugin system exposes the following structure, used as a base for functional parsing:

Schema
└── DescFile
    ├── extensions 	Sequence[DescExtension]
    ├── dependencies 	Sequence[DescFile]
    ├── enums 	Sequence[DescEnum]
    │   └── values 	Sequence[DescEnumValue]
    ├── messages 	Sequence[DescMessage]
    │   ├── fields 	Sequence[DescField]
    │   ├── nested_enums 	Sequence[DescEnum]
    │   ├── nested_messages 	Sequence[DescMessage]
    │   └── oneofs 	Sequence[DescOneof]
    └── Sequence[DescService]
        └── ...

Services are skipped at the moment.
"""

from protobuf.plugin import Schema

from protoc_gen_sqlmodel.utils import handle_extension, handle_leaf_enum
from protoc_gen_sqlmodel.utils.message_handlers import handle_message


def generate(schema: Schema) -> None:
    for desc in schema.files_to_generate:
        f = schema.generate_file(desc, "_sqlmodel.py")
        f.preamble(desc)
        for ext in desc.extensions:
            handle_extension(ext, f)
        for e in desc.enums:
            handle_leaf_enum(e, f)
        for m in desc.messages:
            handle_message(m, f)
