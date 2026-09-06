# nano_cust Language Specification

## Syntax

## Types

### Lists

`list T` is a mutable reference type.  A list value is a handle, so assigning
one list variable to another or passing it to a function does not copy its
contents.  Consequently, mutations through either name are visible through
the other name.

```text
let a: list int;
let b: list int = a;
b.push(1); // a[1] is also 1
```

Lists may be nested.  `list list int` stores handles to `list int` values;
Scratch's native lists are never nested directly.

Indexes are one-based, matching Scratch.  Accessing an index outside
`1..length` is a runtime error in nano_cust (rather than inheriting Scratch's
empty-string result).  Mutating a list during `for` iterates over the length
captured at loop entry.

The Scratch lowering uses one append-only heap per source sprite:

```text
__nc_runtime__.__List_Start__
__nc_runtime__.__List_Length__
__nc_runtime__.__List_Capacity__
__nc_runtime__.__List_Alive__
__nc_runtime__.__List_Data__
```

Handle `0` is null.  Each positive handle indexes the first four metadata
lists.  A full logical list is copied to a larger region at the end of
`Data`; old regions are intentionally left unused.  The lowering must never
use Scratch's insert/delete blocks on `Data`, because those operations would
move all following regions.

## Classes

## Functions

## Objects

## Object Lifetime

## RAII

## Sprites

## Runtime
