from requests import Response


def try_get_json(r: Response, key: str) -> str:
    """
    Try to parse a response as json and get an attribute but
    but fall back to just providing the response text
    """
    try:
        return str(r.json()[key])
    except (ValueError, KeyError):
        return r.text
