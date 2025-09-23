import re
from datetime import datetime
from zoneinfo import ZoneInfo


def convert_string_to_date(date_string: str, hour: str) -> datetime:
    # splits the string
    day, month, year = re.split(r"[\/\.\-]", date_string.strip())
    native_date = datetime(int(year), int(month), int(day), int(hour), 0, 0, tzinfo=ZoneInfo("Australia/Sydney"))
    return native_date
