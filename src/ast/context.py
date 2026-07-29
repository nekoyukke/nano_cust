from dataclasses import dataclass

from typing import Any

from src.ast.symbol import ClassSymbol, VariableSymbol, FunctionSymbol
from src.ast.abc_class import Type
from src.ast.type import Function
from src.ast.abc_class import Symbol

@dataclass
class Context():
    types: dict[str, ClassSymbol]
    val_type: dict[VariableSymbol, Type]
    func_type: dict[FunctionSymbol, Function]

    def __repr__(self) -> str:
        def fmt_sym(s: Symbol) -> str:
            short_id = f"{id(s):x}"[-4:]
            return f"'{s.name}'#{short_id} from {s.__class__.__name__}" # TODO: Fix this

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
            f")"
        )