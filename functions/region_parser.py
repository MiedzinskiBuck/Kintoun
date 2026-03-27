from functools import lru_cache


@lru_cache(maxsize=1)
def get_regions():
    with open("data/regions.txt", "r") as regions_file:
        return regions_file.read().splitlines()


def select_regions():
    regions = get_regions()
    print("[+] Available Regions...\n")

    for region in regions:
        print("- {}".format(region))
    selected_region = input("\n[+] Select region (Default All): ")

    if not selected_region:
        selected_regions = []
        for region in regions:
            selected_regions.append(region)
        return selected_regions

    if selected_region not in regions:
        print("[-] Invalid Region...")
        return False

    selected_region = [selected_region]
    return selected_region


class Region():
    def __new__(self):
        return select_regions()
