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
    def parse_metadata(cls, metadata: Any) -> str | Any: #Any aswell bc empty dict
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
    def handle_missing_metadata(cls, data: str | None) -> str | Any:
        if data is None:
            return {} #sending an empty dict to the ZoneMetadata will fill the empty dict with the defaults
        return data


class Connection(BaseModel):
    start: str
    end: str
    metadata: str | None


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
        self._zones: list[Zone] = []
        self._connections: list[Connection] = []
        self._start_zone: Zone
        self._end_zone: Zone

        self._hubs: list[tuple[int, dict[str, Any]]] = []
        self.connections: list[tuple[int, dict[str, Any]]] = []
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
                        ) -> dict[str, Any] | None:

        # Get pair by matching to the regex key: value pattern
        # Returns a dict containing the key and the value
        pair = re.fullmatch(
                    SyntaxParser.PATTERNS["key_value"],
                    line,
                    re.VERBOSE
                )

        # If it is not in a valid pair structure, it returns None
        if pair is None:
            self._errors_list.append(
                    SyntaxError(
                        index=index,
                        input=line,
                        type="formatting",
                        message="Expected 'key: value' format"
                    )
            )
            return None

        # Check if key is valid
        key = pair["key"]
        if key not in SyntaxParser.VALID_KEYS:
            self._errors_list.append(
                SyntaxError(
                    index=index,
                    input=line,
                    type="invalid_key",
                    message=f"Allowed keys = {SyntaxParser.VALID_KEYS}"
                )
            )
            return None

        # Check for duplicates
        if key in SyntaxParser.UNIQUE_KEYS and \
            key in self._seen_keys:
                self._errors_list.append(
                    SyntaxError(
                        index=index,
                        input=line,
                        type="duplicate_key",
                        message=f"{key} must be declared only once"
                    )
                )
                return None

        self._seen_keys.add(key) # if it's unique and it hasnt been seen
        return pair.groupdict()

    def _validate_zone(
                    self,
                    key: str,
                    value: str,
                    index: int
                ) -> Zone | None:

        # Try to get the data dict using regex
        try:
            data = SyntaxParser._match_value(key, value, index) #groupdict

        except SyntaxError as formatting_err:
            self._errors_list.append(formatting_err)
            return None

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
            return None

        self._seen_zones.add(data["name"])

        # Creating the zone with the Zone basemodel
        try:
            zone = Zone(**data)
        except ValidationError as pydantic:
            message = ""
            for error in pydantic.errors():
                loc = str(error["loc"][0])
                msg = str(error["msg"])
                tmp = " -> ".join([loc, msg])
                message = "\n                ".join([message, tmp])
            self._errors_list.append(
                SyntaxError(
                    index=index,
                    input=value,
                    type="pydantic",
                    message=f"{message}"
                )
            )
            return None

        return zone

    def _validate_connection(
                        self,
                        key: str,
                        value: str,
                        index: int
                    ) -> Connection | None:
        # Try to get the data dict using regex
        try:
            data = SyntaxParser._match_value(key, value, index) #groupdict
        except SyntaxError as formatting_err:
            self._errors_list.append(formatting_err)
            return None

        start, end = data["start"], data["end"]
        if start not in self._seen_zones or end not in self._seen_zones:
            self._errors_list.append(
                SyntaxError(
                    index=index,
                    input=value,
                    type="undefined_zones",
                    message=f"Connections must link previously defined zones"
                )
            )
            return None

        try:
            connection = Connection(**data)
        except ValidationError as pydantic:
            message = ""
            for error in pydantic.errors():
                loc = str(error["loc"][0])
                msg = str(error["msg"])
                tmp = " -> ".join([loc, msg])
                message = "\n                ".join([message, tmp])
            self._errors_list.append(
                SyntaxError(
                    index=index,
                    input=value,
                    type="pydantic",
                    message=f"{message}"
                )
            )
            return None

        return connection

    def _validate_nb_drones(
                        self,
                        line: str,
                        pair: str,
                        index: int,
                        is_first: bool
                    ) -> int | None:

        value = pair["value"]

        try:
            data = SyntaxParser._match_value("nb_drones", value, index) #groupdict
        except SyntaxError as formatting_err:
            self._errors_list.append(formatting_err)
            return None

        if is_first != True:
            self._errors_list.append(
                        SyntaxError(
                            index=index,
                            input=line,
                            type="line_placement",
                            message="nb_drones must be declared in the first line"
                        )
            )
            return None

        return data["nb_drones"]


    def validate_data(self, lines: list[str]) -> dict[str, Any]:
        is_first = True

        for index, line in enumerate(lines, start=1):

            # Ommit comments or empty lines
            if line.startswith("#") or not line:
                continue

            # Validate key-value structure
            pair = self._validate_pair_structure(line, index)
            if pair is None:
                continue

            key, value = pair["key"], pair["value"]

            # nb_drones
            if key == "nb_drones":
                nb_drones = self._validate_nb_drones(line, pair, index, is_first)
                if nb_drones is None:
                    continue
                else:
                    self._nb_drones = nb_drones
            is_first = False

            # zones
            if key in SyntaxParser.ZONE_KEYS:
                zone = self._validate_zone(key, value, index)
                if zone is None:
                    continue
                else:
                    if key == "start_hub":
                        self._start_zone = zone
                    elif key == "end_hub":
                        self._end_zone = zone
                    else:
                        self._zones.append(zone)

            # connections
            elif key == "connection":
                connection = self._validate_connection(key, value, index)
                if zone is None:
                    continue
                self.connections.append(connection)


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
        self._raw_data["hubs"] = self._zones #adding hubs to the dict
        self._raw_data["connections"] = self._connections #adding connections to the dict

        return self._raw_data


class MapData(BaseModel):
    nb_drones: int = Field(gt=0)
    start_hub: Zone
    end_hub: Zone
    hubs: list[Zone]
    connections: list[Connection]

    @model_validator(mode="before")
    @classmethod
    def process_tuple(cls, data: dict[str, Any]) -> dict[str, Any]:
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

    def get_data(self) -> Any:
        raw_data: dict[str, Any] = self.validate_data(self.lines)
        print(raw_data)
        # map_data = MapData(**raw_data)
        return raw_data
