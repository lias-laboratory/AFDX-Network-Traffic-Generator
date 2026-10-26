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

"""This function converts a JSON file from the generator to a mod file that can be used by the pyFA tool.
It takes a JSON file as input (mandatory) and then create the output mod file in the same directory adding the suffix "_mod" to the original file name. The output mod file will contain the same data as the input JSON file, but with the semantic structure that is required by the pyFA tool.
The function will also print the output mod file path to the console."""
def convert_json_to_mod(input_json_file):

    #The code will check if the input JSON file exists and if not, it will print an error message and exit the program.
    if not os.path.exists(input_json_file):
        print(f"Error: The file {input_json_file} does not exist.")
        return

    # Load the input JSON file
    with open(input_json_file, 'r') as f:
        data = json.load(f)

    # Create the output mod file path by adding the suffix "_pyFA" to the original file name
    output_mod_file = os.path.splitext(input_json_file)[0] + "_pyFA.mod"

    # Create the output varaible to store the data that will be written to the output mod file (it is a txt file with a specific extension). The file will contain the number of ES and all the ES with their output port (id + rate) on one line, the number of switches and all the switches with their output port (id + rate) on one line, and the number of flows and all the flows with their path (id + path) on one line.
    output_data = []

    # add end systems as a list (end system are only connected to one switch)
    nb_end_systems = data.get("metadata", {}).get("nb_end_systems", 0)
    output_data.append(str(int(nb_end_systems)))
    end_systems = data.get("end_systems", [])
    for end_system in end_systems:
        if(end_system.get("destination", "") == None):
            continue
        # there is only 1 output port per end system
        output_port = end_system.get("output_port", [])
        output_data.append(str(end_system.get("id", "")) + " " + str(1))
        id_output_port = 1
        rate = int(output_port.get("bandwidth", -1))
        output_data.append("\t" + str(id_output_port) + " " + str(rate))

    # Create table with key: switch_id and value: table of key: output ports (the destination), value: number of the output port.
    switch_output_ports = {}
    for switch in data.get("switches", []):
        output_ports = switch.get("output_port", [])
        output_port_mapping = {}
        for index, output_port in enumerate(output_ports, start=1):
            destination = output_port.get("destination", "")
            output_port_mapping[destination] = index
        switch_output_ports[switch.get("id", "")] = output_port_mapping

    # add end systems as a list (end system are only connected to one switch)
    nb_switches = data.get("metadata", {}).get("nb_switches", 0)
    output_data.append(str(int(nb_switches)))
    switches = data.get("switches", [])
    for switch in switches:
        output_ports = switch.get("output_port", [])
        output_data.append(str(switch.get("id", "")) + " " + str(len(output_ports)))
        id_output_port = 1
        for output_port in output_ports:
            rate = int(output_port.get("bandwidth", -1))
            output_data.append("\t" + str(id_output_port) + " " + str(rate))
            id_output_port += 1

    # Add flows to the output JSON file
    flows = data.get("flows", [])
    output_data.append(str(len(flows)))
    index_flow = 1
    for flow in flows:
        size = int(flow.get("size", 0));
        # 100 should be the output rate of the end system source (in Mbps)
        BAG = int(int(flow.get("bag", 1)) * 100 / 8);
        output_data.append(str(index_flow) + " " + str(BAG) + " " + str(size) + " " + str(size) + " " + str(flow.get("priority", 0)))
        path = flow.get("path", [])
        # path must be converted into a list of server. A server is equivalent to a link. Then, we create the list with name[i]_name[i+1]
        path_servers = []
        for i in range(len(path) - 1):
            current_switch = path[i]
            next_switch = path[i + 1]
            path_servers.append(f"1 {current_switch} {switch_output_ports.get(current_switch, {}).get(next_switch, 1)}")
        output_data.append("\t" + " ".join(path_servers) + " 0")
        index_flow += 1


    # Write the output mod file
    with open(output_mod_file, "w", encoding="utf-8") as file:
        file.write("\n".join(output_data))
        file.write("\n")

    # Print the output mod file path to the console
    print(f"Output mod file created: {output_mod_file}")


# Main: take the input JSON file path as a command line argument and call the function to convert it to Saihu format. Another option is to ask the user for the parameters (packetizer and analysis_option) and then call the function to convert it to Saihu format. If the user does not provide any input, default values will be used (packetizer: false, analysis_option: FIFO).
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_json_to_pyFA.py <input_json_file> ")
        sys.exit(1)

    input_json_file = sys.argv[1]
    convert_json_to_mod(input_json_file)
