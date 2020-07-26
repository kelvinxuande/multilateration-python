# necessary imports:
import csv
import os
import yaml
from datetime import datetime

"""
required configurations:
"""
station_number = 3  # number of stations deployed
master_folder = 'Resilio'  # this should be in the same directory
minimum_num_stations = 3  # for the message to be considered complete and usable

# acquire list of directories in master folder:
directories = []
for directory in os.listdir(master_folder):
    directories.append(master_folder + '/' + directory)

"""
Function to acquire lists of messages from all stations matching 'target_second',
    in all directories
args:
    target_filename: an integer, the 'current server-side second' value
    directories: a list of folder names (strings) in master_folder
returns:
    a list of all messages (in list-form) of the target seconds,
    a list of locations used
"""
def get_msg_all(target_time, directories):
    directories.sort()
    target_filename = str(target_time) + '.txt'
    config_filename = '0_station_config.yml'

    msg_all = []

    location_name = None  # default of 'Unspecified'
    locations = []

    for directory in directories:
        matching_msg_list = []
        formatted_target_filename = directory + '/' + target_filename
        formatted_config_filename = directory + '/' + config_filename
        
        try:
            with open(formatted_config_filename, 'r') as data:
                config_data = yaml.safe_load(data)
        except:
            print("Error - Filename: %s cannot be found in %s" %(formatted_config_filename, directory))
            break   # cannot find config file in directory, move onto next directory
            
        if config_data["Feed_to_base"] == True:
            location_name = config_data["Location name"]
            locations.append(config_data)
        else:
            break   # 'Feed_to_base' set to false for current directory/ station, move onto next directory
        
        try:
            with open(formatted_target_filename, 'r') as f:
                reader = csv.reader(f)
                for row in reader:
                    row.insert(0, location_name)
                    matching_msg_list.append(row)
            
                # here, we can do some sorting within each directory before adding it into our list,
                # e.g. sorting by index 2 if it contains the timestamp.
                    # it is best to create a function to do the sorting ('in-place') for you.
                matching_msg_list.sort(key = lambda x: x[2])
            
                msg_all.extend(matching_msg_list)
        except:
            print("Error - Filename: %s cannot be found in %s" %(formatted_target_filename, directory))
            
    return msg_all, locations


"""start of main code"""
"""
    Numbers to represent the current 'system second' is hardcoded here.
    In order to avoid 'race condition', we use timestamps at 'system-second' - 1 for multi-lateration
"""

# # For actual implemetation:
# utc_now = datetime.utcnow()
# utc_midnight = utc_now
# current_serverTime = (utc_now - utc_midnight.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()
# target_time = int(current_serverTime - 1)
# print(target_time)  # check
# # acquire lists of messages and lists of locations used:
# msg_list_all, locations = get_msg_all(target_time, directories)


# Only for testing purposes:
current_serverTime = 31563
target_time = int(current_serverTime - 1)
# acquire lists of messages and lists of locations used:
msg_list_all, locations = get_msg_all(target_time, directories)


# do print checks:
print("\nMultilateration target second: %d\n" %(target_time))
print("Client stations to be used for multilateration:")
for location in locations:
    print(location)
print("\nMessages retrieved from these stations:")
for messages in msg_list_all:
    print(messages)
