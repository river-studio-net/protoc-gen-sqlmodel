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
    ext_on_delete,
    ext_passive_deletes,
    ext_pg_uuid7,
    ext_primary_key,
    ext_py_default,
    ext_relationship,
    ext_sa_type,
    ext_server_default,
    ext_sqlmodel_default,
    ext_sqlmodel_default_factory,
    ext_table,
)
from protoc_gen_sqlmodel.utils import (
    get_presence,
    get_python_scalar_type,
    handle_import_desc,
)

FIELD = Module("sqlmodel").ident("Field")


def handle_field_extensions(desc: DescField):
    extension_components = []
    if opts := desc.proto.options:
        if ext_sa_type in opts:
            extension_components.append(
                f"sa_column={handle_import_str(opts[ext_sa_type])}",
            )


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
            print_components.extend([handle_import_desc(message), field_presence])
        case DescFieldValueEnum(enum, default_value, _):
            print_components.append(handle_import_desc(enum))
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
