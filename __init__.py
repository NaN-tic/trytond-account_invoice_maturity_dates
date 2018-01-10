# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import invoice


def register():
    Pool.register(
        invoice.Configuration,
        invoice.Invoice,
        invoice.InvoiceMaturityDate,
        invoice.ModifyMaturitiesStart,
        module='account_invoice_maturity_dates', type_='model')
    Pool.register(
        invoice.ModifyMaturities,
        module='account_invoice_maturity_dates', type_='wizard')
