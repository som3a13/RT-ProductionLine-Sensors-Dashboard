*For Linux : (check scripts too for headless mode)*  


*python3 ./simulators/sensor_serial.py --config "temperature:1:115200:8N1" --config "pressure:2:115200:8N1"*

*python3 ./simulators/sensor_modbus.py --config "voltage:5:localhost:1502:1:0" --config "pressure:7:localhost:1502:2:0"*

*python3 ./simulators/start_tcp_system.py --server-ports 5000 5001 --sensor flow:3:localhost:5000 --sensor vibration:4:localhost:5000 --sensor flow:6:localhost:5001*

*python3 ./scripts/test_webhook_server.py*

*python3 main.py*


For windows : (check scripts too for headless mode)

*python3 ./simulators/sensor_serial.py --config "temperature:1:115200:8N1" --com-port COM20 --config "pressure:2:115200:8N1" --com-port COM22*

*python3 ./simulators/sensor_modbus.py --config "voltage:5:localhost:1502:1:0" --config "pressure:7:localhost:1502:2:0"*

*python3 ./simulators/start_tcp_system.py --server-ports 5000 5001 --sensor flow:3:localhost:5000 --sensor vibration:4:localhost:5000 --sensor flow:6:localhost:5001*

*python3 ./scripts/test_webhook_server.py*

*python3 main.py*

---

## Credits

**Author:** Eng. Mohammed Ismail
