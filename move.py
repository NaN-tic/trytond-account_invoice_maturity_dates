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
                    })
        values['terms'] = terms
        return values

    def default_preview(self, fields):
        values = super().default_preview(fields)
        move_description, = {r.move.description for r in self.records}
        values['description'] = move_description
        line_description, = {r.description for r in self.records}
        for value in values.get('terms', None):
            value['description'] = line_description
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
