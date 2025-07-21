import datetime
import re

def convert_string_to_date(date_string: str, hour_string: str) -> datetime.datetime:
    # splits the string
    day, month, year = re.split(r"[\/\.\-]", date_string.strip())
    native_date = datetime.datetime.strptime(day + month + year + hour_string, "%d%m%Y%H")
    return native_date

def get_unix_timestamp(date: datetime.datetime) -> float:
    return date.timestamp()

if __name__ == "__main__":
    date_string = "01-01-2023"
    hour = "13"

    timestamp = convert_string_to_date(date_string, hour_string=hour)

    print(timestamp)

    new_dt = datetime.timedelta(hours=3)

    unix_timestamp = get_unix_timestamp(timestamp)

