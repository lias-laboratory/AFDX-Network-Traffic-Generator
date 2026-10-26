import json
import os
import sys


# Ask user for parameters
VALID_ANALYSIS_OPTIONS = {"FIFO", "IS", "PK", "CEIL", "MOH", "TDMI"}

DEFAULT_PACKETIZER = False
DEFAULT_ANALYSIS_OPTIONS = ["FIFO"]


def ask_packetizer():
    """Ask the user whether the packetizer should be enabled."""
    while True:
        user_input = input(
            "Enable packetizer? [true/false, default: false]: "
        ).strip().lower()

        if user_input == "":
            return DEFAULT_PACKETIZER

        if user_input in {"true", "t"}:
            return True

        if user_input in {"false", "f"}:
            return False

        print("Invalid value. Please enter 'true' or 'false'.")


def ask_analysis_options():
    """Ask the user for one or more analysis options."""
    while True:
        user_input = input(
            "Analysis option(s) [FIFO, IS, PK, CEIL, MOH, TDMI, "
            "default: FIFO]: "
        ).strip().upper()

        if user_input == "":
            return DEFAULT_ANALYSIS_OPTIONS.copy()

        # Accept comma-separated options
        options = [option.strip() for option in user_input.split(",")]

        # Check that all options are valid
        invalid_options = [
            option for option in options
            if option not in VALID_ANALYSIS_OPTIONS
        ]

        if invalid_options:
            print(
                f"Invalid option(s): {', '.join(invalid_options)}.\n"
                f"Valid options are: {', '.join(sorted(VALID_ANALYSIS_OPTIONS))}."
            )
            continue

        # Remove duplicates while preserving order
        return list(dict.fromkeys(options))

"""This function converts a JSON file from the generator to a JSON file that can be used by the Saihu tool.
It takes a JSON file as input (mandatory) and ask parameters to user  (or default values are taken if user does not provide any input) and then create the output JSON file in the same directory adding the suffix "_saihu" to the original file name. The output JSON file will contain the same data as the input JSON file, but with additional parameters that are required by the Saihu tool.
The function will also print the output JSON file path to the console."""
def convert_json_to_saihu(input_json_file, ask_user=False):

    #The code will check if the input JSON file exists and if not, it will print an error message and exit the program.
    if not os.path.exists(input_json_file):
        print(f"Error: The file {input_json_file} does not exist.")
        return

    # Load the input JSON file
    with open(input_json_file, 'r') as f:
        data = json.load(f)

    #Ask user for parameters : "packetizer" (true or false) and "analysis_option" (FIFO: FIFO property, IS: Input shaper, PK: Packetizer, CEIL: Fixed precision, can reduce computation time but slightly reduce precision, MOH and TDMI: Can improve delay bounds. For technical details please contact the author of xTFA Ludovic Thomas). For analysis, it can be a list of options. User can also press enter to use default values (packetizer: false, analysis_option: FIFO). The code checks if the user input is valid and if not, it will ask the user to enter a valid value.
    # Get parameters from the user
    if ask_user:
        packetizer = ask_packetizer()
        analysis_options = ask_analysis_options()
    else:
        packetizer = False
        analysis_options = ["FIFO"]

    # Create the output JSON file path by adding the suffix "_saihu" to the original file name
    output_json_file = os.path.splitext(input_json_file)[0] + "_saihu.json"

    # Create the structure : First the network. It includes name, packetizer, multiplexing, analysis_option, time_unit, data_unit, rate_unit. Then the flows. Each flow includes name, path, arrival curve, max_packet_length and min_packet_length. Then the servers. Each server includes name, service_curve (with latencies, rates) and capacity.
    output_data = {
        "network": {
            "name": data.get("metadata", {}).get("topology", "Generated network"),
            "packetizer": packetizer,
            "multiplexing": "FIFO",
            "analysis_option": analysis_options,
            "time_unit": "us",
            "data_unit": "b",
            "rate_unit": "Mbps"
        },
        "flows": [],
        "servers": []
    }

    # Add flows to the output JSON file
    for flow in data.get("flows", []):
        size = int(flow.get("size", 0)) * 8;
        BAG = int(flow.get("bag", 1));
        path = flow.get("path", [])
        # path must be converted into a list of server. A server is equivalent to a link. Then, we create the list with name[i]_name[i+1]
        path_servers = []
        for i in range(len(path) - 1):
            path_servers.append(f"{path[i]}_{path[i+1]}")

        # arrival curve is converted to a dictionary with keys bursts and rates (each of them is a list of values). The BAG and size of the original flow are converted to bursts and rates.
        arrival_curve = {
            "bursts": [1],
            "rates": [f"{size / BAG}Mbps"]
        }
        output_data["flows"].append({
            "name": flow.get("id", ""),
            "path": path_servers,
            "arrival_curve": arrival_curve,
            "max_packet_length": size,
            "min_packet_length": size
        })

    # Add servers to the output JSON file
    for end_system in data.get("end_systems", []):
        output_port = end_system.get("output_port", []).get("destination", "")
        if(output_port == None):
            continue
        rate = int(end_system.get("output_port", []).get("Bandwidth", 0))
        name = f"{end_system.get("id", "")}_{end_system.get("output_port", []).get("destination", "")}"

        output_data["servers"].append({
            "name": name,
            "service_curve": {
                    "latencies": ["0.0000001ns"],
                    "rates": [f"{rate}Mbps"]
            }
        })
    for switch in data.get("switches", []):
        for output_port in switch.get("output_port", []):
            name = f"{switch.get("id", "")}_{output_port.get("destination", "")}"
            rate = int(output_port.get("Bandwidth", 0))

            output_data["servers"].append({
                "name": name,
                "service_curve": {
                    "latencies": ["0.0000001ns"],
                    "rates": [f"{rate}Mbps"]
                }
            })

    # Write the output JSON file
    with open(output_json_file, 'w') as f:
        json.dump(output_data, f, indent=4)

    # Print the output JSON file path to the console
    print(f"Output JSON file created: {output_json_file}")


# Main: take the input JSON file path as a command line argument and call the function to convert it to Saihu format. Another option is to ask the user for the parameters (packetizer and analysis_option) and then call the function to convert it to Saihu format. If the user does not provide any input, default values will be used (packetizer: false, analysis_option: FIFO).
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_json_to_saihu.py <input_json_file> [--ask-user]")
        sys.exit(1)

    input_json_file = sys.argv[1]
    ask_user = "--ask-user" in sys.argv
    convert_json_to_saihu(input_json_file, ask_user=ask_user)
