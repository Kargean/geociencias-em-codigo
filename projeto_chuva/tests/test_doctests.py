"""Roda como testes os exemplos escritos nas docstrings (as linhas que começam com >>>)."""
import doctest
import unittest

from chuva import qualidade, resumo


def load_tests(loader, tests, ignore):
    # O unittest chama esta função especial para saber quais testes adicionar.
    tests.addTests(doctest.DocTestSuite(qualidade))
    tests.addTests(doctest.DocTestSuite(resumo))
    return tests


if __name__ == "__main__":
    unittest.main()
