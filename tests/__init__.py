# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
try:
    from trytond.modules.account_invoice_maturity_dates.tests.test_account_invoice_maturity_dates import suite
except ImportError:
    from .test_account_invoice_maturity_dates import suite

__all__ = ['suite']
