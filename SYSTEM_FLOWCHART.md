# Si-Ware Production Line Monitoring System - High-Level Flowchart

## Graphical Flowcharts

High-resolution PNG images have been generated with improved organization:

1. **SYSTEM_ARCHITECTURE.png** - Complete system architecture diagram with organized layers

   - Grouped components by function (Simulators, Communication, Management, GUI, Remote Console, Notifications)
   - Color-coded layers for easy identification
   - Clear data flow paths

2. **DATA_FLOW.png** - Data flow sequence diagram

   - Shows step-by-step data processing
   - Grouped by processing stages
   - Numbered flow steps

3. **STARTUP_SEQUENCE.png** - System startup flowchart
   - Phased startup process
   - Clear initialization steps
   - User interaction flow

These images show the visual representation of the system architecture with improved organization and clarity.

---

## System Architecture Flow (Mermaid Diagram)

```mermaid
flowchart TD
    Start([System Startup]) --> Sim[Start Sensor Simulators]
    Start --> App[Start Main Application]

    Sim --> S1[Sensor 1 Simulator<br/>PTY/Serial<br/>Trend-Based]
    Sim --> S2[Sensor 2 Simulator<br/>PTY/Serial<br/>Trend-Based]
    Sim --> TCPStart[Start TCP Servers<br/>start_tcp_system.py]
    Sim --> S5[Sensor 5 Simulator<br/>Modbus/TCP<br/>Trend-Based]

    TCPStart --> TS1[TCP Server 1<br/>Port 5000]
    TCPStart --> TS2[TCP Server 2<br/>Port 5001]

    TS1 --> C3[Sensor 3 Client<br/>Flow Rate<br/>Trend-Based]
    TS1 --> C4[Sensor 4 Client<br/>Vibration<br/>Trend-Based]
    TS2 --> C6[Sensor 6 Client<br/>Flow Rate 2<br/>Trend-Based]

    App --> Load[Load Configuration<br/>config.json<br/>Detect TCP Servers]
    Load --> Init[Initialize Components]

    Init --> SM[Sensor Manager<br/>Auto-detect Servers]
    Init --> GUI[GUI Application]
    Init --> RC[Remote Console Server]
    Init --> AN[Alarm Notification Manager]

    SM --> SC1[Serial Communicator 1]
    SM --> SC2[Serial Communicator 2]
    SM --> TC1[TCP Communicator<br/>Server:5000]
    SM --> TC2[TCP Communicator<br/>Server:5001]
    SM --> MC1[Modbus Communicator 1]

    SC1 -.->|Connect PTY| S1
    SC2 -.->|Connect PTY| S2
    TC1 -.->|Connect| TS1
    TC2 -.->|Connect| TS2
    MC1 -.->|Connect| S5

    S1 -->|JSON Frames| SC1
    S2 -->|JSON Frames| SC2
    C3 -->|JSON Data| TS1
    C4 -->|JSON Data| TS1
    C6 -->|JSON Data| TS2
    TS1 -->|Relay Data| TC1
    TS2 -->|Relay Data| TC2
    S5 -->|Modbus Frames| MC1

    SC1 -->|SensorReading| SM
    SC2 -->|SensorReading| SM
    TC1 -->|SensorReading| SM
    TC2 -->|SensorReading| SM
    MC1 -->|SensorReading| SM

    SM -->|PyQt Signal| GUI
    SM -->|Check Alarms| AlarmCheck{Alarm<br/>Detected?}

    AlarmCheck -->|Yes| Alarm[Create AlarmEvent]
    AlarmCheck -->|No| GUI

    Alarm --> AN
    Alarm --> RC
    Alarm --> GUI

    AN -->|Webhook POST| Webhook[Webhook Server]
    AN -->|Desktop Notification| Desktop[OS Notification]

    GUI -->|Display| Dashboard[Dashboard Tab]
    GUI -->|Display| AlarmLog[Alarm Log Tab]
    GUI -->|Display| Tools[System Tools Tab]

    RC -->|WebSocket| WS[WebSocket Server<br/>Port 8765]
    RC -->|HTTP| HTTP[HTTP Server<br/>Port 8080]

    HTTP -->|Serve| WebUI[Web Interface<br/>remote_console_client.html]

    WS -->|Real-time Data| WebUI
    WebUI -->|Commands| WS
    WS -->|Execute| RC

    style Start fill:#90EE90
    style App fill:#87CEEB
    style SM fill:#FFB6C1
    style GUI fill:#DDA0DD
    style RC fill:#F0E68C
    style AN fill:#FFA07A
    style Alarm fill:#FF6347
    style TS1 fill:#B3E5FC
    style TS2 fill:#B3E5FC
    style TCPStart fill:#DCEDC8
```

## Data Flow Diagram

```mermaid
sequenceDiagram
    participant Sim as Sensor Simulator<br/>(Serial/Modbus)
    participant Client as TCP Sensor Client<br/>(For TCP Sensors)
    participant Server as TCP Server<br/>(Port 5000/5001)
    participant Comm as Communicator<br/>(Worker Thread)
    participant SM as Sensor Manager
    participant GUI as GUI Application
    participant AN as Alarm Notification
    participant RC as Remote Console
    participant Web as Web Interface

    Note over Sim,Server: Serial/Modbus Path
    Sim->>Comm: Send Data Frame<br/>(JSON/Modbus)

    Note over Client,Server: TCP Path
    Client->>Server: Send JSON Data
    Server->>Comm: Relay Data<br/>(Broadcast)

    Comm->>Comm: Parse Frame
    Comm->>Comm: Create SensorReading
    Comm->>SM: Emit Signal<br/>(Thread-Safe)

    SM->>SM: Check Alarm Limits
    alt Alarm Detected
        SM->>SM: Create AlarmEvent
        SM->>AN: Emit Alarm Signal
        SM->>RC: Add Alarm to Log
        SM->>GUI: Emit Alarm Signal
        AN->>AN: Send Notifications<br/>(Webhook, Desktop)
    end

    SM->>GUI: Emit Reading Signal
    GUI->>GUI: Update Dashboard
    GUI->>GUI: Update Plots
    GUI->>GUI: Update Status

    RC->>Web: Broadcast Updates<br/>(WebSocket)
    Web->>RC: Send Commands
    RC->>RC: Execute Commands
    RC->>Web: Send Response
```

## Component Interaction Flow

```mermaid
graph LR
    subgraph "Sensor Layer"
        S1[Sensor 1<br/>PTY/Serial<br/>Trend-Based]
        S2[Sensor 2<br/>PTY/Serial<br/>Trend-Based]
        S5[Sensor 5<br/>Modbus/TCP<br/>Trend-Based]
    end

    subgraph "TCP Architecture"
        C3[Sensor 3 Client<br/>Flow Rate]
        C4[Sensor 4 Client<br/>Vibration]
        C6[Sensor 6 Client<br/>Flow Rate 2]
        TS1[TCP Server 1<br/>Port 5000]
        TS2[TCP Server 2<br/>Port 5001]
    end

    subgraph "Communication Layer<br/>(Main App)"
        SC[Serial<br/>Communicators]
        TC1[TCP Comm<br/>:5000]
        TC2[TCP Comm<br/>:5001]
        MC[Modbus<br/>Communicator]
    end

    subgraph "Management Layer"
        SM[Sensor Manager<br/>Auto-detect Servers]
    end

    subgraph "Application Layer"
        GUI[GUI Application<br/>PyQt5]
        RC[Remote Console<br/>WebSocket/HTTP]
    end

    subgraph "Service Layer"
        AN[Alarm Notification<br/>Manager]
    end

    S1 & S2 --> SC
    C3 & C4 --> TS1
    C6 --> TS2
    TS1 --> TC1
    TS2 --> TC2
    S5 --> MC

    SC & TC1 & TC2 & MC --> SM
    SM --> GUI
    SM --> RC
    SM --> AN

    GUI --> RC
    AN --> GUI
```

## Startup Sequence

```mermaid
flowchart TD
    Start([User Starts System]) --> StartSims[Start Sensor Simulators]
    Start --> StartApp[Start Main Application]

    StartSims --> StartSerial[Start Serial Sensors<br/>Sensor 1 & 2]
    StartSims --> StartTCP[Start TCP System<br/>start_tcp_system.py]
    StartSims --> StartModbus[Start Modbus Sensor<br/>Sensor 5]

    StartTCP --> TCP1[TCP Server 1<br/>Port 5000]
    StartTCP --> TCP2[TCP Server 2<br/>Port 5001]
    StartTCP --> ConnectClients[Connect Sensor Clients<br/>to Servers]

    StartApp --> LoadConfig[Load config.json]
    LoadConfig --> InitGUI[Initialize GUI]
    InitGUI --> InitSM[Initialize Sensor Manager<br/>Create Communicators]
    InitSM --> InitRC[Initialize Remote Console]
    InitRC --> StartWS[Start WebSocket Server<br/>Port 8765]
    StartWS --> StartHTTP[Start HTTP Server<br/>Port 8080]
    StartHTTP --> ShowGUI[Show GUI Window]
    ShowGUI --> Wait[Wait for User Action]

    Wait -->|User Clicks Connect| Connect[Connect to All Servers]
    Connect --> SC1[Connect Serial 1]
    Connect --> SC2[Connect Serial 2]
    Connect --> TC1[Connect TCP Server:5000]
    Connect --> TC2[Connect TCP Server:5001]
    Connect --> MC1[Connect Modbus 1]

    SC1 --> StartThread1[Start Worker Thread 1]
    SC2 --> StartThread2[Start Worker Thread 2]
    TC1 --> StartThread3[Start Worker Thread 3]
    TC2 --> StartThread4[Start Worker Thread 4]
    MC1 --> StartThread5[Start Worker Thread 5]

    StartThread1 & StartThread2 & StartThread3 & StartThread4 & StartThread5 --> Running[System Running]

    Running --> ReadData[Read Sensor Data<br/>Trend-Based Values]
    ReadData --> ProcessData[Process & Check Alarms]
    ProcessData --> UpdateGUI[Update GUI]
    ProcessData --> UpdateRC[Update Remote Console]
    ProcessData --> SendNotifications[Send Notifications]

    UpdateGUI --> ReadData
    UpdateRC --> ReadData
    SendNotifications --> ReadData

    style Start fill:#90EE90
    style Running fill:#87CEEB
    style ReadData fill:#FFB6C1
    style StartTCP fill:#DCEDC8
    style TCP1 fill:#B3E5FC
    style TCP2 fill:#B3E5FC
```

## Alarm Processing Flow

```mermaid
flowchart TD
    Reading[New Sensor Reading] --> Check{Value within<br/>Limits?}

    Check -->|Yes| StatusOK[Status: OK]
    Check -->|No| CheckLow{Value <br/>Low Limit?}
    Check -->|Faulty| StatusFaulty[Status: FAULTY<br/>Value = -999.0]

    CheckLow -->|Yes| AlarmLow[Create LOW Alarm]
    CheckLow -->|No| AlarmHigh[Create HIGH Alarm]

    AlarmLow --> AlarmEvent[AlarmEvent Created]
    AlarmHigh --> AlarmEvent
    StatusFaulty --> AlarmEvent

    AlarmEvent --> AddLog[Add to Alarm Log]
    AlarmEvent --> Notify[Trigger Notifications]

    AddLog --> UpdateGUI[Update GUI Alarm Table]
    AddLog --> UpdateRC[Update Remote Console]

    Notify --> Webhook[Send Webhook POST]
    Notify --> Desktop[Show Desktop Notification]

    StatusOK --> UpdateDisplay[Update Sensor Display]
    UpdateGUI --> UpdateDisplay
    UpdateRC --> UpdateDisplay

    style AlarmEvent fill:#FF6347
    style Notify fill:#FFA07A
    style StatusOK fill:#90EE90
```

## Remote Console Command Flow

```mermaid
sequenceDiagram
    participant User as Web Browser
    participant HTTP as HTTP Server
    participant WS as WebSocket Server
    participant RC as Remote Console
    participant SM as Sensor Manager
    participant GUI as GUI Application

    User->>HTTP: Request /remote_console_client.html
    HTTP->>User: Serve HTML Page
    User->>WS: WebSocket Connect
    WS->>User: Request Authentication
    User->>WS: Send Credentials
    WS->>RC: Authenticate User
    RC->>User: Auth Success/Failure

    User->>WS: Send Command<br/>(get_status, get_sensors, etc.)
    WS->>RC: Process Command
    RC->>SM: Get Sensor Data
    RC->>RC: Get Alarm Log
    RC->>WS: Return Response
    WS->>User: Send JSON Response
    User->>User: Update Web Interface

    alt Clear Alarms Command
        User->>WS: clear_alarms
        WS->>RC: Clear Alarms
        RC->>GUI: Clear Alarm Log
        RC->>User: Success Response
    end

    alt Self-Test Command
        User->>WS: run_self_test
        WS->>RC: Run Tests
        RC->>SM: Check Connections
        RC->>RC: Test Components
        RC->>User: Test Results
    end
```

## Thread Architecture Flow

```mermaid
graph TD
    subgraph "Main Thread (GUI)"
        GUI[GUI Application]
        SM[Sensor Manager]
    end

    subgraph "Worker Thread 1"
        WT1[Serial Communicator 1]
        WT1Q[Queue 1]
    end

    subgraph "Worker Thread 2"
        WT2[Serial Communicator 2]
        WT2Q[Queue 2]
    end

    subgraph "Worker Thread 3"
        WT3[TCP Communicator 1]
        WT3Q[Queue 3]
    end

    subgraph "Worker Thread 4"
        WT4[TCP Communicator 2]
        WT4Q[Queue 4]
    end

    subgraph "Worker Thread 5"
        WT5[Modbus Communicator 1]
        WT5Q[Queue 5]
    end

    subgraph "AsyncIO Thread"
        RC[Remote Console Server]
    end

    WT1 -->|PyQt Signal| SM
    WT2 -->|PyQt Signal| SM
    WT3 -->|PyQt Signal| SM
    WT4 -->|PyQt Signal| SM
    WT5 -->|PyQt Signal| SM

    SM -->|Thread-Safe| GUI
    SM -->|Update| RC

    style GUI fill:#DDA0DD
    style SM fill:#FFB6C1
    style RC fill:#F0E68C
```

## ASCII Art Flowchart (Plain Text Version)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SYSTEM STARTUP FLOW                          │
└─────────────────────────────────────────────────────────────────┘

    [User Starts Application]
            │
            ├───> Start Sensor Simulators
            │         │
            │         ├───> Sensor 1 (PTY) ────> /dev/pts/X
            │         ├───> Sensor 2 (PTY) ────> /dev/pts/Y
            │         ├───> Sensor 3 (TCP) ────> localhost:5000
            │         ├───> Sensor 4 (TCP) ────> localhost:5001
            │         └───> Sensor 5 (Modbus) ──> localhost:1502
            │
            └───> Start Main Application (main.py)
                      │
                      ├───> Load config.json
                      │
                      ├───> Initialize Sensor Manager
                      │         │
                      │         ├───> Serial Communicators
                      │         ├───> TCP Communicators
                      │         └───> Modbus Communicator
                      │
                      ├───> Initialize GUI (PyQt5)
                      │         │
                      │         ├───> Dashboard Tab
                      │         ├───> Alarm Log Tab
                      │         └───> System Tools Tab
                      │
                      ├───> Start Remote Console
                      │         │
                      │         ├───> WebSocket Server (Port 8765)
                      │         └───> HTTP Server (Port 8080)
                      │
                      └───> Show GUI Window

┌─────────────────────────────────────────────────────────────────┐
│                    DATA FLOW                                     │
└─────────────────────────────────────────────────────────────────┘

    Sensor Simulator
            │
            │ (JSON/Modbus Frame)
            ▼
    Communicator (Worker Thread)
            │
            │ Parse & Create SensorReading
            ▼
    Sensor Manager
            │
            ├───> Check Alarm Limits
            │         │
            │         ├───> OK ────────────> Update GUI
            │         ├───> LOW Alarm ────> Create AlarmEvent
            │         ├───> HIGH Alarm ───> Create AlarmEvent
            │         └───> FAULTY ───────> Create AlarmEvent
            │
            ├───> Emit PyQt Signal (Thread-Safe)
            │         │
            │         └───> GUI Updates (Main Thread)
            │
            └───> Update Remote Console
                      │
                      └───> Broadcast to Web Clients

┌─────────────────────────────────────────────────────────────────┐
│                    ALARM PROCESSING                              │
└─────────────────────────────────────────────────────────────────┘

    Sensor Reading
            │
            ▼
    Check Value vs Limits
            │
            ├───> Within Limits ────> Status: OK ────> Update Display
            │
            ├───> Below Low Limit ──> Create LOW Alarm
            │
            ├───> Above High Limit ─> Create HIGH Alarm
            │
            └───> Value = -999.0 ───> Status: FAULTY
                      │
                      ▼
            Create AlarmEvent
                      │
            ┌─────────┴─────────┐
            │                   │
            ▼                   ▼
    Add to Alarm Log    Trigger Notifications
            │                   │
            │                   ├───> Webhook POST
            │                   └───> Desktop Notification
            │
            ▼
    Update GUI & Remote Console

┌─────────────────────────────────────────────────────────────────┐
│                    REMOTE CONSOLE FLOW                           │
└─────────────────────────────────────────────────────────────────┘

    Web Browser
            │
            ├───> HTTP Request ────> http://localhost:8080/...
            │                           │
            │                           ▼
            │                    HTTP Server
            │                           │
            │                           ▼
            │                    Serve HTML Page
            │
            └───> WebSocket Connect ──> ws://localhost:8765
                      │
                      ▼
            Authentication
                      │
                      ▼
            Send Commands
                      │
            ┌─────────┴─────────┐
            │                   │
    get_status          get_sensors
    get_alarms          clear_alarms
    run_self_test       get_snapshot
            │                   │
            └─────────┬─────────┘
                      │
                      ▼
            Remote Console Server
                      │
                      ├───> Query Sensor Manager
                      ├───> Query Alarm Log
                      └───> Execute Commands
                      │
                      ▼
            Send JSON Response
                      │
                      ▼
            Update Web Interface
```

## Key System Components

1. **Sensor Simulators**: Generate realistic sensor data
2. **Communicators**: Handle protocol-specific communication (Serial, TCP, Modbus)
3. **Sensor Manager**: Unified interface for all sensors, manages worker threads
4. **GUI Application**: PyQt5 desktop interface with real-time updates
5. **Remote Console**: WebSocket/HTTP server for remote access
6. **Alarm Notification Manager**: Handles webhook and desktop notifications

## Communication Patterns

- **Thread-Safe Signals**: Worker threads use PyQt signals to communicate with GUI thread
- **Event-Driven**: System responds to sensor readings and user commands
- **Real-Time Updates**: Data flows continuously from sensors to GUI and remote console
- **Asynchronous**: Remote console uses asyncio for non-blocking operations

---

_This flowchart represents the high-level architecture and data flow of the Si-Ware Production Line Monitoring System._
