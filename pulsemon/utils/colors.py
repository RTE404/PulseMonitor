def severity_color(val: float, yellow: float, red: float) -> str:
    if val >= red:
        return "red"
    elif val >= yellow:
        return "yellow"
    return "green"
