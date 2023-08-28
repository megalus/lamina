import json
from datetime import date
from decimal import Decimal


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, date):
            return o.isoformat()
        return super(DecimalEncoder, self).default(o)
