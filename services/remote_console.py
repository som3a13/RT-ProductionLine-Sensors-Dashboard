"""
Remote Maintenance Console - WebSocket server for remote access

Author: Mohammed Ismail AbdElmageid
"""
import asyncio
import json
import websockets
from datetime import datetime
from typing import Dict, Set, Optional
from core.sensor_data import SensorReading, AlarmEvent


class RemoteConsoleServer:
    """WebSocket server for remote maintenance console"""
    
    def __init__(self, host: str = "localhost", port: int = 8765, users: dict = None):
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.authenticated_clients: Set[websockets.WebSocketServerProtocol] = set()
        
        # Use users from config, or default if not provided
        if users:
            self.access_control = users
        else:
            # Default fallback credentials
            self.access_control = {
                "admin": {"password": "admin123", "permissions": ["read", "write", "commands"]},
                "operator": {"password": "operator123", "permissions": ["read"]},
                "viewer": {"password": "viewer123", "permissions": ["read"]}
            }
        self.client_roles: Dict[websockets.WebSocketServerProtocol, str] = {}
        self.sensor_readings: Dict[int, SensorReading] = {}
        self.alarm_log: list = []
        self.system_logs: list = []  # System logs for live log viewer
        self.clear_alarms_callback = None  # Callback to clear alarms in main GUI
        self.command_handlers = {
            "get_status": self.handle_get_status,
            "get_sensors": self.handle_get_sensors,
            "get_alarms": self.handle_get_alarms,
            "clear_alarms": self.handle_clear_alarms,
            "set_limit": self.handle_set_limit,
            "get_logs": self.handle_get_logs,
            "run_self_test": self.handle_run_self_test,
            "get_snapshot": self.handle_get_snapshot
        }
    
    def set_sensor_readings(self, readings: Dict[int, SensorReading]):
        """Update sensor readings (called from main application)"""
        self.sensor_readings = readings
    
    def add_alarm(self, alarm: AlarmEvent):
        """Add alarm to log (called from main application)"""
        self.alarm_log.append(alarm)
        # Keep only last 1000 alarms
        if len(self.alarm_log) > 1000:
            self.alarm_log = self.alarm_log[-1000:]
    
    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Register a new client"""
        self.clients.add(websocket)
        print(f"Client connected: {websocket.remote_address}")
    
    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Unregister a client"""
        username = self.client_roles.get(websocket, None)
        self.clients.discard(websocket)
        self.authenticated_clients.discard(websocket)
        if websocket in self.client_roles:
            del self.client_roles[websocket]
        
        # Log user logout if they were authenticated
        if username:
            client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
            self.add_system_log(f"User '{username}' logged out from {client_addr}", "INFO")
        
        print(f"Client disconnected: {websocket.remote_address}")
    
    def add_system_log(self, message: str, level: str = "INFO"):
        """Add a system log entry"""
        log_entry = {
            "level": level,
            "timestamp": datetime.now().isoformat(),
            "message": message
        }
        self.system_logs.append(log_entry)
        # Keep only last 1000 logs
        if len(self.system_logs) > 1000:
            self.system_logs = self.system_logs[-1000:]
        
        # Broadcast log to all authenticated clients (fire and forget)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.broadcast_log(log_entry))
            else:
                loop.run_until_complete(self.broadcast_log(log_entry))
        except RuntimeError:
            # If no event loop is running, skip broadcasting (will be sent on next get_logs)
            pass
    
    async def broadcast_log(self, log_entry: Dict):
        """Broadcast log entry to all authenticated clients"""
        if not self.authenticated_clients:
            return
        
        message = json.dumps({
            "type": "log",
            "log": log_entry
        })
        
        disconnected = set()
        for client in self.authenticated_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        for client in disconnected:
            await self.unregister_client(client)
    
    async def authenticate(self, websocket: websockets.WebSocketServerProtocol, 
                          message: Dict) -> bool:
        """Authenticate client"""
        username = message.get("username", "")
        password = message.get("password", "")
        
        if username in self.access_control:
            if self.access_control[username]["password"] == password:
                self.authenticated_clients.add(websocket)
                self.client_roles[websocket] = username
                
                # Log user login
                client_addr = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
                self.add_system_log(f"User '{username}' logged in from {client_addr}", "INFO")
                
                await websocket.send(json.dumps({
                    "type": "auth_success",
                    "role": username,
                    "permissions": self.access_control[username]["permissions"]
                }))
                return True
        
        # Log failed authentication attempt
        self.add_system_log(f"Failed authentication attempt for user '{username}'", "WARNING")
        
        await websocket.send(json.dumps({
            "type": "auth_failure",
            "message": "Invalid credentials"
        }))
        return False
    
    def has_permission(self, websocket: websockets.WebSocketServerProtocol, 
                      permission: str) -> bool:
        """Check if client has permission"""
        if websocket not in self.authenticated_clients:
            return False
        role = self.client_roles.get(websocket, "")
        if role in self.access_control:
            return permission in self.access_control[role]["permissions"]
        return False
    
    async def handle_get_status(self, websocket: websockets.WebSocketServerProtocol, 
                               data: Dict) -> Dict:
        """Handle get_status command"""
        return {
            "type": "status",
            "sensor_count": len(self.sensor_readings),
            "alarm_count": len(self.alarm_log),
            "timestamp": datetime.now().isoformat()
        }
    
    async def handle_get_sensors(self, websocket: websockets.WebSocketServerProtocol, 
                                data: Dict) -> Dict:
        """Handle get_sensors command"""
        sensors = []
        for sensor_id, reading in self.sensor_readings.items():
            sensors.append({
                "id": reading.sensor_id,
                "name": reading.sensor_name,
                "value": reading.value,
                "status": reading.status.value,
                "timestamp": reading.timestamp.isoformat(),
                "unit": reading.unit
            })
        return {
            "type": "sensors",
            "sensors": sensors
        }
    
    async def handle_get_alarms(self, websocket: websockets.WebSocketServerProtocol, 
                               data: Dict) -> Dict:
        """Handle get_alarms command"""
        limit = data.get("limit", 100)
        alarms = []
        for alarm in self.alarm_log[-limit:]:
            alarms.append({
                "timestamp": alarm.timestamp.isoformat(),
                "sensor_name": alarm.sensor_name,
                "sensor_id": alarm.sensor_id,
                "value": alarm.value,
                "alarm_type": alarm.alarm_type,
                "unit": alarm.unit
            })
        return {
            "type": "alarms",
            "alarms": alarms,
            "count": len(alarms)
        }
    
    async def handle_clear_alarms(self, websocket: websockets.WebSocketServerProtocol, 
                                 data: Dict) -> Dict:
        """Handle clear_alarms command"""
        if not self.has_permission(websocket, "write"):
            return {"type": "error", "message": "Permission denied"}
        
        username = self.client_roles.get(websocket, "Unknown")
        alarm_count = len(self.alarm_log)
        
        # Clear alarms in remote console
        self.alarm_log.clear()
        
        # Log alarm clearing event
        self.add_system_log(f"User '{username}' cleared alarm log ({alarm_count} alarms removed)", "INFO")
        
        # Clear alarms in main GUI if callback is set
        if self.clear_alarms_callback:
            try:
                # Call the callback (it will handle thread-safety)
                self.clear_alarms_callback()
            except Exception as e:
                print(f"Error clearing alarms in main GUI: {e}")
                import traceback
                traceback.print_exc()
        
        # Return success message and empty alarms list to update web interface
        return {
            "type": "success", 
            "message": "Alarm log cleared in both remote console and desktop app",
            "alarms": []  # Send empty alarms list to update web interface
        }
    
    async def handle_set_limit(self, websocket: websockets.WebSocketServerProtocol, 
                              data: Dict) -> Dict:
        """Handle set_limit command"""
        if not self.has_permission(websocket, "write"):
            return {"type": "error", "message": "Permission denied"}
        
        # This would need to be integrated with the main application
        # to actually change sensor limits
        return {
            "type": "success",
            "message": "Limit update request received (requires main app integration)"
        }
    
    async def handle_get_logs(self, websocket: websockets.WebSocketServerProtocol, 
                             data: Dict) -> Dict:
        """Handle get_logs command - Live log viewer"""
        limit = data.get("limit", 100)
        
        # Combine system logs and alarm logs
        logs = []
        
        # Add system logs (most recent first)
        for log in self.system_logs[-limit:]:
            logs.append(log)
        
        # Add alarm logs
        for alarm in self.alarm_log[-limit:]:
            logs.append({
                "level": "ALARM",
                "timestamp": alarm.timestamp.isoformat(),
                "message": f"{alarm.alarm_type} alarm on {alarm.sensor_name}: {alarm.value:.2f} {alarm.unit}"
            })
        
        # Sort by timestamp (most recent first)
        logs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Return only the requested limit
        logs = logs[:limit]
        
        return {
            "type": "logs",
            "logs": logs,
            "count": len(logs)
        }
    
    async def handle_run_self_test(self, websocket: websockets.WebSocketServerProtocol,
                                   data: Dict) -> Dict:
        """Handle run_self_test command - Run system self-test"""
        if not self.has_permission(websocket, "commands"):
            return {"type": "error", "message": "Permission denied - requires 'commands' permission"}
        
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": []
        }
        
        # Test 1: Check sensor readings availability
        sensor_test = {
            "name": "Sensor Readings",
            "status": "PASS" if len(self.sensor_readings) > 0 else "FAIL",
            "details": f"{len(self.sensor_readings)} sensors available"
        }
        test_results["tests"].append(sensor_test)
        
        # Test 2: Check each sensor
        for sensor_id, reading in self.sensor_readings.items():
            sensor_status_test = {
                "name": f"Sensor {sensor_id} ({reading.sensor_name})",
                "status": "PASS" if reading.status.value == "OK" else "WARN",
                "details": f"Value: {reading.value:.2f} {reading.unit}, Status: {reading.status.value}"
            }
            test_results["tests"].append(sensor_status_test)
        
        # Test 3: Check alarm log
        alarm_test = {
            "name": "Alarm Log",
            "status": "PASS",
            "details": f"{len(self.alarm_log)} alarms in log"
        }
        test_results["tests"].append(alarm_test)
        
        # Test 4: Check WebSocket connection
        connection_test = {
            "name": "WebSocket Connection",
            "status": "PASS" if websocket in self.authenticated_clients else "FAIL",
            "details": "Connection active" if websocket in self.authenticated_clients else "Connection inactive"
        }
        test_results["tests"].append(connection_test)
        
        # Calculate overall status
        all_passed = all(test["status"] == "PASS" for test in test_results["tests"])
        test_results["overall_status"] = "PASS" if all_passed else "WARN"
        test_results["total_tests"] = len(test_results["tests"])
        test_results["passed"] = sum(1 for test in test_results["tests"] if test["status"] == "PASS")
        test_results["failed"] = sum(1 for test in test_results["tests"] if test["status"] == "FAIL")
        test_results["warnings"] = sum(1 for test in test_results["tests"] if test["status"] == "WARN")
        
        return {
            "type": "self_test",
            "results": test_results
        }
    
    async def handle_get_snapshot(self, websocket: websockets.WebSocketServerProtocol,
                                data: Dict) -> Dict:
        """Handle get_snapshot command - Request detailed snapshot of values"""
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "system_status": {
                "sensor_count": len(self.sensor_readings),
                "alarm_count": len(self.alarm_log),
                "connected_clients": len(self.authenticated_clients)
            },
            "sensors": []
        }
        
        # Detailed sensor information
        for sensor_id, reading in self.sensor_readings.items():
            sensor_detail = {
                "id": reading.sensor_id,
                "name": reading.sensor_name,
                "value": reading.value,
                "status": reading.status.value,
                "unit": reading.unit,
                "timestamp": reading.timestamp.isoformat(),
                "is_alarm": reading.status.value in ["LOW Alarm", "HIGH Alarm", "Faulty Sensor"]
            }
            snapshot["sensors"].append(sensor_detail)
        
        # Recent alarms (last 10)
        snapshot["recent_alarms"] = []
        for alarm in self.alarm_log[-10:]:
            snapshot["recent_alarms"].append({
                "timestamp": alarm.timestamp.isoformat(),
                "sensor_id": alarm.sensor_id,
                "sensor_name": alarm.sensor_name,
                "alarm_type": alarm.alarm_type,
                "value": alarm.value,
                "unit": alarm.unit
            })
        
        # System health summary
        healthy_sensors = sum(1 for r in self.sensor_readings.values() if r.status.value == "OK")
        alarm_sensors = sum(1 for r in self.sensor_readings.values() if "Alarm" in r.status.value)
        faulty_sensors = sum(1 for r in self.sensor_readings.values() if r.status.value == "Faulty Sensor")
        
        snapshot["health_summary"] = {
            "healthy": healthy_sensors,
            "alarms": alarm_sensors,
            "faulty": faulty_sensors,
            "total": len(self.sensor_readings)
        }
        
        return {
            "type": "snapshot",
            "snapshot": snapshot
        }
    
    def set_clear_alarms_callback(self, callback):
        """Set callback function to clear alarms in main GUI"""
        self.clear_alarms_callback = callback
    
    async def handle_command(self, websocket: websockets.WebSocketServerProtocol, 
                           message: Dict):
        """Handle incoming command"""
        if websocket not in self.authenticated_clients:
            await websocket.send(json.dumps({
                "type": "error",
                "message": "Not authenticated"
            }))
            return
        
        command = message.get("command", "")
        data = message.get("data", {})
        
        if command in self.command_handlers:
            try:
                handler = self.command_handlers[command]
                result = await handler(websocket, data)
                await websocket.send(json.dumps(result))
            except Exception as e:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
        else:
            await websocket.send(json.dumps({
                "type": "error",
                "message": f"Unknown command: {command}"
            }))
    
    async def broadcast_sensor_update(self, reading: SensorReading):
        """Broadcast sensor update to all authenticated clients"""
        if not self.authenticated_clients:
            return
        
        message = json.dumps({
            "type": "sensor_update",
            "sensor": {
                "id": reading.sensor_id,
                "name": reading.sensor_name,
                "value": reading.value,
                "status": reading.status.value,
                "timestamp": reading.timestamp.isoformat(),
                "unit": reading.unit
            }
        })
        
        disconnected = set()
        for client in self.authenticated_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        for client in disconnected:
            await self.unregister_client(client)
    
    async def broadcast_alarm(self, alarm: AlarmEvent):
        """Broadcast alarm to all authenticated clients"""
        if not self.authenticated_clients:
            return
        
        message = json.dumps({
            "type": "alarm",
            "alarm": {
                "timestamp": alarm.timestamp.isoformat(),
                "sensor_name": alarm.sensor_name,
                "sensor_id": alarm.sensor_id,
                "value": alarm.value,
                "alarm_type": alarm.alarm_type,
                "unit": alarm.unit
            }
        })
        
        disconnected = set()
        for client in self.authenticated_clients:
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        for client in disconnected:
            await self.unregister_client(client)
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle client connection"""
        await self.register_client(websocket)
        try:
            # Send welcome message
            await websocket.send(json.dumps({
                "type": "welcome",
                "message": "Connected to Remote Maintenance Console"
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "")
                    
                    if msg_type == "auth":
                        await self.authenticate(websocket, data)
                    elif msg_type == "command":
                        await self.handle_command(websocket, data)
                    else:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": f"Unknown message type: {msg_type}"
                        }))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start(self):
        """Start the WebSocket server"""
        print(f"Remote Console Server starting on ws://{self.host}:{self.port}")
        async with websockets.serve(
            self.handle_client, 
            self.host, 
            self.port,
            ping_interval=20,
            ping_timeout=10
        ):
            print(f"Remote Console Server running on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever
    
    def run(self):
        """Run the server (blocking)"""
        asyncio.run(self.start())


def main():
    """Main function for standalone server"""
    import sys
    # Allow port to be specified via command line argument
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    server = RemoteConsoleServer(host="localhost", port=port)
    print(f"Starting standalone Remote Console Server on ws://localhost:{port}")
    server.run()


if __name__ == "__main__":
    main()

