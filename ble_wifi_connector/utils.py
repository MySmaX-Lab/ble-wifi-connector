import getmac


def get_mac_address(interface: str = None) -> str:
    mac_address = getmac.get_mac_address(interface)

    if mac_address:
        mac_address = mac_address.replace(':', '').upper()
        return mac_address
    else:
        return None
