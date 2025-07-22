import re
from datetime import datetime
from zoneinfo import ZoneInfo


def convert_string_to_date(date_string: str, hour: str) -> datetime:
    # splits the string
    day, month, year = re.split(r"[\/\.\-]", date_string.strip())
    native_date = datetime(int(year), int(month), int(day), int(hour), 0, 0, tzinfo=ZoneInfo("Australia/Sydney"))
    return native_date


def get_unix_timestamp(date: datetime) -> int:
    return round(date.timestamp())


if __name__ == "__main__":
    date_string = "01-01-2023"
    hour = "13"

    timestamp = convert_string_to_date(date_string, hour)

    print("austrlaian time")
    print(timestamp)
    unix_timestamp = get_unix_timestamp(timestamp)

    print(get_unix_timestamp(datetime.now()))
