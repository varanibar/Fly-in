from pathlib import Path
from typing import Any
from enum import StrEnum
from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    model_validator,
    field_validator
    )
import re
from pydantic_core import PydanticCustomError
import webcolors

# Project modules
from .errors import SyntaxError, SyntaxErrorList


class ZoneTypes(StrEnum):
    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class ZoneMetadata(BaseModel):
    zone: ZoneTypes = ZoneTypes.NORMAL
    color: webcolors.IntegerRGB = Field(default=None)
    max_drones: int = Field(default=1, gt=0)

    model_config = {"extra": "forbid"}  # reject unknown metadata properties

    @field_validator("color", mode="before")
    def get_rgb(cls, color: str) -> webcolors.IntegerRGB:

        try:
            rgb = webcolors.name_to_rgb(color)

        except Exception as err:
            raise PydanticCustomError(
                    "invalid_color",
                    f"'{color}' is not valid"
                    )

        return rgb


    @model_validator(mode="before")
    @classmethod
    def get_tags(cls, metadata: Any) -> str | Any:
        #it can be a str or an empty dict (bc handle_missing_metadata())
        if isinstance(metadata, str):
            # if its a string, it gets parsed and if it succeeds it returns
            # a dict containing the tags ready for pydantic validation

            if metadata != " ".join(metadata.split()):
                raise PydanticCustomError(
                    "invalid_spacing",
                    "Metadata must have no leading, "
                    "trailing, or repeated spaces"
                    )

            tags = {}  # to keep track of the tags

            for tag in metadata.split():
                key, separator, value = tag.partition("=")

                if not separator or not key or not value:
                    raise PydanticCustomError(
                        "invalid_tag",
                        f"Invalid metadata tag: '{tag}'"
                        )

                if key in tags:
                    raise PydanticCustomError(
                        "duplicate_tag",
                        f"Duplicate metadata tag: '{key}'")

                tags[key] = value

            return tags  # dict containing the tags, ready for field validation

        return metadata  # an empty dict, gets filled with the default values



class Zone(BaseModel):
    name: str = Field(pattern=r"^[^-\s]+$")
    x: int
    y: int
    metadata: ZoneMetadata

    # If metadata=None, we need to have the default values
    @field_validator("metadata", mode="before")
    @classmethod
    def handle_missing_metadata(cls, metadata: str | None) -> str | Any:
        if metadata is None: #In case its None, we need the default values
            return {}  # an empty dict, gets filled with the default values
        return metadata

    @property
    def zone_type(self) -> str:
        return self.metadata.zone

    @property
    def color(self) -> webcolors.IntegerRGB:
        return self.metadata.color

    @property
    def max_drones(self) -> int:
        return self.metadata.max_drones


class Connection(BaseModel):
    start: str
    end: str
    max_link_capacity: int = Field(default=1, gt=0)

    @model_validator(mode="before")
    @classmethod
    def parse_metadata(cls, data: dict[str, Any]) -> dict[str, Any]:
        metadata = data.pop("metadata")

        if metadata is not None:

            if metadata != " ".join(metadata.split()):
                raise PydanticCustomError(
                    "invalid_spacing",
                    "Metadata must have no leading, "
                    "trailing, or repeated spaces"
                    )

            if len(metadata.split()) > 1:
                raise PydanticCustomError(
                    "too_many_tags",
                    "Only one tag allowed"
                    )

            key, separator, value = metadata.partition("=")

            if not separator or not key or not value:
                raise PydanticCustomError(
                    "invalid_structure",
                    f"Expected '[max_link_capacity=<positive_integer>]'"
                    )

            if key != "max_link_capacity":
                raise PydanticCustomError(
                    "invalid_tag",
                    f"Expected '[max_link_capacity=...]'"
                    )

            data[key] = value

        return data

    @model_validator(mode="after")
    def validate_start_end(self) -> "Connection":

        if self.start == self.end:
                raise PydanticCustomError(
                    "connection_zones",
                    f"Start zone and end zone can't be the same"
                    )

        return self


class Pattern:
    _PAIR = r"""
            [ ]*              # Zero or more spaces
            (?P<key>[\w]+)    # Any word character
            :[ ]+             # Colon followed by one or more spaces
            (?P<value>[^:]+)  # one or more chars except ':'
        """

    _NB_DRONES = r"""
            (?P<nb_drones>[+]?[\d]+) # zero or one of '+', one or more digits
            [ ]*               # Zero or more spaces
        """

    _ZONE = r"""
            (?P<name>\S+)      # one or more of any non-whitespace character
            [ ]+               # one or more spaces
            (?P<x>[^\s\[\]]+)  # A character except: any whitespace and []
            [ ]+               # one or more spaces
            (?P<y>[^\s\[\]]+)  # A character except: any whitespace and []
            (?:                # Optional metadata
                [ ]+           # One or more spaces
                \[             # '['
                (?P<metadata>[^\[\]]+) # one or more chars except []
                \]             # '['
            )?
            [ ]*               # Zero or more spaces
        """

    _CONNECTION = r"""
            (?P<start>[^-\s]+) # one or more chars except '-' and any whitespace
            -                  # dash
            (?P<end>[^-\s]+)   # one or more chars except '-' and any whitespace
            (?:                # Optional
                [ ]+           # One or more spaces
                \[             # '['
                (?P<metadata>[^\[\]]+) # one or more chars except []
                \]             # '['
            )?
            [ ]*               # Zero or more spaces
        """

    PATTERNS = {
        "pair": _PAIR,
        "nb_drones": _NB_DRONES,
        "zone": _ZONE,
        "connection": _CONNECTION,
    }

    @staticmethod
    def match_value(
                key: str,
                value: str,
                index: int
            ) -> dict[str, Any]:

        pattern_key = "zone" if key in SyntaxParser.ZONE_KEYS else key

        pattern = Pattern.PATTERNS[pattern_key]
        format = SyntaxParser.FORMATS[pattern_key]

        match = re.fullmatch(
            pattern,
            value,
            re.VERBOSE
        )

        if match is None:
            raise SyntaxError(
                index=index,
                input=f"{value}",
                type=f"invalid_{key}_format",
                message=f"Expected '{format}'"
            )

        return match.groupdict()


class SyntaxParser:

    VALID_KEYS = {"nb_drones", "start_hub", "end_hub", "hub", "connection"}
    UNIQUE_KEYS = {"nb_drones", "start_hub", "end_hub"}
    ZONE_KEYS = {"start_hub", "end_hub", "hub"}

    FORMATS = {
        "pair": "key: value",
        "nb_drones": "nb_drones: <positive_integer>",
        "zone": "hub: <name> <x> <y> [metadata]",
        "connection": "connection: <zone1>-<zone2> [metadata]",
    }

    def __init__(self, lines: list[str]):
        self._lines = lines
        self._raw_data: dict[str, Any] = {}
        self._nb_drones: int = 0
        self._zones: list[Zone] = []
        self._connections: list[Connection] = []
        self._start_zone: Zone
        self._end_zone: Zone

        self._errors_list: list[SyntaxError] = []
        self._seen_keys: set[str] = set()
        self._seen_zones: set[str] = set()
        self._seen_connections: set[frozenset[str]] = set()

    def _validate_pair_structure(
                            self,
                            line: str,
                            index: int
                        ) -> dict[str, Any] | None:

        pair = None

        try:
            pair = Pattern.match_value(
                                    key="pair",
                                    value=line,
                                    index=index
                                )

        except SyntaxError as formatting_err:
            self._errors_list.append(formatting_err)

        else:
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

            else:
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

                else:
                    self._seen_keys.add(key)

        return pair

    def _validate_nb_drones(
                        self,
                        pair: dict[str, Any],
                        index: int,
                        is_first: bool
                    ) -> int:

        value = pair["value"]
        nb_drones = 0

        try:
            data = Pattern.match_value(
                        key="nb_drones",
                        value=value,
                        index=index
                    )

        except SyntaxError as formatting_err:
            self._errors_list.append(formatting_err)

        else:
            nb_drones = int(data["nb_drones"])

            if nb_drones == 0:
                self._errors_list.append(
                    SyntaxError(
                        index=index,
                        input=f"nb_drones: {value}",
                        type="nb_drones",
                        message=("nb_drones must be "
                                    "more than 0")
                    )
                )

            if is_first is not True:
                self._errors_list.append(
                    SyntaxError(
                        index=index,
                        input=f"nb_drones: {value}",
                        type="line_placement",
                        message=("nb_drones must be "
                                    "declared in the first line")
                    )
                )

        return nb_drones

    def _validate_zone(
                    self,
                    pair: dict[str, Any],
                    index: int
                ) -> Zone | None:

        key, value = pair["key"], pair["value"]
        zone = None  # if Zone creation is unsuccesful, it will return None

        try:
            # data: name x y [metadata]
            data = Pattern.match_value(
                        key=key,
                        value=value,
                        index=index
                    )

        except SyntaxError as formatting_err:
            self._errors_list.append(formatting_err)

        else:
            # Duplicates
            if data["name"] in self._seen_zones:
                self._errors_list.append(
                    SyntaxError(
                        index=index,
                        input=value,
                        type="duplicate_zone",
                        message=f"Zone '{data["name"]}' is already defined"
                    )
                )

            else:
                self._seen_zones.add(data["name"])

                # Create Zone
                try:
                    zone = Zone(**data)

                except ValidationError as pydantic:
                    message = "Field validation errors"
                    connector = "\n                     - "
                    for error in pydantic.errors():
                        type = str(error["type"])
                        loc = ".".join(map(str, error["loc"]))
                        msg = str(error["msg"])

                        tmp = " -> ".join([type, loc, msg])
                        message = connector.join([message, tmp])

                    self._errors_list.append(
                        SyntaxError(
                            index=index,
                            input=value,
                            type="pydantic",
                            message=f"{message}"
                        )
                    )

        return zone

    def _validate_connection(
                        self,
                        pair: dict[str, Any],
                        index: int
                    ) -> Connection | None:

        err_list = self._errors_list
        key, value = pair["key"], pair["value"]
        connection = None

        try:
            data = Pattern.match_value(
                                key=key,
                                value=value,
                                index=index
                            )

        except SyntaxError as formatting_err:
            err_list.append(formatting_err)

        else:
            start, end = data["start"], data["end"]
            if start not in self._seen_zones or end not in self._seen_zones:
                err_list.append(
                    SyntaxError(
                        index=index,
                        input=value,
                        type="undefined_zones",
                        message=("Connections must link"
                                " previously defined zones")
                    )
                )

            else:
                try:
                    connection = Connection(**data)

                except ValidationError as pydantic:
                    message = "Field validation errors for connection:"
                    connector = "\n                     - "
                    for pydantic_err in pydantic.errors():
                        type = str(pydantic_err["type"])
                        loc = ".".join(map(str, pydantic_err["loc"]))
                        msg = str(pydantic_err["msg"])

                        tmp = " -> ".join([type, loc, msg])
                        message = connector.join([message, tmp])

                    err_list.append(
                        SyntaxError(
                            index=index,
                            input=value,
                            type="pydantic",
                            message=f"{message}"
                        )
                    )

                else:
                    #Duplicates
                    current = frozenset({connection.start, connection.end})

                    if current in self._seen_connections:
                        err_list.append(
                            SyntaxError(
                                index=index,
                                input=value,
                                type="duplicate_connection",
                                message=("Connections must be unique, "
                                        "a-b and b-a are considered duplicates")
                            )
                        )

                    else:
                        self._seen_connections.add(current)

        return connection

    def _check_missing_keys(self) -> None:
        missing_keys = SyntaxParser.UNIQUE_KEYS - self._seen_keys

        if missing_keys:
            self._errors_list.append(
                SyntaxError(
                    index=None,
                    input=None,
                    type="missing_keys",
                    message=f"Missing mandatory keys: {missing_keys}"
                )
            )

    def _validate_data(self, lines: list[str]) -> dict[str, Any]:
        is_first = True

        for index, line in enumerate(lines, start=1):

            # Ommit comments or empty lines
            if line.startswith("#") or not line:
                continue

            # Validate key-value structure
            pair = self._validate_pair_structure(line, index)
            if pair is None:
                continue
            key = pair["key"]

            # nb_drones
            if key == "nb_drones":
                nb_drones = self._validate_nb_drones(pair, index, is_first)
                is_first = False
                if nb_drones == 0:
                    continue
                else:
                    self._nb_drones = nb_drones
            is_first = False

            # zones
            if key in SyntaxParser.ZONE_KEYS:
                zone = self._validate_zone(pair, index)
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
                connection = self._validate_connection(pair, index)
                if connection is None:
                    continue
                else:
                    self._connections.append(connection)

        # Check missing keys
        self._check_missing_keys()

        # If errors were found, they are raised using a custom error class
        if self._errors_list:
            raise SyntaxErrorList(err_list=self._errors_list)

        # If no errors were found
        self._raw_data["nb_drones"] = self._nb_drones
        self._raw_data["start_zone"] = self._start_zone
        self._raw_data["end_zone"] = self._end_zone
        self._raw_data["zones"] = self._zones
        self._raw_data["connections"] = self._connections

        return self._raw_data


class MapData(BaseModel):
    nb_drones: int = Field(gt=0)
    start_zone: Zone
    end_zone: Zone
    zones: list[Zone]
    connections: list[Connection]

    def show(self) -> None:
        print(f"nb_drones = {self.nb_drones}")
        start = self.start_zone
        end = self.end_zone
        print()
        print(f"start_zone = {start.name} {start.x} {start.y} {start.metadata}")
        print(f"end_zone = {end.name} {end.x} {end.y} {end.zone_type} {end.color} {end.max_drones}")
        print()
        for z in self.zones:
            print(f"zone = {z.name} {z.x} {z.y} {z.zone_type} {z.color} {z.max_drones}")
        print()
        for c in self.connections:
            print(f"connection = {c}")


class Parser(SyntaxParser):
    def __init__(self, file_path: Path):
        self.file_path: Path = file_path
        self.lines: list[str] = self._get_lines()
        super().__init__(lines=self.lines)

    def _get_lines(self) -> list[str]:
        file = open(self.file_path, "r")
        lines = file.read().splitlines()
        file.close()
        return lines

    def get_data(self) -> Any:
        raw_data: dict[str, Any] = self._validate_data(self.lines)
        map_data = MapData(**raw_data)
        return map_data
