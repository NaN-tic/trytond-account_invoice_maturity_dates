===============================
Invoice Maturity Dates Scenario
===============================

Imports::
    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install account_invoice::

    >>> Module = Model.get('ir.module')
    >>> module, = Module.find(
    ...     [('name', '=', 'account_invoice_maturity_dates')])
    >>> module.click('install')
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company))
    >>> fiscalyear.click('create_period')

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> cash = accounts['cash']

    >>> Journal = Model.get('account.journal')
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.credit_account = cash
    >>> cash_journal.debit_account = cash
    >>> cash_journal.save()

Create tax::

    >>> tax = create_tax(Decimal('.10'))
    >>> tax.save()

Create parties::

    >>> Party = Model.get('party.party')
    >>> supplier = Party(name='Supplier')
    >>> supplier.save()
    >>> customer = Party(name='Customer')
    >>> customer.save()

Allow to cancel moves on expense and revenue jounral::

    >>> Journal = Model.get('account.journal')
    >>> expense_journal, = Journal.find([('type', '=', 'expense')])
    >>> expense_journal.update_posted = True
    >>> expense_journal.save()
    >>> revenue_journal, = Journal.find([('type', '=', 'revenue')])
    >>> revenue_journal.update_posted = True
    >>> revenue_journal.save()

Configure cash journal::

    >>> Account = Model.get('account.account')
    >>> cash, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('name', '=', 'Main Cash'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.credit_account = cash
    >>> cash_journal.debit_account = cash
    >>> cash_journal.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> product = Product()
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.list_price = Decimal('40')
    >>> template.cost_price = Decimal('25')
    >>> template.account_expense = expense
    >>> template.account_revenue = revenue
    >>> template.supplier_taxes.append(tax)
    >>> template.customer_taxes.append(Tax(tax.id))
    >>> template.save()
    >>> product.template = template
    >>> product.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> payment_term = PaymentTerm(name='Term')
    >>> line = payment_term.lines.new(type='percent', ratio=Decimal('.5'))
    >>> delta = line.relativedeltas.new(days=0)
    >>> line = payment_term.lines.new(type='remainder')
    >>> delta = line.relativedeltas.new(days=15)
    >>> payment_term.save()

Create invoice::

    >>> Invoice = Model.get('account.invoice')
    >>> invoice = Invoice()
    >>> invoice.type = 'in_invoice'
    >>> invoice.party = party
    >>> invoice.invoice_date = today
    >>> invoice.payment_term = payment_term
    >>> line = invoice.lines.new()
    >>> line.product = product
    >>> line.quantity = 8
    >>> line.unit_price = Decimal('25')
    >>> invoice.untaxed_amount
    Decimal('200.00')
    >>> invoice.tax_amount
    Decimal('20.00')
    >>> invoice.total_amount
    Decimal('220.00')
    >>> invoice.click('post')

Split first maturity into two::

    >>> modify = Wizard('account.invoice.modify_maturities', [invoice])
    >>> modify.form.invoice_amount
    Decimal('220.00')
    >>> modify.form.lines_amount
    Decimal('220.00')
    >>> modify.form.pending_amount
    Decimal('0.00')
    >>> first_maturity, second_maturity = modify.form.maturities
    >>> first_maturity.amount
    Decimal('110.00')
    >>> first_maturity.date == today
    True
    >>> second_maturity.amount
    Decimal('110.00')
    >>> second_maturity.date == today + relativedelta(days=15)
    True
    >>> first_maturity.amount = Decimal('55.0')
    >>> modify.form.pending_amount
    Decimal('55.00')
    >>> modify.execute('modify')
    Traceback (most recent call last):
        ...
    UserError: ('UserError', (u'There is still 55.00 US Dollar to be assigned. Please assignt it to some maturity date', ''))
    >>> new_maturity = modify.form.maturities.new()
    >>> new_maturity.amount
    Decimal('55.00')
    >>> new_maturity.date = today + relativedelta(days=2)
    >>> modify.execute('modify')
    >>> invoice.reload()
    >>> first, second, third = sorted(invoice.lines_to_pay,
    ...     key=lambda a: a.maturity_date)
    >>> first.credit
    Decimal('55.0')
    >>> first.maturity_date == today
    True
    >>> second.credit
    Decimal('55.00')
    >>> second.maturity_date == today + relativedelta(days=2)
    True
    >>> third.credit
    Decimal('110.00')
    >>> third.maturity_date == today + relativedelta(days=15)
    True

Unify all maturities to two::

    >>> modify = Wizard('account.invoice.modify_maturities', [invoice])
    >>> _ = modify.form.maturities.pop()
    >>> _ = modify.form.maturities.pop()
    >>> _ = modify.form.maturities.pop()
    >>> new_maturity = modify.form.maturities.new()
    >>> new_maturity.date = today
    >>> new_maturity.amount = Decimal('110.00')
    >>> new_maturity = modify.form.maturities.new()
    >>> new_maturity.date = today + relativedelta(days=15)
    >>> modify.execute('modify')
    >>> invoice.reload()
    >>> first, second = sorted(invoice.lines_to_pay,
    ...     key=lambda a: a.maturity_date)
    >>> first.credit
    Decimal('110.00')
    >>> first.maturity_date == today
    True
    >>> second.credit
    Decimal('110.00')
    >>> second.maturity_date == today + relativedelta(days=15)
    True

Partialy pay the invoice and check we can not change anymore the maturities::

    >>> pay = Wizard('account.invoice.pay', [invoice])
    >>> pay.form.journal = cash_journal
    >>> pay.form.amount = Decimal('110.00')
    >>> pay.execute('choice')
    >>> invoice.reload()
    >>> invoice.amount_to_pay
    Decimal('110.00')
    >>> modify = Wizard('account.invoice.modify_maturities', [invoice])
    Traceback (most recent call last):
        ...
    UserError: ('UserError', (u'Can not modify maturities of invoice 1 Party because its line (Main Payable) is reconciled', ''))


Create a refund and check we can modify it maturities::

    >>> credit_note = Invoice()
    >>> credit_note.type = 'in_credit_note'
    >>> credit_note.party = party
    >>> credit_note.invoice_date = today
    >>> credit_note.payment_term = payment_term
    >>> line = credit_note.lines.new()
    >>> line.product = product
    >>> line.quantity = -8
    >>> line.unit_price = Decimal(25)
    >>> credit_note.untaxed_amount
    Decimal('200.00')
    >>> credit_note.tax_amount
    Decimal('20.00')
    >>> credit_note.total_amount
    Decimal('220.00')
    >>> credit_note.click('post')
    >>> modify = Wizard('account.invoice.modify_maturities', [credit_note])
    >>> modify.form.invoice_amount
    Decimal('220.00')
    >>> modify.form.lines_amount
    Decimal('220.00')
    >>> modify.form.pending_amount
    Decimal('0.00')
    >>> first_maturity, second_maturity = modify.form.maturities
    >>> first_maturity.amount
    Decimal('110.00')
    >>> first_maturity.date == today
    True
    >>> second_maturity.amount
    Decimal('110.00')
    >>> second_maturity.date == today + relativedelta(days=15)
    True
    >>> first_maturity.amount = Decimal('55.0')
    >>> modify.form.pending_amount
    Decimal('55.00')
    >>> new_maturity = modify.form.maturities.new()
    >>> new_maturity.amount
    Decimal('55.00')
    >>> new_maturity.date = today + relativedelta(days=2)
    >>> modify.execute('modify')
    >>> credit_note.reload()
    >>> first, second, third = sorted(credit_note.lines_to_pay,
    ...     key=lambda a: a.maturity_date)
    >>> first.debit
    Decimal('55.0')
    >>> first.maturity_date == today
    True
    >>> second.debit
    Decimal('55.00')
    >>> second.maturity_date == today + relativedelta(days=2)
    True
    >>> third.debit
    Decimal('110.00')
    >>> third.maturity_date == today + relativedelta(days=15)
    True

Create customer invoice::

    >>> Invoice = Model.get('account.invoice')
    >>> invoice = Invoice()
    >>> invoice.type = 'out_invoice'
    >>> invoice.party = party
    >>> invoice.invoice_date = today
    >>> invoice.payment_term = payment_term
    >>> line = invoice.lines.new()
    >>> line.product = product
    >>> line.quantity = 8
    >>> line.unit_price = Decimal('25.0')
    >>> invoice.untaxed_amount
    Decimal('200.00')
    >>> invoice.tax_amount
    Decimal('20.00')
    >>> invoice.total_amount
    Decimal('220.00')
    >>> invoice.click('post')

Split first maturity into two::

    >>> modify = Wizard('account.invoice.modify_maturities', [invoice])
    >>> modify.form.invoice_amount
    Decimal('220.00')
    >>> modify.form.lines_amount
    Decimal('220.00')
    >>> modify.form.pending_amount
    Decimal('0.00')
    >>> first_maturity, second_maturity = modify.form.maturities
    >>> first_maturity.amount
    Decimal('110.00')
    >>> first_maturity.date == today
    True
    >>> second_maturity.amount
    Decimal('110.00')
    >>> second_maturity.date == today + relativedelta(days=15)
    True
    >>> first_maturity.amount = Decimal('55.0')
    >>> new_maturity = modify.form.maturities.new()
    >>> new_maturity.amount
    Decimal('55.00')
    >>> new_maturity.date = today + relativedelta(days=2)
    >>> modify.execute('modify')
    >>> invoice.reload()
    >>> first, second, third = sorted(invoice.lines_to_pay,
    ...     key=lambda a: a.maturity_date)
    >>> first.debit
    Decimal('55.0')
    >>> first.maturity_date == today
    True
    >>> second.debit
    Decimal('55.00')
    >>> second.maturity_date == today + relativedelta(days=2)
    True
    >>> third.debit
    Decimal('110.00')
    >>> third.maturity_date == today + relativedelta(days=15)
    True

Create a customer refund and check we can modify it maturities::

    >>> credit_note = Invoice()
    >>> credit_note.type = 'out_credit_note'
    >>> credit_note.party = party
    >>> credit_note.invoice_date = today
    >>> credit_note.payment_term = payment_term
    >>> line = credit_note.lines.new()
    >>> line.product = product
    >>> line.quantity = 8
    >>> line.unit_price = Decimal('25.0')
    >>> credit_note.untaxed_amount
    Decimal('200.00')
    >>> credit_note.tax_amount
    Decimal('20.00')
    >>> credit_note.total_amount
    Decimal('220.00')
    >>> credit_note.click('post')
    >>> modify = Wizard('account.invoice.modify_maturities', [credit_note])
    >>> modify.form.invoice_amount
    Decimal('220.00')
    >>> modify.form.lines_amount
    Decimal('220.00')
    >>> modify.form.pending_amount
    Decimal('0.00')
    >>> first_maturity, second_maturity = modify.form.maturities
    >>> first_maturity.amount
    Decimal('110.00')
    >>> first_maturity.date == today
    True
    >>> second_maturity.amount
    Decimal('110.00')
    >>> second_maturity.date == today + relativedelta(days=15)
    True
    >>> first_maturity.amount = Decimal('55.0')
    >>> modify.form.pending_amount
    Decimal('55.00')
    >>> new_maturity = modify.form.maturities.new()
    >>> new_maturity.amount
    Decimal('55.00')
    >>> new_maturity.date = today + relativedelta(days=2)
    >>> modify.execute('modify')
    >>> credit_note.reload()
    >>> first, second, third = sorted(credit_note.lines_to_pay,
    ...     key=lambda a: a.maturity_date)
    >>> first.credit
    Decimal('55.0')
    >>> first.maturity_date == today
    True
    >>> second.credit
    Decimal('55.00')
    >>> second.maturity_date == today + relativedelta(days=2)
    True
    >>> third.credit
    Decimal('110.00')
    >>> third.maturity_date == today + relativedelta(days=15)
    True
