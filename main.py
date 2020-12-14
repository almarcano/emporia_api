import sys
import json
from dateutil import tz
from datetime import datetime, timedelta
import csv
import plotly
import plotly.graph_objects as go
import pandas as pd

from pyemvue.pyemvue import PyEmVue
from pyemvue.customer import Customer
from pyemvue.enums import Scale, Unit, TotalTimeFrame, TotalUnit
from pyemvue.device import VueDevice, VueDeviceChannel, VuewDeviceChannelUsage

vue = PyEmVue()
now = datetime.utcnow()
startUse = datetime(2020, 10, 1, 0, 0, 0)

def main():
    errorMsg = 'Please pass a file containing the "email" and "password" as json.'
    if len(sys.argv) == 1:                      # Chequea si se pasó el archivo Json
        print(errorMsg)
        sys.exit(1)

    filepath = sys.argv[1]                      # Path del archivo Json

    data = {}
    email = None
    passw = None
    idToken = None
    accessToken = None
    refreshToken = None

    try:
        with open(filepath) as f:               # Abre el archivo Json
            data = json.load(f)
    except:
        print('Error opening file.', errorMsg)
        raise

    if ('email' not in data or 'password' not in data) and ('idToken' not in data or 'accessToken' not in data or 'refreshToken' not in data):
        print(errorMsg)
        sys.exit(1)
    canLogIn = False
    if 'email' in data:
        email = data['email']
        if 'password' in data:
            passw = data['password']
            canLogIn = True
    if 'idToken' in data and 'accessToken' in data and 'refreshToken' in data:
        idToken = data['idToken']
        accessToken = data['accessToken']
        refreshToken = data['refreshToken']
        canLogIn = True
    if not canLogIn:
        print('Not enough details to log in.', errorMsg)
        sys.exit(1)
    # LOGIN
    vue.login(email, passw, idToken, accessToken, refreshToken, token_storage_file='keys.json')
    # CUSTOMER DATA
    customer = vue.get_customer_details()                   # Get customer details
    print("Customer ID: " + str(customer.customer_gid))
    print("Nombre: " + customer.first_name)
    print("Apellidos: " + customer.lastName)
    print("Email: " + customer.email)
    print("Creado: " + customer.created_at)
    print()
    # DEVICES DETAILS
    devices = vue.get_devices()                             # Get devices details
    for i, device in enumerate(devices):
        device = vue.populate_device_properties(device)
        totalUsage = vue.get_usage_over_time(devices[i].channels[0], startUse, now, scale=Scale.HOUR.value, unit=Unit.WATTS)
        create_csv(device.device_name, totalUsage)          # Crea Archivos csv
        create_plot(device.device_name)                     # Crea Gráficos en html
        print(device.device_name)                           # Nombre del equipo
        print("GID: " + str(device.device_gid))             # GID del equipo
        print("Modelo: " + device.model)                    # Modelo del equipo
        print("Device ID: " + '-'.join(device.manufacturer_id.upper()[i:i+4] for i in range(0,16,4)))  # Serial del equipo
        print("Firmware: " + device.firmware)
        vue.populate_device_properties(device)                 # Firmware del equipo
        for chan in device.channels:
            print(f"Canales en uso: {chan.channel_num} Multiplicador: {chan.channel_multiplier}")
        print(round(vue.get_total_usage(devices[i].channels[0], TotalTimeFrame.MONTH.value) / 1000, 2), "kwh used month to date")
        print(round(vue.get_total_usage(devices[i].channels[0], TotalTimeFrame.ALL.value) / 1000, 2), "kwh used TOTAL")
        print()  

def create_csv(name, total):
    filename = name + ".csv"
    fieldNames = ["DateTime", "Value"]
    startUse = datetime(2020, 9, 30, 18, 0, 0)
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldNames)
        writer.writeheader()
        for i, line in enumerate(total):
            date_and_time = startUse + timedelta(hours=+i)
            if line is None:
                kwh = 0.0   
            else: 
                kwh = round(float(line)/1000, 2)
            writer.writerow({"DateTime":date_and_time, "Value":kwh})

def create_plot(name):
    csv_file = name + ".csv"
    df = pd.read_csv(csv_file)
    data = [go.Scatter( x = df['DateTime'], y = df['Value'])]
    fig = go.Figure(data)
    plotly.offline.plot(fig, filename = name + ".html")    

if __name__ == '__main__':
    main()