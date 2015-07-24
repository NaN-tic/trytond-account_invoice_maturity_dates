# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .invoice import *


def register():
    Pool.register(
        Invoice,
        InvoiceMaturityDate,
        ModifyMaturitiesStart,
        module='account_invoice_maturity_dates', type_='model')
    Pool.register(
        ModifyMaturities,
        module='account_invoice_maturity_dates', type_='wizard')
