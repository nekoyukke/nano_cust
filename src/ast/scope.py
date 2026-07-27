from __future__ import annotations

from dataclasses import dataclass, field, fields

from src.ast.abc_class import Symbol

@dataclass
class Scope():
    sym: dict[str, Symbol] = field(default_factory=dict[str, Symbol])
    parent: Scope|None=None

    def push(self):
        return Scope(parent=self)

    def deep(self) -> int:
        if self.parent:return self.parent.deep()+1
        return 0

    def pop(self):
        if self.parent:return self.parent
        return self
    
    def lookup(self, name:str) -> Symbol|None:
        if name in self.sym:
            return self.sym[name]
        if self.parent: return self.parent.lookup(name)
        return None

    def get_global(self) -> Scope:
        if self.parent:return self.parent
        return self
    
    def __repr__(self) -> str:
        valid_fields: list[str] = []
        
        for f in fields(self):
            value = getattr(self, f.name)
            
            # 2. 辞書型（sym: dict[str, Symbol] など）の整形処理
            if isinstance(value, dict):
                if not value:
                    formatted_val = "{}"
                else:
                    # 要素ごとに改行 ＋ インデント（スペース4個）を入れる
                    items_str = ",\n    ".join(
                        f"{k!r}: {v!r}" for k, v in value.items()
                    )
                    formatted_val = f"{{\n    {items_str}\n}}"
            else:
                formatted_val = repr(value)
                
            valid_fields.append(f"{f.name}={formatted_val}")
            
        return f"{self.__class__.__name__}({', '.join(valid_fields)})"