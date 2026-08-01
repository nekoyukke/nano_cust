from dataclasses import dataclass
from abc import ABC

from src.backend.ir.value import *

# =========================
# Base
# =========================

@dataclass
class Stmt(ABC):
    pass


@dataclass
class Expr(ABC):
    pass


@dataclass
class BoolExpr(Expr):
    pass