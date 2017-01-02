#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import unittest
import doctest
import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from functools import partial
import trytond.tests.test_tryton
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT, test_view,\
    test_depends
from trytond.tests.test_tryton import doctest_setup, doctest_teardown
from trytond.transaction import Transaction
from trytond.exceptions import UserWarning


class TestAccountInvoiceMaturityDatesCase(unittest.TestCase):
    'Test Account Invoice Maturity Dates module'

    def setUp(self):
        trytond.tests.test_tryton.install_module('account_invoice_maturity_dates')
        self.company = POOL.get('company.company')
        self.user = POOL.get('res.user')
        self.journal = POOL.get('account.journal')
        self.account = POOL.get('account.account')
        self.payment_term = POOL.get('account.invoice.payment_term')
        self.fiscalyear = POOL.get('account.fiscalyear')
        self.sequence = POOL.get('ir.sequence')
        self.sequence_strict = POOL.get('ir.sequence.strict')
        self.move = POOL.get('account.move')
        self.party = POOL.get('party.party')
        self.invoice = POOL.get('account.invoice')
        self.invoice_line = POOL.get('account.invoice.line')
        self.maturity_date = POOL.get('account.invoice.maturity_date')

    def test0005views(self):
        'Test views'
        test_view('account_invoice_maturity_dates')

    def test0006depends(self):
        'Test depends'
        test_depends()

    def test0010move_internal_quantity(self):
        'Test Move.internal_quantity'
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            today = datetime.date.today()

            company, = self.company.search([
                    ('rec_name', '=', 'Dunder Mifflin'),
                    ])
            currency = company.currency
            self.user.write([self.user(USER)], {
                'main_company': company.id,
                'company': company.id,
                })

            fiscalyear, = self.fiscalyear.search([])
            invoice_sequence, = self.sequence_strict.create([{
                        'name': '%s' % today.year,
                        'code': 'account.invoice',
                        'company': company.id,
                        }])
            fiscalyear.out_invoice_sequence = invoice_sequence
            fiscalyear.in_invoice_sequence = invoice_sequence
            fiscalyear.out_credit_note_sequence = invoice_sequence
            fiscalyear.in_credit_note_sequence = invoice_sequence
            fiscalyear.save()

            journal, = self.journal.search([
                    ('code', '=', 'REV'),
                    ])
            journal.update_posted = True
            journal.save()

            receivable, = self.account.search([
                ('kind', '=', 'receivable'),
                ('company', '=', company.id),
                ])
            revenue, = self.account.search([
                ('kind', '=', 'revenue'),
                ('company', '=', company.id),
                ])

            payment_term, = self.payment_term.create([{
                        'name': 'Payment Term',
                        'lines': [
                            ('create', [{
                                        'sequence': 0,
                                        'type': 'remainder',
                                        'months': 0,
                                        'days': 0,
                                        }])]
                        }])

            customer, = self.party.create([{
                        'name': 'customer',
                        'addresses': [
                            ('create', [{}]),
                            ],
                        'account_receivable': receivable.id,
                        'customer_payment_term': payment_term.id,
                        }])

            invoice = self.invoice()
            invoice.company = company
            invoice.type = 'out_invoice'
            invoice.party = customer
            invoice.invoice_address = customer.addresses[0]
            invoice.currency = company.currency
            invoice.journal = journal
            invoice.account = receivable
            invoice.payment_term = payment_term
            invoice.lines = []
            invoice_line = self.invoice_line()
            invoice.lines.append(invoice_line)
            invoice_line.quantity = 1
            invoice_line.account = revenue
            invoice_line.unit_price = Decimal('100.00')
            invoice_line.description = 'Product'
            invoice.save()
            self.invoice().post([invoice])

            # if m.account == invoice.account
            move_line = invoice.move.lines[0]

            mdates = []
            mdate = self.maturity_date()
            mdate.date = today
            mdate.amount = Decimal('40.00')
            mdate.move_line = move_line
            mdates.append(mdate)
            mdate2 = self.maturity_date()
            mdate2.date = today + datetime.timedelta(days=10)
            mdate2.amount = Decimal('60.00')
            mdate2.move_line = None
            mdates.append(mdate2)
            invoice.set_maturities(mdates)

            self.assertEqual(invoice.move.lines[0].debit, Decimal('60.00'))
            self.assertEqual(invoice.move.lines[1].debit, Decimal('40.00'))
            self.assertEqual(invoice.move.lines[2].credit, Decimal('100.00'))

def suite():
    suite = trytond.tests.test_tryton.suite()
    from trytond.modules.company.tests import test_company
    for test in test_company.suite():
        if test not in suite and not isinstance(test, doctest.DocTestCase):
            suite.addTest(test)
    from trytond.modules.account.tests import test_account
    for test in test_account.suite():
        if test not in suite and not isinstance(test, doctest.DocTestCase):
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        TestAccountInvoiceMaturityDatesCase))
    return suite
