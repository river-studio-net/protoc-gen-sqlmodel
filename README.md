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
