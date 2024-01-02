# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import invoice, move


def register():
    Pool.register(
        invoice.Configuration,
        invoice.Invoice,
        move.RescheduleLinesStart,
        move.RescheduleLinesTerm,
        module='account_invoice_maturity_dates', type_='model')
    Pool.register(
        move.RescheduleLines,
        invoice.RescheduleLinesToPay,
        module='account_invoice_maturity_dates', type_='wizard')
