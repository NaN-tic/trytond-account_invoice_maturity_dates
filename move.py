# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pyson import Eval
from trytond.pool import PoolMeta
from trytond.wizard import Wizard


class RescheduleLines(Wizard):
    "Reschedule Lines"
    __name__ = 'account.move.line.reschedule'

    def default_start(self, fields):
        values = super().default_start(fields)
        terms = []
        for record in self.records:
            terms.append({
                    'date': record.maturity_date,
                    'amount': record.amount,
                    'currency': values.get('currency'),
                    'description': record.description,
                    'payment_type': record.payment_type.id,
                    'bank_account': record.bank_account.id,
                    })
        values['terms'] = terms
        return values

    def default_preview(self, fields):
        values = super().default_preview(fields)
        move_description, = {r.move.description for r in self.records}
        values['description'] = move_description
        line_description, = {r.description for r in self.records}
        payment_type, = {r.payment_type.id for r in self.records}
        bank_account, = {r.bank_account.id for r in self.records}
        for value in values.get('terms', []):
            value['description'] = line_description
            value['payment_type'] = payment_type
            value['bank_account'] = bank_account
        return values

    @classmethod
    def get_reschedule_move(
            cls, amount, balance, journal, terms, account, date=None,
            **line_values):
        move, balance_line = super().get_reschedule_move(amount, balance,
            journal, terms, account, date, **line_values)
        for line in move.lines:
            for term in terms:
                if term.date == line.maturity_date:
                    line.description = term.description
                    line.payment_type = term.payment_type
                    line.bank_account = term.bank_account
                    if not term.bank_account:
                        line.on_change_payment_type()

        return move, balance_line


class RescheduleLinesStart(metaclass=PoolMeta):
    "Reschedule Lines"
    __name__ = 'account.move.line.reschedule.start'

    terms = fields.One2Many(
        'account.move.line.reschedule.term', None, "Terms",
        domain=[
            ('currency', '=', Eval('currency', -1)),
            ], readonly=True)


class RescheduleLinesTerm(metaclass=PoolMeta):
    "Reschedule Lines"
    __name__ = 'account.move.line.reschedule.term'

    description = fields.Char("Description")
    payment_type = fields.Many2One('account.payment.type', 'Payment Type')
    bank_account = fields.Many2One('bank.account', 'Bank Account')
