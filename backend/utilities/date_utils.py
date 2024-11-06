
# app/utils/date_utils.py
from datetime import datetime

def neo4j_datetime_to_python_datetime(neo4j_dt_str: str) -> datetime:
    truncated_str = neo4j_dt_str[:26] + neo4j_dt_str[29:]
    return datetime.fromisoformat(truncated_str)
