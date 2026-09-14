from typing import Any

from more_itertools import collapse, intersperse
from protobuf import (
    DescEnum,
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
from protobuf.plugin import File, Module

from protoc_gen_sqlmodel.proto.sqlmodel_extensions_pb import (
    ext_back_populates,
    ext_cascade_delete,
    ext_default,
    ext_default_factory,
    ext_foreign_key,
    ext_index,
    ext_link_model,
    ext_nullable,
    ext_on_delete,
    ext_passive_deletes,
    ext_pguuid7,
    ext_pguuid7_foreign_key,
    ext_primary_key,
    ext_py_default,
    ext_relationship,
    ext_sa_type,
    ext_server_default,
)
from protoc_gen_sqlmodel.utils import (
    get_presence,
    get_python_scalar_type,
    handle_import_desc,
    handle_python_ref_str,
)

FIELD = Module("sqlmodel").ident("Field")
RELATIONSHIP = Module("sqlmodel").ident("Relationship")

FIELD_EXTENSIONS_BOOL = {
    ext_index: "index",
    ext_primary_key: "primary_key",
    ext_nullable: "nullable",
    ext_cascade_delete: "cascade_delete",
}
FIELD_EXTENSIONS = {
    ext_back_populates: "back_populates",
    ext_passive_deletes: "passive_deletes",
    ext_foreign_key: "foreign_key",
    ext_on_delete: "on_delete",
}

FIELD_EXTENSIONS_PY_REFS = {
    ext_link_model: "link_model",
    ext_py_default: "py_default",
    ext_sa_type: "sa_type",
    ext_default: "default",
    ext_default_factory: "default_factory",
}


def handle_field_extensions(desc: DescField, default_value: Any | None) -> list[Any]:
    extension_components = []

    if opts := desc.proto.options:
        if ext_relationship in opts:
            extension_components.append(RELATIONSHIP)
        else:
            extension_components.append(FIELD)

        extension_components.append("(")

        field_options = []
        if default_value:
            field_options.append(f"default={default_value}")

        if ext_server_default in opts:
            server_default = opts[ext_server_default]
            field_options.append(
                [
                    'sa_column_kwargs={"server_default": ',
                    Module("sqlalchemy").ident("text"),
                    '("',
                    server_default,
                    '")}',
                ]
            )

        if ext_pguuid7 in opts:
            field_options.append(
                [
                    "sa_column=",
                    Module("sqlalchemy").ident("Column"),
                    "(",
                    Module("sqlalchemy.dialects.postgresql").ident("UUID"),
                    "(as_uuid=True), ",
                    "primary_key=True, ",
                    "nullable=False, ",
                    "server_default=",
                    Module("sqlalchemy").ident("text"),
                    '("uuidv7()")',
                    ")",
                ]
            )

        if ext_pguuid7_foreign_key in opts:
            field_options.append(
                [
                    "sa_column=",
                    Module("sqlalchemy").ident("Column"),
                    "(",
                    Module("sqlalchemy.dialects.postgresql").ident("UUID"),
                    "(as_uuid=True), ",
                    "primary_key=True, ",
                    "nullable=False, ",
                    f'foreign_key="{opts[ext_pguuid7_foreign_key]}"',
                    ")",
                ]
            )

        for ext, field_name in FIELD_EXTENSIONS_PY_REFS.items():
            if ext in opts:
                opt = str(opts[ext])
                components = []
                components.extend(
                    [f"{field_name}=", handle_python_ref_str(opt, desc.parent.file)]
                )
                field_options.append(components)

        for ext, field_name in FIELD_EXTENSIONS.items():
            if ext in opts:
                opt = str(opts[ext])
                components = []
                components.append(f'{field_name}="')
                components.append(opt)
                components.append('"')
                field_options.append(components)

        for ext, field_name in FIELD_EXTENSIONS_BOOL.items():
            if ext in opts:
                opt = str(opts[ext])
                components = []
                components.append(f"{field_name}=")
                components.append(opt)
                field_options.append(components)

        extension_components.extend(collapse(intersperse(", ", field_options)))
        extension_components.append(")")

    return extension_components


def handle_leaf_field(desc: DescField, f: File):
    field_name, field_presence = desc.name, get_presence(desc.presence)
    field_preamble = f"{field_name}: "
    print_components = [field_preamble]
    field_default = None

    match desc.value:
        case DescFieldValueScalar(scalar, default_value, _):
            print_components.append(get_python_scalar_type(scalar, desc))
            print_components.append(field_presence)
            if default_value or field_presence:
                field_default = default_value
        case DescFieldValueMessage(message, _, _):
            print_components.extend([handle_import_desc(message), field_presence])
        case DescFieldValueEnum(enum, default_value, _):
            print_components.append(handle_import_desc(enum))
            print_components.append(field_presence)
            if default_value or field_presence:
                field_default = default_value
        case DescFieldValueMap(key, value):
            print_components.append(f"dict[{get_python_scalar_type(key, desc)}, ")
            match value:
                case ScalarType():
                    print_components.append(f"{get_python_scalar_type(value, desc)}]")
                case DescMessage() | DescEnum():
                    print_components.extend([handle_import_desc(value), "]"])
            print_components.append(field_presence)
        case DescFieldValueList(element, _, _):
            print_components.append("list[")
            match element:
                case ScalarType():
                    print_components.append(f"{get_python_scalar_type(element, desc)}]")
                case DescEnum() | DescMessage():
                    print_components.extend(
                        [
                            handle_import_desc(element),
                            "]",
                            field_presence,
                        ]  # is this a bug? shouldn't field_presence be added to the scalar case too?
                    )

    if opts := handle_field_extensions(desc, field_default):
        print_components.append(" = ")
        print_components.extend(opts)

    f.print(*print_components)


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
