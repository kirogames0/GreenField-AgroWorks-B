RESTRICTED_CHEMICALS = [
    "Paraquat",
    "Restricted Herbicide",
    "Toxic Spray"
]


def is_restricted(request: str):
    request = request.lower()

    for chemical in RESTRICTED_CHEMICALS:
        if chemical.lower() in request:
            return True, chemical

    return False, None