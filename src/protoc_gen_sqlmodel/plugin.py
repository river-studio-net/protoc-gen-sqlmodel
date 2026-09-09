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

from logging import getLogger

from protobuf import (
    DescEnum,
    DescExtension,
    DescField,
    DescFieldValueEnum,
    DescFieldValueList,
    DescFieldValueMap,
    DescFieldValueMessage,
    DescFieldValueScalar,
    DescMessage,
    DescOneof,
    ScalarType,
)
from protobuf._descriptors import SupportedFieldPresence
from protobuf.plugin import File, Module, Schema

ENUM = Module("enum").ident("Enum")
FIELD = Module("sqlmodel").ident("Field")
SQLMODEL = Module("sqlmodel").ident("SQLModel")
ANY = Module("typing").ident("Any")
FINAL = Module("typing").ident("Final")
EXTENSION = Module("protobuf").ident("Extension")
FIELD_OPT = Module("protobuf.wkt").ident("FieldOptions")
MESSAGE_OPT = Module("protobuf.wkt").ident("MessageOptions")


logger = getLogger()


def get_presence(presence: SupportedFieldPresence) -> str:
    match presence:
        case SupportedFieldPresence.EXPLICIT:
            return " | None "
        case SupportedFieldPresence.IMPLICIT:
            return ""
        case _:
            return ""


def get_python_scalar_type(scalar: ScalarType):
    match scalar:
        case ScalarType.BOOL:
            return "bool"
        case ScalarType.BYTES:
            return "bytes"
        case (
            ScalarType.DOUBLE
            | ScalarType.FIXED32
            | ScalarType.FIXED64
            | ScalarType.FLOAT
            | ScalarType.SFIXED32
            | ScalarType.SFIXED64
        ):
            return "float"
        case (
            ScalarType.INT32
            | ScalarType.INT64
            | ScalarType.UINT32
            | ScalarType.UINT64
            | ScalarType.SINT32
            | ScalarType.SINT64
        ):
            return "int"
        case ScalarType.STRING:
            return "str"


def handle_leaf_enum(desc: DescEnum, f: File):
    with f.scope(f"class {desc.name}(", ENUM, ", int):"):
        for v in desc.values:
            f.print(f"{v.local_name} = {v.number}")
    f.print()


def handle_leaf_oneof(desc: DescOneof, f: File):
    f.print(f"# oneof {desc.local_name}")
    distinguisher = f"which_{desc.local_name}: "
    f.print(
        distinguisher,
        Module("typing").ident("Literal"),
        "['",
        "', '".join([field.local_name for field in desc.fields]),
        "']",
    )
    for field in desc.fields:
        handle_leaf_field(field, f)
    f.print()


def handle_import(element: DescEnum | DescMessage):
    if element.file.proto.package == "google.protobuf":  # well known types
        match element.name:
            case "Timestamp":
                return Module("datetime").ident("datetime")
            case "Any":
                return Module("typing").ident("Any")
    return Module.for_desc(element.file, "_sqlmodel").ident(element.name)


def handle_leaf_field(desc: DescField, f: File):
    field_name, field_presence = desc.name, get_presence(desc.presence)
    field_preamble, field_presence_preamble = f"{field_name}: ", f"{field_presence}= "
    print_components = [field_preamble]

    match desc.value:
        case DescFieldValueScalar(scalar, default_value, _):
            print_components.append(get_python_scalar_type(scalar))
            if default_value:
                print_components.extend(
                    [field_presence_preamble, FIELD, f"(default={default_value})"]
                )
            else:
                print_components.append(field_presence)
        case DescFieldValueMessage(message, _, _):
            print_components.extend([handle_import(message), field_presence])
        case DescFieldValueEnum(enum, default_value, _):
            print_components.append(handle_import(enum))
            if default_value is not None:  # can be 0
                print_components.extend(
                    [field_presence_preamble, FIELD, f"(default={default_value})"]
                )
            else:
                print_components.append(field_presence)
        case DescFieldValueMap(key, value):
            print_components.append(f"dict[{get_python_scalar_type(key)}, ")
            match value:
                case ScalarType():
                    print_components.append(f"{get_python_scalar_type(value)}]")
                case DescMessage() | DescEnum():
                    print_components.extend([handle_import(value), "]"])
            print_components.append(field_presence)
        case DescFieldValueList(element, _, _):
            print_components.append("list[")
            match element:
                case ScalarType():
                    print_components.append(f"{get_python_scalar_type(element)}]")
                case DescEnum() | DescMessage():
                    print_components.extend(
                        [
                            handle_import(element),
                            "]",
                            field_presence,
                        ]  # is this a bug? shouldn't field_presence be added to the scalar case too?
                    )
    # if opts := desc.proto.options:
    #     from .sqlmodel_extensions_pb import ext_sqlmodel_type

    # if ext_sqlmodel_type in opts:
    #     print_components.extend(
    #         [
    #             field_presence_preamble,
    #             FIELD,
    #             f"(sa_column={handle_import(opts[ext_sqlmodel_type])})",
    #         ]
    #     )
    f.print(*print_components)


def handle_message(desc: DescMessage, f: File, root: bool = True):
    class_suffix = "):"
    if opts := desc.proto.options:
        from .proto.sqlmodel_extensions_pb import ext_table

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


def handle_extension(desc: DescExtension, f: File):
    match desc.extendee.type_name:
        case "google.protobuf.MessageOptions":
            ext = MESSAGE_OPT
        case "google.protobuf.FieldOptions":
            ext = FIELD_OPT
    match desc.value:
        case DescFieldValueScalar(scalar, _, _):
            ext_type = get_python_scalar_type(scalar)

    f.print(
        f"ext_{desc.name}: ",
        FINAL,
        "[",
        EXTENSION,
        "[",
        ext,
        ", ",
        ext_type,
        "]] = ",
        EXTENSION,
        "()",
    )


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
