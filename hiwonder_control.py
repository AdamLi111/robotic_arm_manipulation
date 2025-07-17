import hid
import time
import struct
import argparse

class LeArmController:
    """
    Controller for Hiwonder LeArm using the correct protocol format.
    Protocol based on the LewanSoul/Hiwonder servo communication standard.
    """
    def __init__(self):
        self.VID = 0x0483
        self.PID = 0x5750
        self.device = None
        
        # Protocol constants
        self.FRAME_HEADER = 0x55
        self.CMD_SERVO_MOVE = 0x03
        self.CMD_ACTION_GROUP_RUN = 0x06
        self.CMD_ACTION_GROUP_STOP = 0x07
        self.CMD_ACTION_GROUP_SPEED = 0x0B
        
    def connect(self):
        """Connect to LeArm using hidapi"""
        try:
            print(f"Connecting to LeArm (VID:0x{self.VID:04x}, PID:0x{self.PID:04x})...")
            self.device = hid.device()
            self.device.open(self.VID, self.PID)
            
            manufacturer = self.device.get_manufacturer_string()
            product = self.device.get_product_string()
            print(f"Connected to: {manufacturer} - {product}")
            
            # Set non-blocking mode
            self.device.set_nonblocking(1)
            
            return True
            
        except Exception as e:
            print(f"Connection failed: {e}")
            print("\nMake sure:")
            print("1. LeArm GUI is completely closed")
            print("2. LeArm is powered on")
            print("3. USB cable is connected")
            return False
    
    def build_servo_packet(self, servos_data):
        """
        Build packet for moving servos.
        servos_data: list of tuples (servo_id, position, time_ms)
        Position range: 500-2500 (for 0-180 degrees)
        """
        # Calculate packet length: 3 bytes per servo + 5
        length = len(servos_data) * 3 + 5
        
        # Start building packet
        packet = [self.FRAME_HEADER, self.FRAME_HEADER, length, self.CMD_SERVO_MOVE]
        
        # Add number of servos
        packet.append(len(servos_data))
        
        # Add time (same for all servos in this implementation)
        time_ms = servos_data[0][2] if servos_data else 1000
        packet.append(time_ms & 0xFF)  # Time low byte
        packet.append((time_ms >> 8) & 0xFF)  # Time high byte
        
        # Add servo data
        for servo_id, position, _ in servos_data:
            packet.append(servo_id)  # Servo ID (1-6)
            packet.append(position & 0xFF)  # Position low byte
            packet.append((position >> 8) & 0xFF)  # Position high byte
        
        return packet
    
    def send_packet(self, packet):
        """Send packet to device via HID"""
        try:
            # HID packets must be 64 bytes for this device
            hid_packet = [0x00] * 64  # Start with report ID 0
            
            # Copy our packet data
            for i, byte in enumerate(packet):
                if i + 1 < len(hid_packet):
                    hid_packet[i + 1] = byte
            
            print(f"Sending: {' '.join([f'{b:02X}' for b in packet])}")
            bytes_written = self.device.write(hid_packet)
            print(f"Sent {bytes_written} bytes")
            
            # Try to read response
            time.sleep(0.05)
            data = self.device.read(64, timeout_ms=100)
            if data:
                print(f"Response: {' '.join([f'{b:02X}' for b in data[:16]])}...")
                
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def move_servo(self, servo_id, angle, time_ms=1000):
        """
        Move a single servo to specified angle.
        servo_id: 1-6
        angle: 0-180 degrees
        time_ms: time to complete movement
        """
        # Convert angle to position (500-2500 range)
        position = int((angle / 180.0) * 2000) + 500
        
        print(f"Moving servo {servo_id} to {angle}° (position: {position})")
        
        # Build and send packet
        packet = self.build_servo_packet([(servo_id, position, time_ms)])
        return self.send_packet(packet)
    
    def move_multiple_servos(self, servo_angles, time_ms=1000):
        """
        Move multiple servos simultaneously.
        servo_angles: dict of {servo_id: angle}
        """
        servos_data = []
        for servo_id, angle in servo_angles.items():
            position = int((angle / 180.0) * 2000) + 500
            servos_data.append((servo_id, position, time_ms))
        
        packet = self.build_servo_packet(servos_data)
        return self.send_packet(packet)
    
    def home_position(self):
        """Move all servos to home position (90 degrees)"""
        print("Moving to home position...")
        home_angles = {1: 90, 2: 90, 3: 90, 4: 90, 5: 90, 6: 90}
        return self.move_multiple_servos(home_angles, 1000)
    
    def close(self):
        """Close device connection"""
        if self.device:
            self.device.close()

# Predefined positions for common tasks
POSITIONS = {
    'home': {1: 90, 2: 90, 3: 90, 4: 90, 5: 90, 6: 90},
    'rest': {1: 90, 2: 45, 3: 135, 4: 45, 5: 90, 6: 90},
    'reach_forward': {1: 90, 2: 135, 3: 45, 4: 45, 5: 90, 6: 90},
    'pick_up': {1: 90, 2: 135, 3: 90, 4: 90, 5: 45, 6: 0},
    'button_press': {1: 90, 2: 100, 3: 80, 4: 70, 5: 90, 6: 45}
}

def main():
    parser = argparse.ArgumentParser(description='Control LeArm robot')
    parser.add_argument('-s', '--servo', type=int, help='Servo ID (1-6)')
    parser.add_argument('-a', '--angle', type=int, help='Target angle (0-180)')
    parser.add_argument('-t', '--time', type=int, default=1000, help='Movement time in ms')
    parser.add_argument('-p', '--position', type=str, help='Predefined position')
    parser.add_argument('--list', action='store_true', help='List predefined positions')
    parser.add_argument('--test', action='store_true', help='Test all servos')
    parser.add_argument('--home', action='store_true', help='Move to home position')
    
    args = parser.parse_args()
    
    # Create controller
    controller = LeArmController()
    
    if not controller.connect():
        return
    
    try:
        if args.list:
            print("\nPredefined positions:")
            for name, angles in POSITIONS.items():
                print(f"  {name}: {angles}")
        
        elif args.test:
            print("\n=== Testing all servos ===")
            controller.move_servo(1, 45, 500)
            time.sleep(0.5)
            controller.move_servo(1, 90, 500)
            time.sleep(0.5)
            for servo_id in range(2, 7):
                print(f"\nTesting servo {servo_id}")
                controller.move_servo(servo_id, 45, 500)
                time.sleep(0.5)
                controller.move_servo(servo_id, 135, 500)
                time.sleep(0.5)
                controller.move_servo(servo_id, 90, 500)
                time.sleep(0.5)
        
        elif args.home:
            controller.home_position()
        
        elif args.position:
            if args.position in POSITIONS:
                print(f"Moving to position: {args.position}")
                controller.move_multiple_servos(POSITIONS[args.position], args.time)
            else:
                print(f"Unknown position: {args.position}")
                print(f"Available: {list(POSITIONS.keys())}")
        
        elif args.servo and args.angle is not None:
            controller.move_servo(args.servo, args.angle, args.time)
        
        else:
            # Interactive mode
            print("\n=== LeArm Interactive Control ===")
            print("Commands:")
            print("  move <servo> <angle> [time] - Move servo")
            print("  pos <position_name> - Move to predefined position")
            print("  home - Home position")
            print("  list - List positions")
            print("  quit - Exit")
            
            while True:
                cmd = input("\n> ").strip().split()
                
                if not cmd:
                    continue
                    
                if cmd[0] == 'quit':
                    break
                elif cmd[0] == 'home':
                    controller.home_position()
                elif cmd[0] == 'list':
                    for name in POSITIONS.keys():
                        print(f"  {name}")
                elif cmd[0] == 'pos' and len(cmd) >= 2:
                    if cmd[1] in POSITIONS:
                        controller.move_multiple_servos(POSITIONS[cmd[1]])
                    else:
                        print(f"Unknown position: {cmd[1]}")
                elif cmd[0] == 'move' and len(cmd) >= 3:
                    try:
                        servo = int(cmd[1])
                        angle = int(cmd[2])
                        time_ms = int(cmd[3]) if len(cmd) > 3 else 1000
                        controller.move_servo(servo, angle, time_ms)
                    except ValueError:
                        print("Invalid servo or angle")
                else:
                    print("Unknown command")
    
    finally:
        controller.close()

if __name__ == "__main__":
    main()