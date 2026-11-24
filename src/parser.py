from pathlib import Path
from typing import Any
from enum import StrEnum
from pydantic import BaseModel, Field, ValidationError, model_validator, field_validator

import re
from pydantic_core import PydanticCustomError


GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


class SyntaxErrorList(Exception):
    def __init__(self, err_list: list[SyntaxError]):
        self.err_list = err_list
        self.message = f"{RED}{BOLD}Caught {len(err_list)} Syntax Errors.{RESET}"
        super().__init__(self.message)


class SyntaxError(Exception):
    def __init__(self, index: int | None, input: str | None, type: str, message: str):
        super().__init__()
        self.index = index
        self.input = input
        self.type = type
        self.message = message

    def __str__(self) -> str:
        if self.index == None:
            return(
                F"{BOLD}{RED}  > Absent data:\n{RESET}"
                f"          {BOLD}Type:     {RESET}{self.type}\n"
                f"          {BOLD}Message:  {RESET}{self.message}\n"
            )

        return(
            f"{BOLD}{RED}  > Line {self.index} -> {RESET}{BOLD}'{self.input}'{RESET}\n"
            f"          Type:     {RESET}{self.type}\n"
            f"          Message:  {RESET}{self.message}\n"
        )


class SyntaxParser:

    VALID_KEYS = ("nb_drones", "start_hub", "end_hub", "hub", "connection")
    UNIQUE_KEYS = ("nb_drones", "start_hub", "end_hub")
    ZONE_KEYS = ("start_hub", "end_hub", "hub")

    PATTERNS = {
        "key_value": r"""
            (?P<key>\w+)       # Key
            :[ ]               # Colon followed by one space
            (?P<value>[^:]*) # Non-empty value without additional colons
        """,
        "nb_drones": r"""
            (?P<nb_drones>\d+) # Number of drones
        """,
        "zone": r"""
            (?P<name>\S+)      # Zone name
            [ ]
            (?P<x>[^\s\[\]]+)  # X coordinate
            [ ]
            (?P<y>[^\s\[\]]+)  # Y coordinate
            (?:                # Optional metadata
                [ ]
                \[
                (?P<metadata>[^\[\]]*)
                \]
            )?
        """,
        "connection": r"""
            (?P<start>[^-\s]+) # Starting zone
            -
            (?P<end>[^-\s]+)   # Ending zone
            (?:                # Optional metadata
                [ ]
                \[
                (?P<metadata>.*)
                \]
            )?
        """,
    }

    FORMATS = {
        "nb_drones": "nb_drones: <positive_integer>",
        "zone": "<name> <x> <y> [metadata]",
        "connection": "<zone1>-<zone2> [metadata]",
    }

    def __init__(self, lines: list[str]):
        self._lines = lines
        self._raw_data: dict[str, Any] = {}
        self._nb_drones: int = 0
        self._zones: list[Zone]
        self._start_zone: Zone = None
        self._end_zone: Zone = None

        self._hubs: list[tuple[int, dict[str, Any]]] = []
        self._connections: list[tuple[int, dict[str, Any]]] = []
        self._errors_list: list[SyntaxError] = []
        self._seen_keys: set[str] = set()
        self._seen_zones: set[str] = set()

    @staticmethod
    def _match_value(
                key: str,
                value: str,
                index: int
            ) -> dict[str, Any]:

        pattern_key = "zone" if key in SyntaxParser.ZONE_KEYS else key

        match = re.fullmatch(
            SyntaxParser.PATTERNS[pattern_key],
            value,
            re.VERBOSE
        )

        if match is None:
            raise SyntaxError(
                index=index,
                input=f"{key}: {value}",
                type="formatting",
                message=f"Invalid {key} format. Expected {SyntaxParser.FORMATS[pattern_key]}"
            )

        return match.groupdict()

    def _validate_pair_structure(
                            self,
                            line: str,
                            index: int
                        ) -> dict[str, Any]:

        # Check structure
        pair = re.fullmatch(
                    SyntaxParser.PATTERNS["key_value"],
                    line,
                    re.VERBOSE
                )

        if pair is None:
            raise SyntaxError(
                index=index,
                input=line,
                type="formatting",
                message="Expected 'key: value' format"
            )

        # Check if key is valid
        key, value = pair["key"], pair["value"]
        if key not in SyntaxParser.VALID_KEYS:
            raise SyntaxError(
                            index=index,
                            input=line,
                            type="invalid_key",
                            message=f"Allowed keys = {SyntaxParser.VALID_KEYS}"
                        )

        # Check if key is unique
        if key in SyntaxParser.UNIQUE_KEYS:
            if key in self._seen_keys:
                    self._errors_list.append(
                        SyntaxError(
                            index=index,
                            input=line,
                            type="duplicate_key",
                            message=f"{key} must be declared only once"
                        )
                    )

        self._seen_keys.add(key) # if it's unique and it hasnt been seen
        return key, value

    def _validate_zone(
                    self,
                    key: str,
                    value: str,
                    index: int
                ) -> Zone:

        try:
            data = SyntaxParser._match_value(key, value, index) #groupdict

        except SyntaxError as error:
            self._errors_list.append(error)

        # Zone duplicates are not allowed
        if data["name"] in self._seen_zones:
            self._errors_list.append(
                SyntaxError(
                    index=index,
                    input=value,
                    type="duplicate_zone",
                    message=f"Zone '{data["name"]}' is already defined"
                )
            )

        self._seen_zones.add(data["name"])
        zone = None

        try:
            zone = Zone(**data)

        except ValidationError as pydantic:
            message = ""
            for error in pydantic.errors():
                loc: str = error["loc"][0]
                msg = error["msg"]
                tmp = " -> ".join([loc, msg])
                print(tmp)
                message = "\n                ".join([message, tmp])
            self._errors_list.append(
                SyntaxError(
                    index=index,
                    input=value,
                    type="pydantic",
                    message=f"{message}"
                )
            )

        return zone


    def validate_data(self, lines: list[str]) -> dict[str, Any]:
        first_line = 0

        for index, line in enumerate(lines, start=1):

            # Ommit comments or empty lines
            if line.startswith("#") or not line:
                continue

            first_line += 1

            # Validate key-value structure
            try:
                key, value = self._validate_pair_structure(line, index)
            except SyntaxError as error:
                self._errors_list.append(error)
                continue

            # Check special condition for nb of drones (placement)
            if key == "nb_drones" and first_line != 1:
                    self._errors_list.append(
                        SyntaxError(
                            index=index,
                            input=line,
                            type="line_placement",
                            message="nb_drones must be declared in the first line"
                        )
                    )
                    continue

            # Validate the value and extract all the parts using the patterns
            try:
                data = SyntaxParser._match_value(key, value, index) #groupdict
            except SyntaxError as error:
                self._errors_list.append(error)
                continue

            # Store nb_drones
            if key == "nb_drones":
                self._nb_drones = data["nb_drones"]

            # Store zones
            elif key in SyntaxParser.ZONE_KEYS:
                print(index)
                zone = self._validate_zone(key, value, index)
                if zone is None:
                    continue
                else:
                    if key == "start_hub":
                        self._start_zone = zone
                    elif key == "end_hub":
                        self._end_zone = zone

            # Store connection
            elif key == "connection":

                start, end = data["start"], data["end"]
                if start not in self._seen_zones or end not in self._seen_zones:
                    self._errors_list.append(
                        SyntaxError(
                            index=index,
                            input=line,
                            type="undefined_zones",
                            message=f"Connections must link previously defined zones"
                        )
                    )
                    continue

                self._connections.append((index, data))

        # Check mandatory keys
        missing_keys = set(SyntaxParser.UNIQUE_KEYS) - self._seen_keys

        if missing_keys:
            self._errors_list.append(
                SyntaxError(
                    index=None,
                    input=None,
                    type="missing_keys",
                    message=f"Missing mandatory keys: {missing_keys}"
                )
            )

        # If errors were found, they are raised using a custom error class
        if self._errors_list:
            raise SyntaxErrorList(err_list=self._errors_list)

        # If no errors were found
        self._raw_data["hubs"] = self._hubs #adding hubs to the dict
        self._raw_data["connections"] = self._connections #adding connections to the dict

        return self._raw_data


class ZoneTypes(StrEnum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class ZoneMetadata(BaseModel):
    zone: ZoneTypes = ZoneTypes.NORMAL
    color: str = "none"
    max_drones: int = Field(default=1, gt=0)

    model_config = {"extra": "forbid"} #reject unknown metadata properties
    @model_validator(mode="before")
    @classmethod
    # Transforms the string into a dict before field validation
    def parse_metadata(cls, metadata: Any): #Any -> str | empty dict
        if isinstance(metadata, str):

            if metadata!= " ".join(metadata.split()):
                    raise PydanticCustomError(
                        "invalid_spacing",
                        "Metadata must have no leading, trailing, or repeated spaces"
                        )

            tags = {} # to keep track of the tags

            for tag in metadata.split():
                key, separator, value = tag.partition("=") #partition method splits the str into exactly three parts

                if not separator or not key or not value:
                    raise PydanticCustomError(
                        "invalid_structure",
                        f"Invalid metadata: '{tag}'"
                        )

                if key in tags:
                    raise PydanticCustomError(
                        "duplicate_tag",
                        f"Duplicate metadata tag: '{key}'")

                tags[key] = value

            return tags #if it was a string, it will get sent for pydantic validation

        return metadata #if it was an empty dict it will get filled with the default values


class Zone(BaseModel):
    name: str
    x: int
    y: int
    metadata: ZoneMetadata = Field(default_factory=ZoneMetadata) #no metadata field triggers the creation of ZoneMetadata() thanks to default_factory

    # If metadata=None, we need to have the default values
    @field_validator("metadata", mode="before")
    @classmethod
    def handle_missing_metadata(cls, data: str | None):
        if data is None:
            return {} #sending an empty dict to the ZoneMetadata will fill the empty dict with the defaults
        return data


class Connection(BaseModel):
    start: str
    end: str
    metadata: str | None


class MapData(BaseModel):
    nb_drones: int = Field(gt=0)
    start_hub: Zone
    end_hub: Zone
    hubs: list[Zone]
    connections: list[Connection]

    @model_validator(mode="before")
    @classmethod
    def process_tuple(cls, data: dict[str, Any]):
        # nb_drones: (index, data)
        nb_drones = data["nb_drones"][1]

        # start_hub: (index, {name, x, y, metadata})
        start_hub = data["start_hub"][1]

        # end_hub: (index, {name, x, y, metadata})
        end_hub = data["end_hub"][1]

        # hubs: [(index, {name, x, y, metadata})]
        hubs = [value for index, value in data["hubs"]]

        # connections: [(index, {start, end, metadata})]
        connections = [value for index, value in data["connections"]]

        return {
        "nb_drones": nb_drones,
        "start_hub": start_hub,
        "end_hub": end_hub,
        "hubs": hubs,
        "connections": connections
        }



class Parser(SyntaxParser):
    def __init__(self, file_path: Path):
        self.file_path: Path = file_path
        self.lines: list[str] = self.get_lines()
        super().__init__(lines=self.lines)

    def get_lines(self) -> list[str]:
        file = open(self.file_path, "r")
        lines = file.read().splitlines()
        file.close()
        return lines

    def get_data(self) -> MapData:
        raw_data: dict[str, Any] = self.validate_data(self.lines)
        print(raw_data)
        # map_data = MapData(**raw_data)
        return raw_data
