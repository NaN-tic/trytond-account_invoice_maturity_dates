===============================
Invoice Maturity Dates Scenario
===============================

Imports::
    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> today = datetime.date.today()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install account_invoice::

    >>> Module = Model.get('ir.module.module')
    >>> module, = Module.find(
    ...     [('name', '=', 'account_invoice_maturity_dates')])
    >>> module.click('install')
    >>> Wizard('ir.module.module.install_upgrade').execute('upgrade')

Create company::

    >>> Currency = Model.get('currency.currency')
    >>> CurrencyRate = Model.get('currency.currency.rate')
    >>> currencies = Currency.find([('code', '=', 'USD')])
    >>> if not currencies:
    ...     currency = Currency(name='US Dollar', symbol=u'$', code='USD',
    ...         rounding=Decimal('0.01'), mon_grouping='[]',
    ...         mon_decimal_point='.')
    ...     currency.save()
    ...     CurrencyRate(date=today + relativedelta(month=1, day=1),
    ...         rate=Decimal('1.0'), currency=currency).save()
    ... else:
    ...     currency, = currencies
    >>> Company = Model.get('company.company')
    >>> Party = Model.get('party.party')
    >>> company_config = Wizard('company.company.config')
    >>> company_config.execute('company')
    >>> company = company_config.form
    >>> party = Party(name='Dunder Mifflin')
    >>> party.save()
    >>> company.party = party
    >>> company.currency = currency
    >>> company_config.execute('add')
    >>> company, = Company.find([])

Reload the context::

    >>> User = Model.get('res.user')
    >>> config._context = User.get_preferences(True, config.context)

Create fiscal year::

    >>> FiscalYear = Model.get('account.fiscalyear')
    >>> Sequence = Model.get('ir.sequence')
    >>> SequenceStrict = Model.get('ir.sequence.strict')
    >>> fiscalyear = FiscalYear(name=str(today.year))
    >>> fiscalyear.start_date = today + relativedelta(month=1, day=1)
    >>> fiscalyear.end_date = today + relativedelta(month=12, day=31)
    >>> fiscalyear.company = company
    >>> post_move_seq = Sequence(name=str(today.year), code='account.move',
    ...     company=company)
    >>> post_move_seq.save()
    >>> fiscalyear.post_move_sequence = post_move_seq
    >>> invoice_seq = SequenceStrict(name=str(today.year),
    ...     code='account.invoice', company=company)
    >>> invoice_seq.save()
    >>> fiscalyear.out_invoice_sequence = invoice_seq
    >>> fiscalyear.in_invoice_sequence = invoice_seq
    >>> fiscalyear.out_credit_note_sequence = invoice_seq
    >>> fiscalyear.in_credit_note_sequence = invoice_seq
    >>> fiscalyear.save()
    >>> FiscalYear.create_period([fiscalyear.id], config.context)

Create chart of accounts::

    >>> AccountTemplate = Model.get('account.account.template')
    >>> Account = Model.get('account.account')
    >>> account_template, = AccountTemplate.find([('parent', '=', None)])
    >>> create_chart = Wizard('account.create_chart')
    >>> create_chart.execute('account')
    >>> create_chart.form.account_template = account_template
    >>> create_chart.form.company = company
    >>> create_chart.execute('create_account')
    >>> receivable, = Account.find([
    ...         ('kind', '=', 'receivable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> payable, = Account.find([
    ...         ('kind', '=', 'payable'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> revenue, = Account.find([
    ...         ('kind', '=', 'revenue'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> expense, = Account.find([
    ...         ('kind', '=', 'expense'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> account_tax, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('company', '=', company.id),
    ...         ('name', '=', 'Main Tax'),
    ...         ])
    >>> create_chart.form.account_receivable = receivable
    >>> create_chart.form.account_payable = payable
    >>> create_chart.execute('create_properties')

Allow to cancel moves on expense jounral::

    >>> Journal = Model.get('account.journal')
    >>> expense_journal, = Journal.find([('type', '=', 'expense')])
    >>> expense_journal.update_posted = True
    >>> expense_journal.save()

Configure cash journal::

    >>> cash, = Account.find([
    ...         ('kind', '=', 'other'),
    ...         ('name', '=', 'Main Cash'),
    ...         ('company', '=', company.id),
    ...         ])
    >>> cash_journal, = Journal.find([('type', '=', 'cash')])
    >>> cash_journal.credit_account = cash
    >>> cash_journal.debit_account = cash
    >>> cash_journal.save()

Create tax::

    >>> TaxCode = Model.get('account.tax.code')
    >>> Tax = Model.get('account.tax')
    >>> tax = Tax()
    >>> tax.name = 'Tax'
    >>> tax.description = 'Tax'
    >>> tax.type = 'percentage'
    >>> tax.rate = Decimal('.10')
    >>> tax.invoice_account = account_tax
    >>> tax.credit_note_account = account_tax
    >>> invoice_base_code = TaxCode(name='invoice base')
    >>> invoice_base_code.save()
    >>> tax.invoice_base_code = invoice_base_code
    >>> invoice_tax_code = TaxCode(name='invoice tax')
    >>> invoice_tax_code.save()
    >>> tax.invoice_tax_code = invoice_tax_code
    >>> credit_note_base_code = TaxCode(name='credit note base')
    >>> credit_note_base_code.save()
    >>> tax.credit_note_base_code = credit_note_base_code
    >>> credit_note_tax_code = TaxCode(name='credit note tax')
    >>> credit_note_tax_code.save()
    >>> tax.credit_note_tax_code = credit_note_tax_code
    >>> tax.save()

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
    >>> template.save()
    >>> product.template = template
    >>> product.save()

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> PaymentTermLine = Model.get('account.invoice.payment_term.line')
    >>> payment_term = PaymentTerm(name='Term')
    >>> payment_term_line = PaymentTermLine(type='percent', days=0,
    ...     percentage=Decimal(50))
    >>> payment_term.lines.append(payment_term_line)
    >>> payment_term_line = PaymentTermLine(type='remainder', days=15)
    >>> payment_term.lines.append(payment_term_line)
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
    UserError: ('UserError', (u'Can not modify maturities of invoice 1 because its line (Main Payable) is reconciled', ''))


Create a refund and check we can modify it maturities::

    >>> credit_note = Invoice()
    >>> credit_note.type = 'in_credit_note'
    >>> credit_note.party = party
    >>> credit_note.invoice_date = today
    >>> credit_note.payment_term = payment_term
    >>> line = credit_note.lines.new()
    >>> line.product = product
    >>> line.quantity = 8
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
