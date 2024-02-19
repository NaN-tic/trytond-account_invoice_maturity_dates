# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import ModelView
from trytond.pool import Pool, PoolMeta


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        post_definition = cls._buttons['post'].copy()
        post_definition['icon'] = 'tryton-ok'
        # We must duplicate the button otherwise the return value is not
        # correctly due to missing returns on inheritance
        cls._buttons.update({
                'post_and_modify_maturities': post_definition,
                })
        cls._buttons['post'].update({
                'invisible': True,
                })
        cls._check_modify_exclude |= {'invoice_report_cache_id'}

    @classmethod
    @ModelView.button
    def post_and_modify_maturities(cls, invoices):
        Configuration = Pool().get('account.configuration')

        config = Configuration(1)
        cls.post(invoices)
        invoice_types = set([i.type for i in invoices])

        if ((config.maturities_on_customer_post and 'out' in invoice_types)
                or (config.maturities_on_supplier_post
                    and 'in' in invoice_types)):
            return cls.reschedule_lines_to_pay(invoices)


class RescheduleLinesToPay(metaclass=PoolMeta):
    "Reschedule Lines to Pay"
    __name__ = 'account.invoice.lines_to_pay.reschedule'

    def do_start(self, action):
        Config = Pool().get('account.configuration')

        config = Config(1)
        if self.record and config.maturities_invoice_report:
            self.record.invoice_report_format = None
            self.record.invoice_report_cache_id = None
            self.record.invoice_report_cache = None
            self.record.save()
        return super().do_start(action)
