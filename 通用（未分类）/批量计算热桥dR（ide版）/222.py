import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress

# Function to process each file
def process_file(file_path):
    I2, R1, R2 = [], [], []
    with open(file_path, 'r') as file:
        lines = file.readlines()[2:]  # Skip the first two lines
        for line in lines:
            columns = line.split()
            if len(columns) >= 5:
                I2.append(float(columns[1]))
                R1.append(float(columns[2]))
                R2.append(float(columns[4]))
    return np.array(I2), np.array(R1), np.array(R2)

# Function to plot and fit data
def plot_and_fit(x, y, xlabel, ylabel, title):
    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    plt.figure()
    plt.plot(x, y, 'o', label='Original data')
    plt.plot(x, intercept + slope * x, 'r', label='Fitted line')
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.show()

    return slope

# Directory containing the data files
directory = r'F:\OneDrive - 草莓甜品屋\实验数据\PE-SiC\PEDOT PSS\undope nanofiber S1'

# Initialize lists to store results
temperatures = []
dR1_values = []
dR2_values = []

# Process each file in the directory
for file_name in os.listdir(directory):
    if file_name.endswith('.txt'):
        try:
            temperature = int(file_name.split('K')[0])
        except ValueError:
            # Skip files that do not contain temperature information
            continue

        file_path = os.path.join(directory, file_name)
        I2, R1, R2 = process_file(file_path)

        # Perform linear fit and calculate dy for R1 and R2
        slope_R1 = plot_and_fit(I2, R1, 'I2', 'R1', f'Linear Fit for {file_name} (R1)')
        slope_R2 = plot_and_fit(I2, R2, 'I2', 'R2', f'Linear Fit for {file_name} (R2)')

        # Calculate dy (slope * dx)
        dx = max(I2)
        print(f'File: {file_name}, Slope R1: {slope_R1}, Slope R2: {slope_R2}, dx: {dx}')
        dR1 = slope_R1 * dx
        dR2 = slope_R2 * dx

        # Store results
        temperatures.append(temperature)
        dR1_values.append(dR1)
        dR2_values.append(dR2)

# Sort results by temperature
sorted_results = sorted(zip(temperatures, dR1_values, dR2_values))

# Output temperature and dR1/dR2 values to a txt file
output_file = 'temperature_dR1_dR2_sorted.txt'
with open(output_file, 'w') as f:
    f.write('Temperature(K)\tdR1\tdR2\n')
    for temp, dR1, dR2 in sorted_results:
        f.write(f'{temp}\t{dR1}\t{dR2}\n')

print(f'Temperature and dR1/dR2 values have been saved to {output_file}')
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import linregress

# Function to process each file
def process_file(file_path):
    I2, R1, R2 = [], [], []
    with open(file_path, 'r') as file:
        lines = file.readlines()[2:]  # Skip the first two lines
        for line in lines:
            columns = line.split()
            if len(columns) >= 5:
                I2.append(float(columns[1]))
                R1.append(float(columns[2]))
                R2.append(float(columns[4]))
    return np.array(I2), np.array(R1), np.array(R2)

# Function to plot and fit data
def plot_and_fit(x, y, xlabel, ylabel, title):
    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    plt.figure()
    plt.plot(x, y, 'o', label='Original data')
    plt.plot(x, intercept + slope * x, 'r', label='Fitted line')
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.show()

    return slope

# Directory containing the data files
directory = r'F:\OneDrive - 草莓甜品屋\实验数据\PE-SiC\PEDOT PSS\undope nanofiber S1'

# Initialize lists to store results
temperatures = []
dR1_values = []
dR2_values = []

# Process each file in the directory
for file_name in os.listdir(directory):
    if file_name.endswith('.txt'):
        try:
            temperature = int(file_name.split('K')[0])
        except ValueError:
            # Skip files that do not contain temperature information
            continue

        file_path = os.path.join(directory, file_name)
        I2, R1, R2 = process_file(file_path)

        # Perform linear fit and calculate dy for R1 and R2
        slope_R1 = plot_and_fit(I2, R1, 'I2', 'R1', f'Linear Fit for {file_name} (R1)')
        slope_R2 = plot_and_fit(I2, R2, 'I2', 'R2', f'Linear Fit for {file_name} (R2)')

        # Calculate dy (slope * dx)
        dx = max(I2)
        print(f'File: {file_name}, Slope R1: {slope_R1}, Slope R2: {slope_R2}, dx: {dx}')
        dR1 = slope_R1 * dx
        dR2 = slope_R2 * dx

        # Store results
        temperatures.append(temperature)
        dR1_values.append(dR1)
        dR2_values.append(dR2)

# Sort results by temperature
sorted_results = sorted(zip(temperatures, dR1_values, dR2_values))

# Output temperature and dR1/dR2 values to a txt file
output_file = 'temperature_dR1_dR2_sorted.txt'
with open(output_file, 'w') as f:
    f.write('Temperature(K)\tdR1\tdR2\n')
    for temp, dR1, dR2 in sorted_results:
        f.write(f'{temp}\t{dR1}\t{dR2}\n')

print(f'Temperature and dR1/dR2 values have been saved to {output_file}')
