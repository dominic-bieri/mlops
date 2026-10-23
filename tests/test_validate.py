from datetime import date

import pandas as pd
import pytest
from fake_data import make_data

from sp500_vol.features.validate import validate_spy, validate_vix


def test_valid_data_passes() -> None:
    sp500, vix = make_data()

    validate_spy(sp500)
    validate_vix(vix)


@pytest.mark.parametrize(
    ("column", "value", "reason"),
    [
        ("close", None, "missing value"),
        ("open", 0.0, "price not above 0"),
        ("div_cash", -1.0, "negative dividend"),
        ("close", 1000.0, "outside low and high"),
    ],
)
def test_bad_spy_row_fails_with_its_date(column: str, value: float | None, reason: str) -> None:
    sp500, _ = make_data()
    sp500.loc[10, column] = value

    with pytest.raises(ValueError, match=reason) as error:
        validate_spy(sp500)

    assert str(sp500.loc[10, "date"]) in str(error.value)


def test_duplicate_spy_date_fails() -> None:
    sp500, _ = make_data()
    sp500 = pd.concat([sp500, sp500.tail(1)])

    with pytest.raises(ValueError, match="duplicate date"):
        validate_spy(sp500)


@pytest.mark.parametrize(("value", "reason"), [(None, "missing value"), (0.0, "not above 0")])
def test_bad_vix_value_fails(value: float | None, reason: str) -> None:
    vix = pd.DataFrame({"date": [date(2024, 3, 14), date(2024, 3, 15)], "close": [13.0, value]})

    with pytest.raises(ValueError, match=reason):
        validate_vix(vix)
