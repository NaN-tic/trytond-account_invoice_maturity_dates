===============================
Invoice Maturity Dates Scenario
===============================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences

Install account_invoice::

    >>> config = activate_modules('account_invoice_maturity_dates')

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
    >>> revenue_journal, = Journal.find([('type', '=', 'revenue')])

Configure cash journal::

    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> PaymentMethod = Model.get('account.invoice.payment.method')
    >>> payment_method = PaymentMethod(name='Cash', journal=cash_journal,
    ...    credit_account=cash, debit_account=cash)
    >>> payment_method.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.save()

Create account category::

    >>> Tax = Model.get('account.tax')
    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.customer_taxes.append(tax)
    >>> account_category.supplier_taxes.append(Tax(tax.id))
    >>> account_category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> Product = Model.get('product.product')
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.list_price = Decimal('40')
    >>> template.account_category = account_category
    >>> product, = template.products
    >>> product.cost_price = Decimal('5')
    >>> template.save()
    >>> product, = template.products

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> payment_term = PaymentTerm(name='Term')
    >>> line = payment_term.lines.new(type='percent', ratio=Decimal('.5'))
    >>> delta = line.relativedeltas.new(days=0)
    >>> line = payment_term.lines.new(type='remainder')
    >>> delta = line.relativedeltas.new(days=15)
    >>> payment_term.save()

Compute today::

    >>> today = datetime.date.today()

Create invoice::

    >>> Invoice = Model.get('account.invoice')
    >>> invoice = Invoice()
    >>> invoice.type = 'in'
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
    >>> first_maturity.amount = Decimal('55.00')
    >>> modify.form.pending_amount
    Decimal('55.00')
    >>> modify.execute('modify')  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    UserError: ('UserError', ('There is still 55.00 U.S. Dollar to be assigned. Please assignt it to some maturity date', ''))
    >>> new_maturity = modify.form.maturities.new()
    >>> new_maturity.amount
    Decimal('55.00')
    >>> new_maturity.date = today + relativedelta(days=2)
    >>> modify.execute('modify')
    >>> invoice.reload()
    >>> first, second, third = sorted(invoice.lines_to_pay,
    ...     key=lambda a: a.maturity_date)
    >>> first.credit
    Decimal('55.00')
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
    >>> pay.form.payment_method = payment_method
    >>> pay.form.amount = Decimal('110.00')
    >>> pay.execute('choice')
    >>> invoice.reload()
    >>> invoice.amount_to_pay
    Decimal('110.00')
    >>> modify = Wizard('account.invoice.modify_maturities', [invoice])  # doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
        ...
    UserError: ('UserError', ('Can not modify maturities of invoice 1 because its line (Main Payable) is reconciled', ''))

Create a refund and check we can modify it maturities::

    >>> credit_note = Invoice()
    >>> credit_note.type = 'in'
    >>> credit_note.party = party
    >>> credit_note.invoice_date = today
    >>> credit_note.payment_term = payment_term
    >>> line = credit_note.lines.new()
    >>> line.product = product
    >>> line.quantity = -8
    >>> line.unit_price = Decimal(25)
    >>> credit_note.untaxed_amount
    Decimal('-200.00')
    >>> credit_note.tax_amount
    Decimal('-20.00')
    >>> credit_note.total_amount
    Decimal('-220.00')
    >>> credit_note.click('post')
    >>> modify = Wizard('account.invoice.modify_maturities', [credit_note])
    >>> modify.form.invoice_amount
    Decimal('-220.00')
    >>> modify.form.lines_amount
    Decimal('-220.00')
    >>> modify.form.pending_amount
    Decimal('0.00')
    >>> first_maturity, second_maturity = modify.form.maturities
    >>> first_maturity.amount
    Decimal('-110.00')
    >>> first_maturity.date == today
    True
    >>> second_maturity.amount
    Decimal('-110.00')
    >>> second_maturity.date == today + relativedelta(days=15)
    True
    >>> first_maturity.amount = Decimal('-55.0')
    >>> modify.form.pending_amount
    Decimal('-55.00')
    >>> new_maturity = modify.form.maturities.new()
    >>> new_maturity.amount
    Decimal('-55.00')
    >>> new_maturity.date = today + relativedelta(days=2)
    >>> modify.execute('modify')
    >>> credit_note.reload()
    >>> first, second, third = sorted(credit_note.lines_to_pay,
    ...     key=lambda a: a.maturity_date)
    >>> first.debit
    Decimal('55.00')
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
    >>> invoice.type = 'out'
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
    Decimal('55.00')
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
    >>> credit_note.type = 'out'
    >>> credit_note.party = party
    >>> credit_note.invoice_date = today
    >>> credit_note.payment_term = payment_term
    >>> line = credit_note.lines.new()
    >>> line.product = product
    >>> line.quantity = -8
    >>> line.unit_price = Decimal('25.0')
    >>> credit_note.untaxed_amount
    Decimal('-200.00')
    >>> credit_note.tax_amount
    Decimal('-20.00')
    >>> credit_note.total_amount
    Decimal('-220.00')
    >>> credit_note.click('post')
    >>> modify = Wizard('account.invoice.modify_maturities', [credit_note])
    >>> modify.form.invoice_amount
    Decimal('-220.00')
    >>> modify.form.lines_amount
    Decimal('-220.00')
    >>> modify.form.pending_amount
    Decimal('0.00')
    >>> first_maturity, second_maturity = modify.form.maturities
    >>> first_maturity.amount
    Decimal('-110.00')
    >>> first_maturity.date == today
    True
    >>> second_maturity.amount
    Decimal('-110.00')
    >>> second_maturity.date == today + relativedelta(days=15)
    True
    >>> first_maturity.amount = Decimal('-55.0')
    >>> modify.form.pending_amount
    Decimal('-55.00')
    >>> new_maturity = modify.form.maturities.new()
    >>> new_maturity.amount
    Decimal('-55.00')
    >>> new_maturity.date = today + relativedelta(days=2)
    >>> modify.execute('modify')
    >>> credit_note.reload()
    >>> first, second, third = sorted(credit_note.lines_to_pay,
    ...     key=lambda a: a.maturity_date)
    >>> first.credit
    Decimal('55.00')
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
