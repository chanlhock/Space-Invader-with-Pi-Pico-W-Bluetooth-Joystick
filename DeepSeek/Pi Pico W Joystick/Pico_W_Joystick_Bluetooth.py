# Pico_W_Joystick_Stable.py
# Stable version with proper BLE handling - FIXED advertising

import bluetooth
import struct
import time
from machine import Pin, ADC, I2C
from ssd1306 import SSD1306_I2C

# Initialize OLED
try:
    i2c = I2C(0, scl=Pin(1), sda=Pin(0), freq=400000)
    oled = SSD1306_I2C(128, 32, i2c) # Initialized to 4 lines OLED display
    oled_available = True
except:
    oled_available = False
    print("OLED not available - continuing without display")

# Initialize joystick pins
x_axis = ADC(Pin(27))
y_axis = ADC(Pin(26))
button = Pin(13, Pin.IN, Pin.PULL_UP)

# BLE UUIDs
JOYSTICK_SERVICE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
JOYSTICK_DATA_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")

# Connection state
connected = False
conn_handle = None

def update_display(line1, line2="", line3="", line4=""):
    """Update OLED display if available"""
    if oled_available:
        try:
            oled.fill(0)
            oled.text(line1, 0, 0)
            if line2:
                oled.text(line2, 0, 8)
            if line3:
                oled.text(line3, 0, 16)
            if line4:
                oled.text(line4, 0, 24)
            oled.show()
        except:
            pass  # Ignore OLED errors

def bt_irq(event, data):
    """BLE event handler"""
    global connected, conn_handle
    
    if event == 1:  # _IRQ_CENTRAL_CONNECT
        conn_handle, addr_type, addr = data
        connected = True
        print("✓ Device connected!")
        update_display("Connected!", "Sending data...")
        
    elif event == 2:  # _IRQ_CENTRAL_DISCONNECT
        conn_handle, addr_type, addr = data
        connected = False
        conn_handle = None
        print("✗ Device disconnected - restarting advertising")
        update_display("Disconnected", "Advertising...")
        
        # Restart advertising with proper format
        adv_data = create_advertising_data("Joystick_Pico")
        ble.gap_advertise(100, adv_data=adv_data)

def create_advertising_data(name):
    """Create advertising data with device name"""
    adv_data = bytearray()
    
    # Flags (0x01) - LE General Discoverable Mode
    adv_data.append(0x02)  # Length
    adv_data.append(0x01)  # Type
    adv_data.append(0x06)  # Value
    
    # Complete local name (0x09)
    name_bytes = name.encode('utf-8')
    adv_data.append(len(name_bytes) + 1)  # Length
    adv_data.append(0x09)  # Type
    adv_data.extend(name_bytes)
    
    return adv_data

# Initialize BLE
print("Initializing BLE...")
ble = bluetooth.BLE()
ble.active(True)
ble.irq(bt_irq)

# Create service
joystick_service = (JOYSTICK_SERVICE_UUID, [
    (JOYSTICK_DATA_UUID, bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY),
])

# Register services
print("Registering services...")
try:
    handles = ble.gatts_register_services([joystick_service])
    joystick_char_handle = handles[0][0]  # Get the characteristic handle
    print(f"Service registered, handle: {joystick_char_handle}")
except Exception as e:
    print(f"Service registration failed: {e}")
    raise

# Set initial value
initial_data = struct.pack('HHH', 32768, 32768, 1)
ble.gatts_write(joystick_char_handle, initial_data)

# Create advertising data
adv_data = create_advertising_data("Joystick_Pico")

# Start advertising
ble.gap_advertise(100, adv_data=adv_data)
print("Advertising as 'Joystick_Pico'")
update_display("Joystick Pico", "Advertising...", "Move joystick", "to start")

print("\n" + "="*40)
print("PICO W READY - Move the joystick!")
print("="*40)
print("Press Ctrl+C to stop\n")

# Main loop
last_values = (32768, 32768, 1)
send_counter = 0
display_counter = 0
last_send_time = time.ticks_ms()
error_count = 0

while True:
    try:
        # Read current values
        x_val = x_axis.read_u16()
        y_val = y_axis.read_u16()
        button_val = button.value()
        
        current_time = time.ticks_ms()
        
        # Always update the characteristic with current values
        current_data = struct.pack('HHH', x_val, y_val, button_val)
        ble.gatts_write(joystick_char_handle, current_data)
        
        # Send notification only if connected
        if connected and conn_handle is not None:
            # Check if values changed significantly
            x_changed = abs(x_val - last_values[0]) > 50
            y_changed = abs(y_val - last_values[1]) > 50
            button_changed = button_val != last_values[2]
            
            # Send at least every 200ms to keep connection alive
            time_since_last = time.ticks_diff(current_time, last_send_time)
            
            if x_changed or y_changed or button_changed or time_since_last > 200:
                try:
                    # Send notification
                    ble.gatts_notify(conn_handle, joystick_char_handle)
                    last_send_time = current_time
                    send_counter += 1
                    
                    # Update display occasionally
                    if send_counter % 5 == 0:
                        x_percent = (x_val * 100) // 65535
                        y_percent = (y_val * 100) // 65535
                        btn_text = "Pressed" if button_val == 0 else "Released"
                        
                        update_display(
                            f"Sent: #{send_counter}",
                            f"X:{x_percent:3d}% ({x_val})",
                            f"Y:{y_percent:3d}% ({y_val})",
                            f"Btn:{btn_text}"
                        )
                        
                        print(f"Sent #{send_counter}: X={x_val:5d} ({x_percent:3d}%), Y={y_val:5d} ({y_percent:3d}%), Button={btn_text}")
                    
                except Exception as e:
                    error_count += 1
                    if error_count % 10 == 1:  # Print every 10th error
                        print(f"Notify error {error_count}: {e}")
                    # If notify fails, device might be disconnected
                    connected = False
                    conn_handle = None
        
        # Update display even when not connected
        elif not connected:
            display_counter += 1
            if display_counter % 20 == 0:
                x_percent = (x_val * 100) // 65535
                y_percent = (y_val * 100) // 65535
                btn_text = "Pressed" if button_val == 0 else "Released"
                
                update_display(
                    "Advertising...",
                    f"X:{x_percent:3d}%",
                    f"Y:{y_percent:3d}%",
                    f"Btn:{btn_text}"
                )
                
                print(f"Local: X={x_val:5d} ({x_percent:3d}%), Y={y_val:5d} ({y_percent:3d}%), Button={btn_text}")
        
        # Update last values
        last_values = (x_val, y_val, button_val)
        
        # Small delay
        time.sleep_ms(20)  # 50Hz update
        
    except KeyboardInterrupt:
        print("\nStopped by user")
        break
    except Exception as e:
        print(f"Main loop error: {e}")
        time.sleep_ms(500)

# Cleanup
ble.active(False)
if oled_available:
    update_display("Program", "Stopped")
print("Bluetooth deactivated")
