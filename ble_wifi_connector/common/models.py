from dataclasses import dataclass


@dataclass
class DiscoveredBleDevice:
    name: str
    address: str

    def __str__(self):
        return f'{self.name} | {self.address}'

    def __repr__(self):
        return self.__str__()