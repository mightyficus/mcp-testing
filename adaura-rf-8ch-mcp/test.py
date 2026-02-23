import requests
from time import sleep

def roam_test(att_ip: str, min: str, max: str, step: str, dwell: str):
    """Do roaming test between two APs with a min and max attenuation"""
    # Make sure min and max are in the correct order
    auth = ("admin", "admin")
    dwell = int(float(dwell))
    if dwell <= 0:
        raise ValueError("Dwell time must be an integer greater than 0!")
    if min > max:
        min, max = max, min
        
    url = f"http://{att_ip}/execute.php?RAMP+A+A+A+A+D+D+D+D+{float(min):.2f}+{float(max):.2f}+{float(step):.2f}+{int(float(dwell))}"
    requests.get(url, auth=auth)
    
    # Gets the dBm values for each channel after the RAMP
    # Use these to check if the ramp proceeded correctly
    sleep(2)
    url = f"http://{att_ip}/execute.php?STATUS"
    response = requests.get(url, auth=auth)
    
    values = [float(line.split(": ")[1]) for line in response.text.strip().split("\r\n") if line]
    print(response.text)
    
    for value in values:
        if float(value) != float(min) and float(value) != float(max):
            print(f"Value {value} does not match {float(min)} or {float(max)}!")
            raise Exception("Ramp up/down did not finish correctly!")
    print("Ramp was successful!")

        
# roam_test("192.168.10.87", "0", "30", "0.25", "100")