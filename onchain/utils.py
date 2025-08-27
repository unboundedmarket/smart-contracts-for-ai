from opshin.ledger.interval import *

def compare_upper_lower_bound(a: UpperBoundPOSIXTime, b: LowerBoundPOSIXTime) -> int:
    # a < b: 1
    # a == b: 0
    # a > b: -1
    result = compare_extended(a.limit, b.limit)
    if result == 0:
        a_closed = get_bool(a.closed)
        b_closed = get_bool(b.closed)
        if a_closed and b_closed:
            result = 0
        else:
            result = 1
    return result

def after_ext(a: POSIXTimeRange, b: ExtendedPOSIXTime) -> bool:
    """Returns whether all of a is after b. b |---a---|"""
    return (
        compare_upper_lower_bound(UpperBoundPOSIXTime(b, TrueData()), a.lower_bound)
        == 1
    )
