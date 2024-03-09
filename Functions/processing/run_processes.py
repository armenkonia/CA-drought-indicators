# -*- coding: utf-8 -*-
"""
Created on Fri Mar  8 21:51:35 2024

@author: armen
"""

import time
import subprocess
import sys

def execute_and_time(script_path):
    # Record the start time
    start_time = time.time()

    try:
        # Use sys.executable to get the Python interpreter executable
        subprocess.run([sys.executable, script_path], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing the script: {e}")
        return

    # Record the end time
    end_time = time.time()

    # Calculate the elapsed time
    execution_time_minutes = (end_time - start_time) / 60

    # Print the result
    print(f"{script_path} execution time: {round(execution_time_minutes, 1)} minutes")


# 3.1 prcp and et
script_path = 'pr_pet_obtain_regional_summaries.py'
execute_and_time(script_path)

script_path = 'pr_and_et_indicators.py'
execute_and_time(script_path)

# 3.3 surface water drought indicator
script_path = 'surface_water_drought_indicator.py'
execute_and_time(script_path)

# 3.4 Groundwater status
script_path = 'groundwater_drought.py'
execute_and_time(script_path)

# 3.5 streamflow conditions
script_path = 'streamflow_indicator.py'
execute_and_time(script_path)

# 3.6 imports indicator
script_path = 'imports_indicator.py'
execute_and_time(script_path)