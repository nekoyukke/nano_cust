from dataclasses import dataclass

from typing import Any

from src.frontend.ast.symbol import *
from src.frontend.ast.abc_class import Type
from src.frontend.ast.type import Function
from src.frontend.ast.abc_class import Symbol

@dataclass
class Context():
    types: dict[str, ClassSymbol]
    val_type: dict[VariableSymbol, Type]
    func_type: dict[FunctionSymbol, Function]
    method_type: dict[MethodSymbol, Function]
    member_type: dict[MemberSymbol, Type]
    args_type: dict[ArgsSymbol, Type]
    entry: FunctionSymbol | None = None

    def __repr__(self) -> str:
        def fmt_sym(s: Symbol) -> str:
            short_id = f"{id(s):x}"[-4:]
            if isinstance(s, VariableSymbol | ClassSymbol | FunctionSymbol | ArgsSymbol):
                return f"'{s.name}'#{short_id} from {s.__class__.__name__}"
            elif isinstance(s, MemberSymbol):
                return f"'{s.val.name}'#{short_id} from {s.__class__.__name__}"
            elif isinstance(s, MethodSymbol):
                return f"'{s.fnc.name}'#{short_id} from {s.__class__.__name__}"
            return ""

        def fmt_dict(d: dict[Any,Any]) -> str:
            if not d:
                return "{}"
            items:list[str] = []
            for k, v in d.items():
                # キーまたは値が Symbol であれば format_symbol を通す
                k_str = fmt_sym(k) if isinstance(k, Symbol) else repr(k)
                v_str = fmt_sym(v) if isinstance(v, Symbol) else repr(v)
                items.append(f"    {k_str}: {v_str}")
            return "{\n" + ",\n".join(items) + "\n}"

        return (
            f"Context(\n"
            f"  types={fmt_dict(self.types)},\n"
            f"  val_type={fmt_dict(self.val_type)},\n"
            f"  func_type={fmt_dict(self.func_type)}\n"
            f"  args_type={fmt_dict(self.args_type)}\n"
            f"  member_type={fmt_dict(self.member_type)}\n"
            f"  method_type={fmt_dict(self.method_type)}\n"
            f")"
        )
