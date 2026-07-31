from safety import is_restricted
from tools import (
    check_inventory,
    check_crop_status,
    request_human_approval,
)


def process_request(user_request):
    restricted, chemical = is_restricted(user_request)

    if restricted:
        return (
            f"⛔ STOP\n"
            f"{chemical} is a restricted chemical.\n"
            f"{request_human_approval()}"
        )

    request = user_request.lower()

    if "inventory" in request:
        return check_inventory()

    if "crop" in request:
        return check_crop_status()

    return "I don't understand your request."


def main():
    print("=" * 50)
    print("🌱 Greenfield AI Assistant")
    print("=" * 50)

    user_request = input("\nEnter your request: ")

    response = process_request(user_request)

    print("\nAssistant:")
    print(response)


if __name__ == "__main__":
    main()
    