import winreg
import subprocess
import ctypes
from ctypes import wintypes

def check_registry_for_virtual_ports():
    """Check Windows registry for virtual COM ports"""
    print("Checking registry for virtual COM ports...\n")
    
    try:
        # Check HKLM\HARDWARE\DEVICEMAP\SERIALCOMM
        key_path = r"HARDWARE\DEVICEMAP\SERIALCOMM"
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
        
        print("Serial devices in registry:")
        i = 0
        while True:
            try:
                name, value, _ = winreg.EnumValue(key, i)
                print(f"  {name}: {value}")
                if '0483' in name or '5750' in name:
                    print("    ^ This might be the Hiwonder device!")
                i += 1
            except WindowsError:
                break
                
        winreg.CloseKey(key)
        
    except Exception as e:
        print(f"Registry error: {e}")

def check_device_by_guid():
    """Check for devices by USB GUID"""
    print("\nChecking USB devices by GUID...")
    
    # Run PowerShell command to get USB devices
    ps_command = """
    Get-WmiObject Win32_PnPEntity | Where-Object {
        $_.DeviceID -like '*VID_0483*PID_5750*'
    } | Select-Object Name, DeviceID, Status
    """
    
    try:
        result = subprocess.run(['powershell', '-Command', ps_command], 
                              capture_output=True, text=True)
        print("Hiwonder device info:")
        print(result.stdout)
    except Exception as e:
        print(f"PowerShell error: {e}")

def list_all_com_ports():
    """List all COM ports including virtual ones"""
    print("\nAll COM ports (including virtual):")
    
    # Method 1: Using mode command
    try:
        result = subprocess.run(['mode'], capture_output=True, text=True, shell=True)
        print(result.stdout)
    except:
        pass
    
    # Method 2: Check common virtual port names
    print("\nChecking common virtual COM ports...")
    for i in range(1, 20):
        port_name = f'COM{i}'
        try:
            # Try to open the port
            handle = ctypes.windll.kernel32.CreateFileW(
                f'\\\\.\\{port_name}',
                0x80000000 | 0x40000000,  # GENERIC_READ | GENERIC_WRITE
                0,
                None,
                3,  # OPEN_EXISTING
                0,
                None
            )
            
            if handle != -1:
                print(f"  {port_name} exists")
                ctypes.windll.kernel32.CloseHandle(handle)
        except:
            pass

def monitor_api_calls():
    """Instructions for API monitoring"""
    print("\n=== API Monitor Instructions ===")
    print("The LeArm software might be using Windows APIs directly.")
    print("\nTo capture the communication:")
    print("1. Download API Monitor (free): http://www.rohitab.com/apimonitor")
    print("2. Run API Monitor as Administrator")
    print("3. In API Monitor:")
    print("   - Go to 'File' -> 'Monitor New Process'")
    print("   - Browse to your LeArm.exe")
    print("   - Before starting, select these APIs to monitor:")
    print("     * Device Input and Output")
    print("     * Human Interface Devices (HID)")
    print("     * Windows Driver Model (WDM)")
    print("4. Start the LeArm software through API Monitor")
    print("5. Move the robot arm and look for:")
    print("   - HidD_SetOutputReport calls")
    print("   - WriteFile calls")
    print("   - DeviceIoControl calls")
    print("\nThis will show you exactly what data is being sent!")

def main():
    print("=== Virtual Serial Port Finder ===\n")
    
    # Check registry
    check_registry_for_virtual_ports()
    
    # Check device by GUID
    check_device_by_guid()
    
    # List all COM ports
    list_all_com_ports()
    
    # Show API monitoring instructions
    monitor_api_calls()
    
    print("\n=== Summary ===")
    print("If no COM ports were found, the LeArm software is likely:")
    print("1. Using HID API directly (not through virtual serial)")
    print("2. Using proprietary USB communication")
    print("3. Using the device exclusively (blocking other programs)")
    print("\nNext steps:")
    print("- Try running hiwonder_control.py with LeArm GUI closed")
    print("- Use API Monitor to capture the exact commands")
    print("- Or proceed with GUI automation as a reliable alternative")

if __name__ == "__main__":
    main()