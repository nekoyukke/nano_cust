from __future__ import annotations

from dataclasses import dataclass, field

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