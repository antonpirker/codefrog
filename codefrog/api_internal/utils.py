
MONTH = 30
YEAR = 365

def get_best_frequency(date_from, date_to):
    """
    Calculate the best frequency for the given time span
    :param date_from:
    :param date_to:
    :return:
    """
    try:
        days = (date_to - date_from).days
    except TypeError:
        days = 0

    if 0 < days <= 3 * MONTH:
        frequency = 'D'
    elif 3 * MONTH < days <= 1 * YEAR:
        frequency = 'W'
    elif 1 * YEAR < days <= 3 * YEAR:
        frequency = 'M'
    elif days > 3 * YEAR:
        frequency = 'Q'
    else:  # default
        frequency = 'D'

    return frequency
