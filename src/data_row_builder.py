'''
These are the data types used to generate a row of data in the final processed journal file
'''

class BaseDataRow(object):
    received_from = "Message Therapy Customers"
    description = "Vagaro Merchant Services Deposit"
    payment_method = ""
    ref_no = ""
    account_name = "00-001 SLW Main Checking"
    credits = ""
    debits = ""

    @classmethod
    def _get_all_level_attributes(cls):
        '''
        This class method will grab all of the keys from the union of the base and children below
        This means that we can build a dictionary from the attributes, tossing any magic attributes
        '''
        attributes = {}
        for base in reversed(cls.mro()):
            attributes.update({
                key.title().replace('_', ' '): value for key, value in base.__dict__.items()
                if not key.startswith('__') and not key.startswith('_') and not callable(value)
            })
        return attributes

class IncomeDataRow(BaseDataRow):
    account_name = "02-003 Massage Income"

class TipsDataRow(BaseDataRow):
    account_name = "02-004 Tips for Service Income"

class MembershipDataRow(BaseDataRow):
    account_name = "02-008 Membership Income"

class DiscountDataRow(BaseDataRow):
    account_name = "02-010 Discount Income"

class VagaroFeeDataRow(BaseDataRow):
    account_name = "01-017 Vagaro Fees"
    received_from = "Vagaro"

class DataRowFactory:

    def __init__(self):
        self.data_types = []

    def add_data_type(self, data_type):
        if data_type == '':
            self.data_types.append('totals')
        else:
            self.data_types.append(data_type)

    def build_data_row(self, data_type=''):
        self.add_data_type(data_type)
        if data_type.lower() == 'income':
            return IncomeDataRow()._get_all_level_attributes()
        elif data_type.lower() == 'tips':
            return TipsDataRow()._get_all_level_attributes()
        elif data_type.lower() == 'membership':
            return MembershipDataRow()._get_all_level_attributes()
        elif data_type.lower() == 'discount':
            return DiscountDataRow()._get_all_level_attributes()
        elif data_type.lower() == 'vagaro':
            return VagaroFeeDataRow._get_all_level_attributes()
        return BaseDataRow()._get_all_level_attributes()