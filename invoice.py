# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.model import Model, ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta

__all__ = ['Configuration', 'Invoice', 'MoveLine', 'InvoiceMaturityDate',
    'ModifyMaturitiesStart', 'ModifyMaturities']


class Configuration:
    __name__ = 'account.configuration'
    __metaclass__ = PoolMeta

    maturities_on_customer_post = fields.Boolean('Show Maturities on '
        'Customer Invoices Post')
    maturities_on_supplier_post = fields.Boolean('Show Maturities on '
        'Supplier Invoices Post')


class Invoice:
    __name__ = 'account.invoice'
    __metaclass__ = PoolMeta

    @classmethod
    def __setup__(cls):
        super(Invoice, cls).__setup__()
        post_definition = cls._buttons['post'].copy()
        post_definition['icon'] = 'tryton-ok'
        # We must duplicate the button otherwise the return value is not
        # correctly due to missing returns on inheritance
        cls._buttons.update({
                'modify_maturities': {
                    'invisible': (Eval('state') != 'posted'),
                    'icon': 'tryton-ok',
                    },
                'post_and_modify_maturities': post_definition,
                })
        cls._buttons['post'].update({
                'invisible': True,
                })

    @classmethod
    @ModelView.button_action(
        'account_invoice_maturity_dates.wizard_modify_maturities')
    def modify_maturities(cls, invoices):
        pass

    @classmethod
    @ModelView.button
    def post_and_modify_maturities(cls, invoices):
        pool = Pool()
        Configuration = pool.get('account.configuration')
        config = Configuration(1)
        cls.post(invoices)
        invoice_types = set([i.type for i in invoices])

        if (config.maturities_on_customer_post and 'out' in invoice_types):
            return cls.modify_maturities(invoices)
        if (config.maturities_on_supplier_post and 'in' in invoice_types):
            return cls.modify_maturities(invoices)


class InvoiceMaturityDate(ModelView):
    'Invoice Maturity Date'
    __name__ = 'account.invoice.maturity_date'
    move_line = fields.Many2One('account.move.line', 'Move Line',
        readonly=True)
    date = fields.Date('Date', required=True)
    amount = fields.Numeric('Amount', digits=(16, Eval('currency_digits', 2)),
        depends=['currency_digits'], required=True)
    currency = fields.Many2One('currency.currency', 'Currency', required=True,
        readonly=True)
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'on_change_with_currency_digits')

    @staticmethod
    def default_currency():
        return Transaction().context.get('currency')

    @staticmethod
    def default_amount():
        return Transaction().context.get('amount', Decimal('0.0'))

    @fields.depends('currency')
    def on_change_with_currency_digits(self, name=None):
        if self.currency:
            return self.currency.digits
        return 2


class MoveLine:
    __metaclass__ = PoolMeta
    __name__ = 'account.move.line'

    @classmethod
    def __setup__(cls):
        super(MoveLine, cls).__setup__()
        cls._check_modify_exclude.add('maturity_date')


class ModifyMaturitiesStart(ModelView):
    'Modify Maturities Start'
    __name__ = 'account.invoice.modify_maturities.start'

    invoice_amount = fields.Numeric('Invoice Amount',
        digits=(16, Eval('currency_digits', 2)),
        depends=['currency_digits'], required=True, readonly=True)
    currency = fields.Many2One('currency.currency', 'Currency', required=True,
        readonly=True)
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'on_change_with_currency_digits')
    lines_amount = fields.Function(fields.Numeric('Assigned Amount',
            digits=(16, Eval('currency_digits', 2)),
            depends=['currency_digits']),
        'on_change_with_lines_amount')
    pending_amount = fields.Function(fields.Numeric('Pending Amount',
            digits=(16, Eval('currency_digits', 2)),
            depends=['currency_digits']),
        'on_change_with_pending_amount')
    maturities = fields.One2Many('account.invoice.maturity_date', None,
        'Maturities', context={
            'currency': Eval('currency'),
            'amount': Eval('pending_amount'),
            },
        depends=['currency', 'pending_amount'])

    @fields.depends('currency')
    def on_change_with_currency_digits(self, name=None):
        if self.currency:
            return self.currency.digits
        return 2

    @fields.depends('maturities')
    def on_change_with_lines_amount(self, name=None):
        _ZERO = Decimal('0.0')
        return sum((l.amount or _ZERO for l in self.maturities), _ZERO)

    @fields.depends('invoice_amount', 'maturities')
    def on_change_with_pending_amount(self, name=None):
        lines_amount = self.on_change_with_lines_amount()
        return self.invoice_amount - lines_amount


class ModifyMaturities(Wizard):
    'Modify Maturities'
    __name__ = 'account.invoice.modify_maturities'
    start = StateView('account.invoice.modify_maturities.start',
        'account_invoice_maturity_dates.modify_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'modify', 'tryton-ok', default=True),
            ])
    modify = StateTransition()

    @classmethod
    def __setup__(cls):
        super(ModifyMaturities, cls).__setup__()
        cls._error_messages.update({
                'already_reconciled': ('Can not modify maturities of invoice '
                    '%(invoice)s because its line %(line)s is reconciled'),
                'pending_amount': ('There is still %(amount)s %(currency)s to '
                    'be assigned. Please assignt it to some maturity date'),
                })

    def default_start(self, fields):
        Invoice = Pool().get('account.invoice')
        default = {}
        invoice = Invoice(Transaction().context['active_id'])
        default['currency'] = invoice.currency.id
        default['currency_digits'] = invoice.currency.digits
        default['invoice_amount'] = invoice.total_amount
        lines = []
        for line in invoice.move.lines:
            if line.account == invoice.account:
                if line.reconciliation:
                    self.raise_user_error('already_reconciled', {
                            'invoice': invoice.rec_name,
                            'line': line.rec_name,
                            })
                amount = line.credit - line.debit
                if line.amount_second_currency:
                    amount = line.amount_second_currency
                if invoice.type == 'out':
                    amount = amount.copy_negate()
                lines.append({
                        'id': line.id,
                        'move_line': line.id,
                        'amount': amount,
                        'date': line.maturity_date,
                        'currency': invoice.currency.id
                        })
                default['maturities'] = sorted(lines, key=lambda a: a['date'])
        return default

    def transition_modify(self):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        Move = pool.get('account.move')
        Line = pool.get('account.move.line')
        if self.start.pending_amount:
            self.raise_user_error('pending_amount', {
                    'amount': str(self.start.pending_amount),
                    'currency': self.start.currency.rec_name,
                    })
        to_create, to_write, to_delete = [], [], []
        invoice = Invoice(Transaction().context['active_id'])
        processed = set()
        for maturity in self.start.maturities:
            amount = maturity.amount
            if invoice.type == 'out':
                amount = amount.copy_negate()
            new_line = invoice._get_move_line(maturity.date, amount)
            # With the speedup patch this may return a Line instance
            # XXX: Use instance when patch is commited
            if isinstance(new_line, Line):
                new_line = new_line._save_values
            line = maturity.move_line
            if not line:
                new_line['move'] = invoice.move.id
                to_create.append(new_line)
                continue
            values = {}
            for field, value in new_line.iteritems():
                current_value = getattr(line, field)
                if isinstance(current_value, Model):
                    current_value = current_value.id
                if current_value != value:
                    values[field] = value
            processed.add(line)
            if values:
                to_write.extend(([line], values))
        for line in invoice.move.lines:
            if line.account == invoice.account:
                if line not in processed:
                    to_delete.append(line)
        if to_create:
            Line.create(to_create)
        if to_write:
            Line.write(*to_write)
        if to_delete:
            Line.delete(to_delete)
        Move.post([invoice.move])
        return 'end'
