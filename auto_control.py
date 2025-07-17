import hid
import time
import argparse
import json
import os

class ButtonPressAutomation:
    """
    Automated button pressing system for LeArm robot.
    Includes position teaching and replay functionality.
    """
    def __init__(self):
        self.VID = 0x0483
        self.PID = 0x5750
        self.device = None
        self.positions_file = "button_positions.json"
        
        # Protocol constants
        self.FRAME_HEADER = 0x55
        self.CMD_SERVO_MOVE = 0x03
        
        # Default home position - safe neutral position
        self.home_position = {1: 80, 2: 90, 3: 180, 4: 130, 5: 90, 6: 70}
        
        # Load saved positions
        self.saved_positions = self.load_positions()
        
    def connect(self):
        """Connect to LeArm"""
        try:
            print("Connecting to LeArm...")
            self.device = hid.device()
            self.device.open(self.VID, self.PID)
            print("Connected successfully!")
            self.device.set_nonblocking(1)
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def build_servo_packet(self, servos_data):
        """Build packet for moving servos"""
        length = len(servos_data) * 3 + 5
        packet = [self.FRAME_HEADER, self.FRAME_HEADER, length, self.CMD_SERVO_MOVE]
        packet.append(len(servos_data))
        
        time_ms = servos_data[0][2] if servos_data else 1000
        packet.append(time_ms & 0xFF)
        packet.append((time_ms >> 8) & 0xFF)
        
        for servo_id, position, _ in servos_data:
            packet.append(servo_id)
            packet.append(position & 0xFF)
            packet.append((position >> 8) & 0xFF)
        
        return packet
    
    def send_packet(self, packet):
        """Send packet to device"""
        try:
            hid_packet = [0x00] * 64
            for i, byte in enumerate(packet):
                if i + 1 < len(hid_packet):
                    hid_packet[i + 1] = byte
            
            self.device.write(hid_packet)
            time.sleep(0.05)
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def move_to_angles(self, angles, time_ms=1000):
        """Move servos to specified angles"""
        servos_data = []
        for servo_id, angle in angles.items():
            # Convert both servo_id and angle to int in case they're strings
            servo_id = int(servo_id)
            angle = float(angle)
            position = int((angle / 180.0) * 2000) + 500
            servos_data.append((servo_id, position, time_ms))
        
        packet = self.build_servo_packet(servos_data)
        return self.send_packet(packet)
    
    def go_home(self, time_ms=1000):
        """Move robot arm to home/safe position"""
        print("Returning to home position...")
        return self.move_to_angles(self.home_position, time_ms)
    
    def set_home_position(self, angles=None):
        """Set a custom home position"""
        if angles:
            self.home_position = angles
        else:
            # Use current position as home
            print("Setting current position as home position")
            # In a real implementation, you would read current servo positions
            # For now, we'll use the teaching interface
    
    def press_button(self, position_name, press_depth=6, press_time=500, return_home=True):
        """
        Press a button at a saved position.
        press_depth: how many degrees to move down for the press
        press_time: how long to hold the press in ms
        return_home: whether to return to home position after pressing
        """
        print(f"\n=== Executing press_button for '{position_name}' ===")
        
        if position_name not in self.saved_positions:
            print(f"Position '{position_name}' not found!")
            return False
        
        position = self.saved_positions[position_name]
        print(f"Moving to button position: {position_name}")
        
        # Move to hover position
        self.move_to_angles(position, 1000)
        time.sleep(1.5)
        
        # Press down (adjust servo 4 or 5 depending on your setup)
        press_position = position.copy()
        # Ensure we're working with integers
        servo_to_press = '5'  
        current_angle = float(press_position.get(servo_to_press))
        print(current_angle)
        press_position[servo_to_press] = current_angle - press_depth
        
        print(f"Pressing button (moving servo {servo_to_press} from {current_angle}° to {press_position[servo_to_press]}°)...")
        self.move_to_angles(press_position, press_time)
        time.sleep(press_time / 1000.0 + 0.5)
        
        # Return to home position if requested
        if return_home:
            self.go_home()
            time.sleep(1)
        
        print(f"=== Completed press_button for '{position_name}' ===\n")
        return True
    
    def teach_position(self, name):
        """Interactive teaching mode to save positions"""
        print(f"\n=== Teaching Position: {name} ===")
        print("Use arrow keys to control servos:")
        print("  1-6: Select servo")
        print("  +/-: Increase/decrease angle")
        print("  s: Save position")
        print("  q: Quit without saving")
        
        # Start from home position instead of all 90°
        current_angles = self.home_position.copy()
        selected_servo = 1
        
        # Move to initial position (home position)
        self.move_to_angles(current_angles)
        
        while True:
            command = input(f"\nServo {selected_servo} at {current_angles[selected_servo]}°: ").strip()
            
            if command == 'q':
                print("Teaching cancelled")
                return False
            
            elif command == 's':
                self.saved_positions[name] = current_angles.copy()
                self.save_positions()
                print(f"Position '{name}' saved!")
                return True
            
            elif command in '123456':
                selected_servo = int(command)
                print(f"Selected servo {selected_servo}")
            
            elif command == '+':
                if current_angles[selected_servo] < 180:
                    current_angles[selected_servo] += 5
                    self.move_to_angles(current_angles, 200)
            
            elif command == '-':
                if current_angles[selected_servo] > 0:
                    current_angles[selected_servo] -= 5
                    self.move_to_angles(current_angles, 200)
    
    def load_positions(self):
        """Load saved positions from file"""
        if os.path.exists(self.positions_file):
            with open(self.positions_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_positions(self):
        """Save positions to file"""
        with open(self.positions_file, 'w') as f:
            json.dump(self.saved_positions, f, indent=2)
    
    def run_sequence(self, sequence, repeat=1, delay=1000, return_home=True):
        """Run a sequence of button presses"""
        print(f"\n=== Running Sequence (repeat={repeat}) ===")
        
        for i in range(repeat):
            if i > 0:
                print(f"\nRepetition {i + 1}/{repeat}")
            
            for step in sequence:
                if isinstance(step, str):
                    # Simple button name
                    self.press_button(step, return_home=False)  # Don't return home between buttons
                elif isinstance(step, dict):
                    # Advanced step with options
                    name = step.get('button')
                    depth = step.get('depth', 10)
                    press_time = step.get('time', 500)
                    self.press_button(name, depth, press_time, return_home=False)
                
                time.sleep(delay / 1000.0)
        
        # Return home after sequence completes
        if return_home:
            self.go_home()
            time.sleep(1)
    
    def turn_dial(self, dial_name, turn_time=1000, return_home=True):
        """
        Turn a dial using three saved positions.
        Expects positions: dial_name_open, dial_name_closed, dial_name_turned
        """
        # Check if all three positions exist
        position_open = f"{dial_name}_open"
        position_closed = f"{dial_name}_closed"
        position_turned = f"{dial_name}_turned"
        
        for pos_name in [position_open, position_closed, position_turned]:
            if pos_name not in self.saved_positions:
                print(f"Position '{pos_name}' not found! Please teach all three positions.")
                return False
        
        print(f"Turning dial: {dial_name}")
        
        # Step 1: Move to open gripper position
        print("Moving to dial with gripper open...")
        self.move_to_angles(self.saved_positions[position_open], 1000)
        time.sleep(1.5)
        
        # Step 2: Close gripper
        print("Closing gripper...")
        self.move_to_angles(self.saved_positions[position_closed], 500)
        time.sleep(0.8)
        
        # Step 3: Turn dial
        print("Turning dial...")
        self.move_to_angles(self.saved_positions[position_turned], turn_time)
        time.sleep(turn_time / 1000.0 + 0.5)
        
        # Optional: Open gripper to release
        print("Releasing dial...")
        # Move back to open position to release
        release_position = self.saved_positions[position_turned].copy()
        release_position['1'] = self.saved_positions[position_open]['1']  # Open gripper
        self.move_to_angles(release_position, 500)
        time.sleep(0.8)
        
        # Return to home position if requested
        if return_home:
            self.go_home()
            time.sleep(1)
        
        return True
    
    def teach_dial_positions(self, dial_name):
        """Teach all three positions needed for turning a dial"""
        print(f"\n=== Teaching Dial Positions for '{dial_name}' ===")
        print("You will teach 3 positions:")
        print("1. Position with gripper OPEN at the dial")
        print("2. Position with gripper CLOSED on the dial")
        print("3. Position after TURNING the dial\n")
        
        # Teach position 1: Open gripper
        input("Position the arm at the dial with GRIPPER OPEN. Press Enter to continue...")
        if not self.teach_position(f"{dial_name}_open"):
            print("Teaching cancelled")
            return False
        
        # Teach position 2: Closed gripper
        input("\nNow CLOSE the gripper on the dial. Press Enter to continue...")
        if not self.teach_position(f"{dial_name}_closed"):
            print("Teaching cancelled")
            return False
        
        # Teach position 3: Turned dial
        input("\nNow TURN the dial to desired position. Press Enter to continue...")
        if not self.teach_position(f"{dial_name}_turned"):
            print("Teaching cancelled")
            return False
        
        print(f"\nAll positions for dial '{dial_name}' saved successfully!")
        return True

    def close(self):
        if self.device:
            self.device.close()

def main():
    parser = argparse.ArgumentParser(description='LeArm Button Press Automation')
    parser.add_argument('--teach', type=str, help='Teach a new button position')
    parser.add_argument('--teach-dial', type=str, help='Teach positions for a dial')
    parser.add_argument('--press', type=str, help='Press a saved button')
    parser.add_argument('--turn', type=str, help='Turn a saved dial')
    parser.add_argument('--list', action='store_true', help='List saved positions')
    parser.add_argument('--sequence', type=str, nargs='+', help='Run a sequence of buttons')
    parser.add_argument('--repeat', type=int, default=1, help='Repeat sequence N times')
    parser.add_argument('--delay', type=int, default=1000, help='Delay between presses (ms)')
    parser.add_argument('--depth', type=int, default=10, help='Press depth in degrees')
    parser.add_argument('--turn-time', type=int, default=1000, help='Time to turn dial (ms)')
    
    args = parser.parse_args()
    
    # Create automation controller
    automation = ButtonPressAutomation()
    
    if not automation.connect():
        return
    
    try:
        if args.list:
            print("\n=== Saved Button Positions ===")
            if automation.saved_positions:
                for name, angles in automation.saved_positions.items():
                    print(f"  {name}: {angles}")
            else:
                print("  No positions saved yet")
        
        elif args.teach:
            automation.teach_position(args.teach)
        
        elif args.teach_dial:
            automation.teach_dial_positions(args.teach_dial)
        
        elif args.press:
            automation.press_button(args.press, args.depth)
        
        elif args.turn:
            automation.turn_dial(args.turn, args.turn_time)
        
        elif args.sequence:
            automation.run_sequence(args.sequence, args.repeat, args.delay)
        
        else:
            # Interactive mode
            print("\n=== LeArm Button Press Automation ===")
            print("Commands:")
            print("  teach <name> - Teach a new button position")
            print("  teach-dial <name> - Teach positions for a dial")
            print("  press <name> - Press a saved button")
            print("  turn <name> - Turn a saved dial")
            print("  sequence <btn1> <btn2> ... - Run a sequence")
            print("  list - List saved positions")
            print("  quit - Exit")
            
            while True:
                cmd = input("\n> ").strip().split()
                
                if not cmd:
                    continue
                
                if cmd[0] == 'quit':
                    break
                elif cmd[0] == 'list':
                    if automation.saved_positions:
                        for name in automation.saved_positions.keys():
                            print(f"  {name}")
                    else:
                        print("No positions saved")
                elif cmd[0] == 'teach' and len(cmd) >= 2:
                    automation.teach_position(cmd[1])
                elif cmd[0] == 'teach-dial' and len(cmd) >= 2:
                    automation.teach_dial_positions(cmd[1])
                elif cmd[0] == 'press' and len(cmd) >= 2:
                    automation.press_button(cmd[1])
                elif cmd[0] == 'turn' and len(cmd) >= 2:
                    automation.turn_dial(cmd[1])
                elif cmd[0] == 'sequence' and len(cmd) >= 2:
                    automation.run_sequence(cmd[1:])
                else:
                    print("Unknown command")
    
    finally:
        automation.close()

if __name__ == "__main__":
    main()