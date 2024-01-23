#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import fields, ModelSQL
from trytond.pool import PoolMeta, Pool
from trytond.modules.company.model import CompanyValueMixin
from trytond.pyson import Eval

maturities_on_customer_post = fields.Boolean('Show Maturities on '
    'Customer Invoices Post')
maturities_on_supplier_post = fields.Boolean('Show Maturities on '
    'Supplier Invoices Post')
maturities_invoice_report = fields.Boolean(
        'Maturities Invoice Report', help=('If we mark it as true, remove '
            'invoice report from invoice and create new invoice report'))


class Configuration(metaclass=PoolMeta):
    __name__ = 'account.configuration'
    maturities_on_customer_post = fields.MultiValue(maturities_on_customer_post)
    maturities_on_supplier_post = fields.MultiValue(maturities_on_supplier_post)
    maturities_invoice_report = fields.MultiValue(maturities_invoice_report)

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field in {'maturities_on_customer_post',
                'maturities_on_supplier_post', 'maturities_invoice_report'}:
            return pool.get('account.configuration.default_account')
        return super(Configuration, cls).multivalue_model(field)


class ConfigurationConformity(metaclass=PoolMeta):
    __name__ = 'account.configuration.default_account'
    maturities_on_customer_post = maturities_on_customer_post
    maturities_on_supplier_post = maturities_on_supplier_post
    maturities_invoice_report = maturities_invoice_report
