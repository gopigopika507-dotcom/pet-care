from datetime import date, timedelta


def calculate_streak(dates):

    if not dates:
        return 0, 0

    dates = sorted(set(dates), reverse=True)

    converted_dates = []

    for d in dates:

        if isinstance(d, str):
            d = date.fromisoformat(d)

        converted_dates.append(d)

    dates = converted_dates

    today = date.today()

    # -------------------------
    # CURRENT STREAK
    # -------------------------

    latest = dates[0]

    if latest < today - timedelta(days=1):

        current_streak = 0

    else:

        current_streak = 1

        expected_date = latest - timedelta(days=1)

        for d in dates[1:]:

            if d == expected_date:

                current_streak += 1

                expected_date -= timedelta(days=1)

            else:

                break

    # -------------------------
    # LONGEST STREAK
    # -------------------------

    longest_streak = 1
    temp_streak = 1

    for i in range(1, len(dates)):

        difference = dates[i - 1] - dates[i]

        if difference.days == 1:

            temp_streak += 1

        else:

            temp_streak = 1

        if temp_streak > longest_streak:

            longest_streak = temp_streak

    return current_streak, longest_streak