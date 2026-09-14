from typing import Any

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
    ext_foreign_key,
    ext_index,
    ext_link_model,
    ext_nullable,
    ext_on_delete,
    ext_passive_deletes,
    ext_primary_key,
    ext_py_default,
    ext_relationship,
    ext_sa_type,
    ext_server_default,
    ext_sqlmodel_default,
    ext_sqlmodel_default_factory,
)
from protoc_gen_sqlmodel.utils import (
    get_presence,
    get_python_scalar_type,
    handle_import_desc,
    handle_python_ref_str,
)

FIELD = Module("sqlmodel").ident("Field")
RELATIONSHIP = Module("sqlmodel").ident("Relationship")

FIELD_EXTENSIONS = {
    ext_back_populates: "back_populates",
    ext_cascade_delete: "cascade_delete",
    ext_foreign_key: "foreign_key",
    ext_index: "index",
    ext_link_model: "link_model",
    ext_on_delete: "on_delete",
    ext_passive_deletes: "passive_deletes",
    ext_primary_key: "primary_key",
    ext_py_default: "py_default",
    ext_sa_type: "sa_type",
    ext_sqlmodel_default: "sqlmodel_default",
    ext_sqlmodel_default_factory: "sqlmodel_default_factory",
    ext_nullable: "nullable",
}


def handle_field_extensions(desc: DescField, default_value: Any | None):
    extension_components = []
    options = False

    if opts := desc.proto.options:
        if ext_relationship in opts:
            extension_components.append(RELATIONSHIP)
        else:
            extension_components.append(FIELD)

        extension_components.append("(")

        field_options = []
        if default_value:
            field_options.append(f"default={default_value}")
            options = True

        if ext_server_default in opts:
            server_default = opts[ext_server_default]
            field_options.append('sa_column_kwargs={"server_default": text("')
            field_options.append(server_default)
            field_options.append('")}, ')

        for ext, field_name in FIELD_EXTENSIONS.items():
            if ext in opts:
                field_options.append(f"{field_name}=")
                field_options.append(handle_python_ref_str(str(opts[ext])))
                field_options.append(", ")
                options = True
        extension_components.extend(field_options)
    extension_components.append(")")

    if options:
        return extension_components
    return []


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
            print_components.append(f"dict[{get_python_scalar_type(key)}, ")
            match value:
                case ScalarType():
                    print_components.append(f"{get_python_scalar_type(value)}]")
                case DescMessage() | DescEnum():
                    print_components.extend([handle_import_desc(value), "]"])
            print_components.append(field_presence)
        case DescFieldValueList(element, _, _):
            print_components.append("list[")
            match element:
                case ScalarType():
                    print_components.append(f"{get_python_scalar_type(element)}]")
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
