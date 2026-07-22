import unittest

from utils.error.error_lists import ErrorLists
from src.parser.parser import Parser
from src.lexer.lexer import Lexer

def parse(string: str):
    return Parser(Lexer(string).tokenize(), string).parse()