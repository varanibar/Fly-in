from pathlib import Path
from typing import Any
from enum import StrEnum
from pydantic import BaseModel, Field, ValidationError, model_validator

from pydantic_core import PydanticCustomError

class FileParserError(Exception):
    pass

class FileParser:

    @staticmethod
    def read_file(path: Path) -> list[str]:
        file = open(path, "r")
        lines = file.read().splitlines()
        file.close()
        return lines

    @staticmethod
    def _get_zone(value: str) -> str:
        parts = value.split()
        return parts[0]

    @staticmethod
    def _get_connections(value: str) -> tuple[str, str]:
        parts = value.split()
        start, end = parts[0].split("-")
        return start, end

    @staticmethod
    def get_raw_data(lines: list[str]) -> dict[str, Any]:
        valid_keys = ["nb_drones", "start_hub", "end_hub", "hub", "connection"]
        unique_keys = ["nb_drones", "start_hub", "end_hub"]
        zone_keys = ["start_hub", "end_hub", "hub"]

        raw_data: dict[str, Any] = {}
        syntax_errors: list[str] = []

        first_line = 0
        hubs: list[str] = []
        zones: list[str] = []
        connections: list[str] = []
        for index, line in enumerate(lines, start=1):

            if line.startswith("#") or not line:
                continue

            elif line.count(":") != 1:
                first_line += 1
                syntax_errors.append(f"Line {index}: expected 'key: value'")
                continue

            first_line += 1

            key, value = line.split(":")

            value = value.strip(" ")
            if key not in valid_keys:
                syntax_errors.append(f"Line {index}: invalid key")
                continue

            if not value:
                syntax_errors.append(f"Line {index}: 'value' must not be empty")
                continue

            if key in unique_keys and key not in raw_data:
                if key == "nb_drones" and first_line != 1:
                    syntax_errors.append(f"Line {index}: nb_drones must declared be the first line")
                    continue
                else:
                    raw_data[key] = value

            elif key in unique_keys and key in raw_data:
                syntax_errors.append(f"Line {index}: {key} must be a unique value")
                continue

            if key in zone_keys:
                zones.append(FileParser._get_zone(value))
                if key == "hub":
                    hubs.append(value)

            elif key == "connection":
                if value.count("-") != 1:
                    syntax_errors.append(f"Line {index}: expected <zone1>-<zone2>")
                    continue
                start, end = FileParser._get_connections(value)
                if not start or not end:
                    syntax_errors.append(f"Line {index}: Connection zones must not be empty")
                    continue
                elif start not in zones or end not in zones:
                    syntax_errors.append(f"Line {index}: Connections must link only previously defined zones using connection")
                    continue
                else:
                    connections.append(value)

        missing_keys = set(unique_keys) - raw_data.keys()
        if missing_keys:
            syntax_errors.append(f"Missing mandatory keys: {missing_keys}")

        if syntax_errors:
            raise FileParserError(syntax_errors)
        else:
            raw_data["hubs"] = hubs
            raw_data["connections"] = connections
            return raw_data

class ZoneTypes(StrEnum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Zones(BaseModel):
    name: str
    x: int
    y: int
    metadata: str

    @model_validator(mode="before")
    @classmethod
    def get_parts(cls, data: str) -> dict[str, Any]:
        if "[" in data:
            split_data = data.split(" [", maxsplit=1)
            name_x_y = split_data[0]
            metadata = "[" + split_data[1]
        else:
            raise PydanticCustomError(
                "zone_format",
                "Not enough arguments, metadata not found"
                )

        parts = name_x_y.split(maxsplit=2)
        print(f"      Parsing:")
        print(f"         name_x_y: {name_x_y}")
        print(f"         metadata: {metadata}")
        print(f"         parts:    {parts}")
        print(f"         len:      {len(parts)}")
        print(f"      Result:",end="")

        if len(parts) != 3:
            raise PydanticCustomError(
                "zone_format",
                "Not enough arguments, expected <name> <x> <y> [metadata]"
                )

        return {
            "name": parts[0],
            "x": parts[1],
            "y": parts[2],
            "metadata": metadata
        }


class Connections:
    pass

class ConfigData(BaseModel):
    nb_drones: int = Field(ge = 1)
    start_hub: str
    end_hub: str
    hubs: list[Zones]
    connections: list[str]

    def show(self) -> None:
        print(
            f"\nConfig data:\n"
            f" nb_drones: {self.nb_drones}\n"
            f" start_hub: {self.start_hub}\n"
            f" end_hub:   {self.end_hub}\n"
        )
        print(" hubs:")
        for hub in self.hubs:
            print(f"  {hub}")

        print("\nconnections:")
        for connection in self.connections:
            print(f"  {connection}")


def parsing(file_path: Path) -> bool:
    try:
        print("======READING FILE=======")
        lines = FileParser.read_file(file_path)
        print("Reading succesful!")
    except Exception as error:
        print(f"File Handling Error: {error}")
        return False

    else:
        try:
            print("======GETTING RAW DATA=======")
            print("Parsing file....")
            raw_data = FileParser.get_raw_data(lines)
            print(raw_data)
            print("raw data succesfully obtained!")

        except FileParserError as syntax_error:
            print("Syntax errors, fix before running again:")
            for err in syntax_error.args[0]:
                print(err)
            return False

        else:
            try:
                print("======PYDANTIC MODEL=======")
                config_data = ConfigData(**raw_data)
                config_data.show()

            except Exception as pydantic_error:
                print(pydantic_error)
                return False

            else:
                return True

if __name__ == "__main__":
    file_path = Path("/home/varaniba/CODAM_CORE/Fly-in/01_linear_path.txt")
    if parsing(file_path):
        result = "Succesful"
    else:
        result = "Failed"

    print(f"\nParsing: {result}")




