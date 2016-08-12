# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import sys
import re
import unittest
import doctest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase
from trytond.tests.test_tryton import doctest_setup, doctest_teardown
from trytond.tests.test_tryton import Py23DocChecker


class ExceptionChecker(Py23DocChecker):
    def check_output(self, want, got, optionflags):
        if sys.version_info[0] > 2:
            got = re.sub("trytond.exceptions.(.*?)", "\\1", got)
        return super(ExceptionChecker, self).check_output(
            want, got, optionflags)
doctest_checker = ExceptionChecker()


class TestCase(ModuleTestCase):
    'Test module'
    module = 'account_invoice_maturity_dates'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    suite.addTests(doctest.DocFileSuite(
            'scenario_account_invoice_maturity_dates.rst',
            setUp=doctest_setup, tearDown=doctest_teardown, encoding='utf-8',
            checker=doctest_checker,
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
