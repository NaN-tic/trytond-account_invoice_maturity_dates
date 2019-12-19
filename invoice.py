# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
from trytond.model import Model, ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pyson import Bool, Eval
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.i18n import gettext
from trytond.exceptions import UserError

__all__ = ['Configuration', 'Invoice', 'InvoiceMaturityDate',
    'ModifyMaturitiesStart', 'ModifyMaturities']
ZERO = Decimal('0.0')


class Configuration(metaclass=PoolMeta):
    __name__ = 'account.configuration'

    maturities_on_customer_post = fields.Boolean('Show Maturities on '
        'Customer Invoices Post')
    maturities_on_supplier_post = fields.Boolean('Show Maturities on '
        'Supplier Invoices Post')
    remove_invoice_report_cache = fields.Boolean('Remove Invoice Report Cache')


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
        Configuration = Pool().get('account.configuration')

        config = Configuration(1)
        cls.post(invoices)
        invoice_types = set([i.type for i in invoices])

        if (config.maturities_on_customer_post and 'out' in invoice_types):
            return cls.modify_maturities(invoices)
        if (config.maturities_on_supplier_post and 'in' in invoice_types):
            return cls.modify_maturities(invoices)

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
                quantize = Decimal(10) ** -Decimal(maturity.currency_digits)
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


class InvoiceMaturityDate(ModelView):
    'Invoice Maturity Date'
    __name__ = 'account.invoice.maturity_date'
    invoice = fields.Many2One('account.invoice', 'Invoice',
        readonly=True)
    move_line = fields.Many2One('account.move.line', 'Move Line',
        readonly=True)
    date = fields.Date('Date', required=True)
    amount = fields.Numeric('Amount', digits=(16, Eval('currency_digits', 2)),
        depends=['currency_digits'], required=True)
    amount_second_currency = fields.Numeric('Amount Second Currency',
        digits=(16, Eval('second_currency_digits', 2)), states={
            'invisible': ~Bool(Eval('second_currency', None)),
        }, depends=['second_currency_digits', 'second_currency'])
    currency = fields.Many2One('currency.currency', 'Currency', required=True,
        readonly=True)
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'on_change_with_currency_digits')
    second_currency = fields.Many2One('currency.currency', 'Second Currency',
        readonly=True, states={
            # 'required': Bool(Eval('amount_second_currency')),
            'invisible': ~Bool(Eval('second_currency', None)),
            },
        depends=['amount_second_currency', 'second_currency'])
    second_currency_digits = fields.Function(fields.Integer(
            'Second Currency Digits', states={
                'invisible': ~Bool(Eval('second_currency', None)),
            }, depends=['second_currency']),
        'on_change_with_second_currency_digits')

    @staticmethod
    def default_invoice():
        return Transaction().context.get('invoice')

    @staticmethod
    def default_currency():
        return Transaction().context.get('currency')

    @staticmethod
    def default_second_currency():
        return Transaction().context.get('second_currency', None)

    @staticmethod
    def default_amount():
        return Transaction().context.get('amount', Decimal('0.0'))

    @staticmethod
    def default_amount_second_currency():
        return Transaction().context.get('amount_second_currency',
            Decimal('0.0'))

    @fields.depends('currency')
    def on_change_with_currency_digits(self, name=None):
        if self.currency:
            return self.currency.digits
        return 2

    @fields.depends('second_currency')
    def on_change_with_second_currency_digits(self, name=None):
        if self.second_currency:
            return self.second_currency.digits
        return 2

    @fields.depends('invoice', 'amount', 'amount_second_currency', 'currency',
        'second_currency')
    def on_change_amount(self):
        Currency = Pool().get('currency.currency')

        if self.amount and self.second_currency:
            with Transaction().set_context(date=self.invoice.currency_date):
                quantize = Decimal(10) ** -Decimal(self.second_currency_digits)
                self.amount_second_currency = Decimal(abs(Currency.compute(
                        self.currency, self.amount, self.second_currency))).\
                            quantize(quantize)

    @fields.depends('invoice', 'amount', 'amount_second_currency', 'currency',
        'second_currency')
    def on_change_amount_second_currency(self):
        Currency = Pool().get('currency.currency')

        if self.amount_second_currency and self.second_currency:
            with Transaction().set_context(date=self.invoice.currency_date):
                quantize = Decimal(10) ** -Decimal(self.currency_digits)
                self.amount = Decimal(abs(Currency.compute(
                    self.second_currency, self.amount_second_currency,
                    self.currency))).quantize(quantize)


class ModifyMaturitiesStart(ModelView):
    'Modify Maturities Start'
    __name__ = 'account.invoice.modify_maturities.start'
    invoices = fields.Many2Many(
        'account.invoice', None, None, 'Invoices', readonly=True)
    invoice = fields.Many2One('account.invoice', 'Invoice', readonly=True)
    invoice_amount = fields.Numeric('Invoice Amount',
        digits=(16, Eval('currency_digits', 2)),
        depends=['currency_digits'], required=True, readonly=True)
    invoice_amount_second_currency = fields.Numeric(
        'Invoice Amount Second Currency',
        digits=(16, Eval('second_currency_digits', 2)),
        states={
            'invisible': ~Bool(Eval('second_currency')),
        },
        depends=['second_currency_digits', 'second_currency'],
        readonly=True)
    currency = fields.Many2One('currency.currency', 'Currency', required=True,
        readonly=True)
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'on_change_with_currency_digits')
    second_currency = fields.Many2One('currency.currency', 'Second Currency',
        readonly=True, states={
            'invisible': ~Bool(Eval('second_currency', None)),
        }, depends=['second_currency'])
    second_currency_digits = fields.Function(fields.Integer(
            'Second Currency Digits'),
        'on_change_with_second_currency_digits')
    lines_amount = fields.Function(fields.Numeric('Assigned Amount',
            digits=(16, Eval('currency_digits', 2)),
            depends=['currency_digits']),
        'on_change_with_lines_amount')
    lines_amount_second_currency = fields.Function(fields.Numeric(
            'Assigned Amount Second Currency',
            digits=(16, Eval('currency_digits', 2)),
            states={
                'invisible': ~Bool(Eval('second_currency', None)),
            }, depends=['currency_digits', 'second_currency']),
        'on_change_with_lines_amount_second_currency')
    pending_amount = fields.Function(fields.Numeric('Pending Amount',
            digits=(16, Eval('currency_digits', 2)),
            depends=['currency_digits']),
        'on_change_with_pending_amount')
    pending_amount_second_currency = fields.Function(fields.Numeric(
            'Pending Amount Second Currency',
            digits=(16, Eval('second_currency_digits', 2)),
            states={
                'invisible': ~Bool(Eval('second_currency', None)),
            }, depends=['second_currency_digits', 'second_currency']),
        'on_change_with_pending_amount_second_currency')
    maturities = fields.One2Many('account.invoice.maturity_date', None,
        'Maturities', context={
            'invoice': Eval('invoice'),
            'currency': Eval('currency'),
            'second_currency': Eval('second_currency', None),
            'amount': Eval('pending_amount'),
            'amount_second_currency': (
                Eval('pending_amount_second_currency', None)),
            },
        depends=['currency', 'pending_amount'])

    @fields.depends('currency')
    def on_change_with_currency_digits(self, name=None):
        if self.currency:
            return self.currency.digits
        return 2

    @fields.depends('second_currency')
    def on_change_with_second_currency_digits(self, name=None):
        if self.second_currency:
            return self.second_currency.digits
        return 2

    @fields.depends('maturities')
    def on_change_with_lines_amount(self, name=None):
        return sum(
            (Decimal(l.amount or 0) for l in self.maturities), Decimal(0))

    @fields.depends('invoice_amount', 'maturities')
    def on_change_with_pending_amount(self, name=None):
        if self.invoice_amount:
            lines_amount = self.on_change_with_lines_amount()
            return self.invoice_amount - lines_amount

    @fields.depends('maturities')
    def on_change_with_lines_amount_second_currency(self, name=None):
        return sum(
            (Decimal(l.amount_second_currency or 0) for l in self.maturities),
            Decimal(0))

    @fields.depends('invoice_amount_second_currency', 'maturities')
    def on_change_with_pending_amount_second_currency(self, name=None):
        if self.invoice_amount_second_currency:
            lines_amount = self.on_change_with_lines_amount_second_currency()
            return self.invoice_amount_second_currency - lines_amount


class ModifyMaturities(Wizard):
    'Modify Maturities'
    __name__ = 'account.invoice.modify_maturities'
    start_state = 'next_'
    next_ = StateTransition()
    ask = StateView('account.invoice.modify_maturities.start',
        'account_invoice_maturity_dates.modify_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Ok', 'modify', 'tryton-ok', default=True),
            ])
    modify = StateTransition()

    def default_ask(self, fields):
        Currency = Pool().get('currency.currency')

        invoice = self.ask.invoice

        defaults = {}
        defaults['invoices'] = [i.id for i in self.ask.invoices]
        defaults['invoice'] = invoice.id
        defaults['currency'] = invoice.company.currency.id
        defaults['currency_digits'] = invoice.company.currency.digits
        if invoice.company.currency.id != invoice.currency.id:
            with Transaction().set_context(date=invoice.currency_date):
                total_amount = Currency.compute(
                    invoice.currency, invoice.total_amount,
                    invoice.company.currency)
            defaults['second_currency'] = invoice.currency.id
            defaults['second_currency_digits'] = invoice.currency.digits
            defaults['invoice_amount_second_currency'] = invoice.total_amount
        else:
            total_amount = invoice.total_amount
        defaults['invoice_amount'] = total_amount

        lines = []
        for line in invoice.move.lines:
            if line.account == invoice.account:
                if line.reconciliation:
                    # TODO remove raise user error or continue
                    raise UserError(
                        gettext('account_invoice_maturity_dates.msg_already_reconciled',
                        invoice=invoice.rec_name,
                        line=line.rec_name,
                        ))

                amount_second_currency = None
                second_currency = None
                if line.amount_second_currency:
                    amount_second_currency = line.amount_second_currency
                    second_currency = line.second_currency

                amount = line.credit - line.debit
                if invoice.type == 'out':
                    amount = amount.copy_negate()
                lines.append({
                        'id': line.id,
                        'invoice': invoice.id,
                        'move_line': line.id,
                        'date': line.maturity_date,
                        'amount': amount,
                        'currency': invoice.company.currency.id,
                        'currency_digits': invoice.company.currency.digits,
                        'amount_second_currency': amount_second_currency,
                        'second_currency': (second_currency.id
                            if second_currency else None),
                        'second_currency_digits': (second_currency.digits
                            if second_currency else None),
                        })
                defaults['maturities'] = sorted(lines, key=lambda a: a['date'])
        return defaults

    def transition_next_(self):
        Invoice = Pool().get('account.invoice')

        invoices = Invoice.browse(Transaction().context['active_ids'])

        def next_invoice():
            invoices = list(self.ask.invoices)
            if not invoices:
                return
            invoice = invoices.pop()
            self.ask.invoice = invoice
            self.ask.invoices = [i.id for i in invoices]
            return invoice

        if getattr(self.ask, 'invoices', None) is None:
            self.ask.invoices = [i.id for i in invoices
                if i.state not in ['cancel', 'paid']]

        while not next_invoice():
            return 'end'
        return 'ask'

    def transition_modify(self):
        Configuration = Pool().get('account.configuration')

        config = Configuration(1)
        invoice = self.ask.invoice

        if self.ask.pending_amount:
            # TODO remove raise user error
            raise UserError(
                gettext('account_invoice_maturity_dates.msg_pending_amount',
                amount=self.ask.pending_amount,
                currency=self.ask.currency.rec_name,
                ))

        invoice.set_maturities(self.ask.maturities)

        if config.remove_invoice_report_cache:
            invoice.invoice_report_cache = None
            invoice.save()
        return 'next_'
