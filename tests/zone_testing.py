from src import file_parser
from pathlib import Path

file_path = "/home/varaniba/CODAM_CORE/Fly-in/tests/valid_maps/easy/01_linear_path.txt"

def check_syntax_parsing(file_path: Path):
    #Try reading file first
    try:
        lines = file_parser.FileParser.read_file(file_path)
    except Exception as error:
        print(f"File Handling Error: {error}")

    #if it succeeds, tries to get raw data by
    #checking if all the expected keys are present
    #and the lines are formatted correctly
    else:
        try:
            raw_data = file_parser.FileParser.get_raw_data(lines)
        except file_parser.FileParserError as syntax_error:
            print("Syntax errors:")
            for err in syntax_error.args[0]:
                print(err)

        #if no syntax errors are found, then the raw
        #data will be sent to a pydantic model for validation
        # else:
            try:
                config_data = file_parser.ConfigData(**raw_data)
                config_data.show()

            except Exception as pydantic_error:
                print(pydantic_error)




