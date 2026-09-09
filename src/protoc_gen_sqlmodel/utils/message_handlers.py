from protobuf import DescMessage
from protobuf.plugin import File, Module

from protoc_gen_sqlmodel.proto.sqlmodel_extensions_pb import ext_table
from protoc_gen_sqlmodel.utils import handle_leaf_enum
from protoc_gen_sqlmodel.utils.field_handlers import (
    handle_leaf_field,
    handle_leaf_oneof,
)

SQLMODEL = Module("sqlmodel").ident("SQLModel")


def handle_message(desc: DescMessage, f: File, root: bool = True):
    class_suffix = "):"
    if opts := desc.proto.options:
        class_suffix = ", table=True):" if ext_table in opts else "):"
    with f.scope(f"class {desc.name}(", SQLMODEL, class_suffix):
        for nm in desc.nested_enums:
            handle_leaf_enum(nm, f)
        for nm in desc.nested_messages:
            handle_message(nm, f, False)
        for field in desc.fields:
            handle_leaf_field(field, f)
        for oneof in desc.oneofs:
            handle_leaf_oneof(oneof, f)
    f.print()
    if root:
        f.print()
