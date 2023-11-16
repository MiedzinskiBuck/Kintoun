class Region():
    def __new__(self):
        regions_file = open("data/regions.txt", "r")
        regions = regions_file.read().splitlines()
        print("[+] Available Regions...\n")

        for region in regions:
            print("- {}".format(region))
        selected_region = input("\n[+] Select region (Default All): ")

        if not selected_region:
            selected_regions = []
            for region in regions:
                selected_regions.append(region)
            return selected_regions

        elif selected_region not in regions:
            print("[-] Invalid Region...")
            return False

        else:
            selected_region = [selected_region]
            return selected_region