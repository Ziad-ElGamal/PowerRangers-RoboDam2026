# tariff.py


# --------------------------------------------------
# Electricity tariff configuration
# --------------------------------------------------

# IMPORTANT:
# Replace these placeholder values with the
# official tariff rates used by the project.

TARIFF_TIERS = [
    {
        "limit_kwh": 50,
        "rate_egp_per_kwh": 0.68
    },
    {
        "limit_kwh": 100,
        "rate_egp_per_kwh": 0.87
    },
    {
        "limit_kwh": 200,
        "rate_egp_per_kwh": 1.06
    },
    {
        "limit_kwh": 350,
        "rate_egp_per_kwh": 1.74
    },
    {
        "limit_kwh": 650,
        "rate_egp_per_kwh": 2.18
    },
    {
        "limit_kwh": 1000,
        "rate_egp_per_kwh": 2.35
    },
    {
        "limit_kwh": float("inf"),
        "rate_egp_per_kwh": 2.89
    }
]


# --------------------------------------------------
# Calculate cost for a given amount of energy
# --------------------------------------------------

def calculate_cost(energy_kwh):
    """
    Calculate electricity cost based on
    cumulative tier consumption.

    Parameters:
        energy_kwh (float):
            Total electricity consumed.

    Returns:
        float:
            Estimated cost in EGP.
    """

    if energy_kwh <= 0:
        return 0.0


    remaining_energy = energy_kwh
    previous_limit = 0
    total_cost = 0.0


    for tier in TARIFF_TIERS:

        tier_limit = tier["limit_kwh"]
        rate = tier["rate_egp_per_kwh"]


        if tier_limit == float("inf"):

            tier_energy = remaining_energy

        else:

            tier_size = tier_limit - previous_limit

            tier_energy = min(
                remaining_energy,
                tier_size
            )


        total_cost += tier_energy * rate


        remaining_energy -= tier_energy


        if remaining_energy <= 0:
            break


        previous_limit = tier_limit


    return total_cost


# --------------------------------------------------
# Calculate cost of NEW consumption
# --------------------------------------------------

def calculate_marginal_cost(
    previous_kwh,
    additional_kwh
):
    """
    Calculate the cost of additional electricity
    consumed after previous_kwh has already been used.

    Example:

        Previous consumption = 75 kWh
        Additional usage    = 2 kWh

    Only the cost of those additional 2 kWh
    is returned.
    """

    if additional_kwh <= 0:
        return 0.0

    previous_cost = calculate_cost(
        previous_kwh
    )

    new_cost = calculate_cost(
        previous_kwh + additional_kwh
    )

    return new_cost - previous_cost


# --------------------------------------------------
# Test
# --------------------------------------------------

if __name__ == "__main__":

    test_values = [
        10,
        50,
        75,
        150,
        300
    ]

    print("Total costs:")
    print("----------------")

    for energy in test_values:
        cost = calculate_cost(
            energy
        )

        print(
            f"{energy} kWh -> "
            f"{cost:.2f} EGP"
        )

    print("\nMarginal cost tests:")
    print("--------------------")

    tests = [
        (0, 10),
        (50, 10),
        (75, 2),
        (100, 10),
        (200, 10)
    ]

    for previous_kwh, additional_kwh in tests:
        cost = calculate_marginal_cost(
            previous_kwh,
            additional_kwh
        )

        print(
            f"Previous: {previous_kwh} kWh | "
            f"Additional: {additional_kwh} kWh | "
            f"Cost: {cost:.2f} EGP"
        )