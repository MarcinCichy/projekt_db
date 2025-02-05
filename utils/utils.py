# utils/utils.py
def parse_decimal_input(value):
    """Konwertuje wartość tekstową z przecinkiem lub kropką na liczbę dziesiętną."""
    try:
        return float(value.replace(',', '.'))
    except ValueError:
        raise ValueError(f"Niepoprawny format liczbowy: {value}")
