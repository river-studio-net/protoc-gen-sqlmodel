# protoc-gen-sqlmodel
A protoc plugin for producing sqlmodel classes.
Meant to manage multi-language projects with a single source of truth called protobuf.
Generate SQLModel from your schema and manage your DB with alembic.

# Install 
Add to your project:
```shell
uv add protoc-gen-sqlmodel
```

Then configure like a regular `buf` plugin in a `bug.gen.yaml` file:
```yml
version: v2
inputs:
  - directory: proto
plugins:
  - local: protoc-gen-sqlmodel
    out: gen
```

# Usage
Run with `protoc` or (preferred) with `uv run buf-generate`.

## Features
To mark a model as a table, include the following extension in your proto files:
```proto
syntax = "proto3";

package example.sqlmodel;

import "google/protobuf/descriptor.proto";

// Marks a protobuf message as a SQLModel table.
extend google.protobuf.MessageOptions {
  bool table = 50001;
}
```

And mark the message schema as:
```proto
syntax = "proto3";

package example.models;

import "sqlmodel_extensions.proto";

message Entity {
  option (example.sqlmodel.table) = true;
}
```

The generated SQLModel will be marked as a table and you can use it directly with alembic for DB management. 

To express field options add the following proto extensions to you fields:
```proto
syntax = "proto3";

package example.sqlmodel;

import "google/protobuf/descriptor.proto";

extend google.protobuf.FieldOptions {
  string sa_type = 50002;
  bool primary_key = 50003;
  string sqlmodel_default = 50004;
  string sqlmodel_default_factory = 50005;
  string py_default = 50006;
  bool index = 50007;
  string foreign_key = 50008;
  bool relationship = 50009;
  string back_populates = 50010;
  bool cascade_delete = 50011;
  string on_delete = 50012;
  string passive_deletes = 50013;
  string link_model = 50014;
  string server_default = 50015;
}
```

Then express fields like:
```proto
map<string, string> import_metadata = 7 [
  (example.sqlmodel.sa_type) = "sqlmodel.JSON"
];
```
