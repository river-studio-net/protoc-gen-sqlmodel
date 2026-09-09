from protobuf import (
    DescEnum,
    DescExtension,
    DescFieldValueScalar,
    DescMessage,
    ScalarType,
)
from protobuf._descriptors import SupportedFieldPresence
from protobuf.plugin import File, Module

ENUM = Module("enum").ident("Enum")
FINAL = Module("typing").ident("Final")
EXTENSION = Module("protobuf").ident("Extension")
FIELD_OPT = Module("protobuf.wkt").ident("FieldOptions")
MESSAGE_OPT = Module("protobuf.wkt").ident("MessageOptions")


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


def handle_import_desc(element: DescEnum | DescMessage):
    if element.file.proto.package == "google.protobuf":  # well known types
        match element.name:
            case "Timestamp":
                return Module("datetime").ident("datetime")
            case "Any":
                return Module("typing").ident("Any")
            # TODO - complete types registery
    return Module.for_desc(element.file, "_sqlmodel").ident(element.name)


def handle_import_str(type_name: str): ...


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
