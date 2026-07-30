from __future__ import annotations

from dataclasses import dataclass, field

from frontend.ast.abc_class import Symbol
from frontend.ast.symbol import *

@dataclass
class Scope():
    sym: dict[str, Symbol] = field(default_factory=dict[str, Symbol])
    parent: Scope | None = None

    def push(self):
        return Scope(parent=self)

    def deep(self) -> int:
        if self.parent: return self.parent.deep() + 1
        return 0

    def pop(self):
        if self.parent: return self.parent
        return self
    
    def lookup(self, name: str) -> Symbol | None:
        if name in self.sym:
            return self.sym[name]
        if self.parent: return self.parent.lookup(name)
        return None

    def get_global(self) -> Scope:
        if self.parent: return self.parent.get_global()
        return self

    def __repr__(self) -> str:
        # ID（メモリ番地）の下4桁（16進数）を文字列化するヘルパー関数
        def format_symbol(s: Symbol) -> str:
            short_id = f"{id(s):x}"[-4:]  # 下4桁を取得（6桁にするなら -6:）
            if isinstance(s, VariableSymbol | ClassSymbol | FunctionSymbol | ArgsSymbol):
                return f"'{s.name}'#{short_id} from {s.__class__.__name__}"
            elif isinstance(s, MemberSymbol):
                return f"'{s.val.name}'#{short_id} from {s.__class__.__name__}"
            elif isinstance(s, MethodSymbol):
                return f"'{s.fnc.name}'#{short_id} from {s.__class__.__name__}"
            return ""


        # sym 辞書内の Symbol を改行 ＋ インデント付きで整形
        if not self.sym:
            sym_str = "{}"
        else:
            sym_items = [
                f"    {k!r}: {format_symbol(v)}" 
                for k, v in self.sym.items()
            ]
            sym_str = "{\n" + ",\n".join(sym_items) + "\n}"

        parent_str = repr(self.parent) if self.parent else "None"
        return f"Scope(sym={sym_str}, parent={parent_str})"