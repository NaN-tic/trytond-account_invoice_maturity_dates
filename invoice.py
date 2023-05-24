# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.model import Model, ModelView, fields
from trytond.pyson import Eval
from trytond.pool import Pool, PoolMeta


class Configuration(metaclass=PoolMeta):
    __name__ = 'account.configuration'

    maturities_on_customer_post = fields.Boolean('Show Maturities on '
        'Customer Invoices Post')
    maturities_on_supplier_post = fields.Boolean('Show Maturities on '
        'Supplier Invoices Post')


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
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

    @classmethod
    @ModelView.button
    def post_and_modify_maturities(cls, invoices):
        Configuration = Pool().get('account.configuration')

        config = Configuration(1)
        cls.post(invoices)
        invoice_types = set([i.type for i in invoices])

        if (config.maturities_on_customer_post and 'out' in invoice_types):
            return cls.reschedule_lines_to_pay(invoices)
        if (config.maturities_on_supplier_post and 'in' in invoice_types):
            return cls.reschedule_lines_to_pay(invoices)

    def set_maturities(self, maturity_dates):
        pool = Pool()
        Move = pool.get('account.move')
        Line = pool.get('account.move.line')

        if not self.move:
            return

        to_create, to_write, to_delete = [], [], []

        Move.draft([self.move])

        processed = set()
        for maturity in maturity_dates:
            amount = maturity.amount
            if self.type == 'out':
                amount = amount.copy_negate()
            new_line = self._get_move_line(maturity.date, amount)
            # With the speedup patch this may return a Line instance
            # XXX: Use instance when patch is commited
            if isinstance(new_line, Line):
                new_line = new_line._save_values
            line = maturity.move_line
            if not line:
                new_line['move'] = self.move.id
                to_create.append(new_line)
                continue
            values = {}
            for field, value in new_line.items():
                current_value = getattr(line, field)
                if isinstance(current_value, Model):
                    current_value = current_value.id
                if current_value != value:
                    values[field] = value
            processed.add(line)
            if values:
                quantize = Decimal(10) ** -Decimal(maturity.currency.digits)
                if 'credit' in values:
                    values['credit'] = Decimal(values.get('credit')).quantize(
                            quantize)
                if 'debit' in values:
                    values['debit'] = Decimal(values.get('debit')).quantize(
                            quantize)
                to_write.extend(([line], values))

        for line in self.move.lines:
            if line.account == self.account:
                if line not in processed:
                    to_delete.append(line)

        if to_create:
            Line.create(to_create)
        if to_write:
            Line.write(*to_write)
        if to_delete:
            Line.delete(to_delete)

        Move.post([self.move])
