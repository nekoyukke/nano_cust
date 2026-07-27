from dataclasses import dataclass, fields
from abc import ABC

from src.ast.base import ASTNode

@dataclass
class Symbol(ABC):
    def __repr__(self) -> str:
        valid_fields:list[str] = []
        for f in fields(self):
            value = getattr(self, f.name)
            
            # 値が IgnoreTarget のインスタンス（またはそのサブクラス）なら無視！
            if isinstance(value, ASTNode):
                continue
                
            valid_fields.append(f"{f.name}={value!r}")
            
        return f"{self.__class__.__name__}({', '.join(valid_fields)})"

@dataclass
class Type(ABC):
    pass
