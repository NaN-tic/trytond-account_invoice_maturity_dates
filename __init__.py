# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import configuration
from . import invoice
from . import move


def register():
    Pool.register(
        configuration.Configuration,
        configuration.ConfigurationConformity,
        invoice.Invoice,
        move.RescheduleLinesStart,
        move.RescheduleLinesTerm,
        module='account_invoice_maturity_dates', type_='model')
    Pool.register(
        move.RescheduleLines,
        invoice.RescheduleLinesToPay,
        module='account_invoice_maturity_dates', type_='wizard')
