#!/usr/bin/env python3
"""
Generate graphical flowchart for Si-Ware System
"""
import os
import sys
from pathlib import Path

try:
    from graphviz import Digraph
except ImportError:
    print("Installing graphviz...")
    os.system("pip install graphviz")
    from graphviz import Digraph

def create_system_flowchart():
    """Create high-level system architecture flowchart with better organization"""
    
    # Create directed graph
    dot = Digraph(comment='Si-Ware System Architecture', format='png')
    dot.attr(rankdir='TB', size='20,14', dpi='300', splines='ortho')
    dot.attr('node', fontsize='11', fontname='Arial')
    dot.attr('edge', fontsize='9', fontname='Arial')
    
    # ========== STARTUP LAYER ==========
    with dot.subgraph(name='cluster_startup') as startup:
        startup.attr(label='System Startup', style='filled', fillcolor='#E8F5E9', color='#2E7D32', fontsize='14', fontname='Arial Bold')
        startup.node('start', 'System Startup', fillcolor='#90EE90', shape='ellipse', style='filled,bold')
    
    # ========== SENSOR SIMULATOR LAYER ==========
    with dot.subgraph(name='cluster_simulators') as sims:
        sims.attr(label='Sensor Simulators', style='filled', fillcolor='#FFF3E0', color='#E65100', fontsize='14', fontname='Arial Bold')
        sims.node('sim1', 'Sensor 1\nTemperature\nPTY/Serial\nTrend-Based', fillcolor='#FFE4B5', shape='box', style='rounded,filled')
        sims.node('sim2', 'Sensor 2\nPressure\nPTY/Serial\nTrend-Based', fillcolor='#FFE4B5', shape='box', style='rounded,filled')
        sims.node('sim5', 'Sensor 5\nVoltage\nModbus/TCP\nTrend-Based', fillcolor='#FFE4B5', shape='box', style='rounded,filled')
    
    # ========== TCP SERVER LAYER ==========
    with dot.subgraph(name='cluster_tcp_servers') as tcp_servers:
        tcp_servers.attr(label='TCP Sensor Servers', style='filled', fillcolor='#E1F5FE', color='#0277BD', fontsize='14', fontname='Arial Bold')
        tcp_servers.node('tcp_server1', 'TCP Server 1\nPort 5000', fillcolor='#B3E5FC', shape='box', style='rounded,filled,bold')
        tcp_servers.node('tcp_server2', 'TCP Server 2\nPort 5001', fillcolor='#B3E5FC', shape='box', style='rounded,filled,bold')
    
    # ========== TCP SENSOR CLIENTS LAYER ==========
    with dot.subgraph(name='cluster_tcp_clients') as tcp_clients:
        tcp_clients.attr(label='TCP Sensor Clients', style='filled', fillcolor='#F1F8E9', color='#558B2F', fontsize='14', fontname='Arial Bold')
        tcp_clients.node('client3', 'Sensor 3 Client\nFlow Rate\nTrend-Based', fillcolor='#DCEDC8', shape='box', style='rounded,filled')
        tcp_clients.node('client4', 'Sensor 4 Client\nVibration\nTrend-Based', fillcolor='#DCEDC8', shape='box', style='rounded,filled')
        tcp_clients.node('client6', 'Sensor 6 Client\nFlow Rate 2\nTrend-Based', fillcolor='#DCEDC8', shape='box', style='rounded,filled')
    
    # ========== MAIN APPLICATION LAYER ==========
    with dot.subgraph(name='cluster_app') as app:
        app.attr(label='Main Application', style='filled', fillcolor='#E3F2FD', color='#1565C0', fontsize='14', fontname='Arial Bold')
        app.node('app', 'Main Application\n(main.py)', fillcolor='#87CEEB', shape='ellipse', style='filled,bold')
        app.node('config', 'Load Configuration\n(config.json)', fillcolor='#BBDEFB', shape='box', style='rounded,filled')
        app.node('init', 'Initialize Components', fillcolor='#BBDEFB', shape='box', style='rounded,filled')
    
    # ========== COMMUNICATION LAYER ==========
    with dot.subgraph(name='cluster_comm') as comm:
        comm.attr(label='Communication Layer (Main App)', style='filled', fillcolor='#F3E5F5', color='#6A1B9A', fontsize='14', fontname='Arial Bold')
        comm.node('sc1', 'Serial\nCommunicator 1\n(PTY)', fillcolor='#E1BEE7', shape='box', style='rounded,filled')
        comm.node('sc2', 'Serial\nCommunicator 2\n(PTY)', fillcolor='#E1BEE7', shape='box', style='rounded,filled')
        comm.node('tc1', 'TCP Communicator\nServer:5000', fillcolor='#E1BEE7', shape='box', style='rounded,filled')
        comm.node('tc2', 'TCP Communicator\nServer:5001', fillcolor='#E1BEE7', shape='box', style='rounded,filled')
        comm.node('mc1', 'Modbus\nCommunicator 1', fillcolor='#E1BEE7', shape='box', style='rounded,filled')
    
    # ========== MANAGEMENT LAYER ==========
    with dot.subgraph(name='cluster_mgmt') as mgmt:
        mgmt.attr(label='Management Layer', style='filled', fillcolor='#FCE4EC', color='#880E4F', fontsize='14', fontname='Arial Bold')
        mgmt.node('sm', 'Sensor Manager\n(Unified Interface)', fillcolor='#F8BBD0', shape='box', style='rounded,filled,bold')
        mgmt.node('check', 'Alarm\nDetection', fillcolor='#FFCDD2', shape='diamond', style='filled')
    
    # ========== APPLICATION LAYER ==========
    with dot.subgraph(name='cluster_gui') as gui:
        gui.attr(label='GUI Application (PyQt5)', style='filled', fillcolor='#E8EAF6', color='#283593', fontsize='14', fontname='Arial Bold')
        gui.node('gui', 'GUI Application', fillcolor='#C5CAE9', shape='box', style='rounded,filled,bold')
        gui.node('dash', 'Dashboard Tab\n(Real-time Data)', fillcolor='#9FA8DA', shape='box', style='rounded,filled')
        gui.node('alarm', 'Alarm Log Tab', fillcolor='#9FA8DA', shape='box', style='rounded,filled')
        gui.node('tools', 'System Tools Tab\n(Self-Test, Snapshot)', fillcolor='#9FA8DA', shape='box', style='rounded,filled')
    
    # ========== REMOTE CONSOLE LAYER ==========
    with dot.subgraph(name='cluster_remote') as remote:
        remote.attr(label='Remote Console', style='filled', fillcolor='#FFF9C4', color='#F57F17', fontsize='14', fontname='Arial Bold')
        remote.node('rc', 'Remote Console\nServer', fillcolor='#FFF59D', shape='box', style='rounded,filled,bold')
        remote.node('ws', 'WebSocket Server\nPort 8765', fillcolor='#FFEB3B', shape='box', style='rounded,filled')
        remote.node('http', 'HTTP Server\nPort 8080', fillcolor='#FFEB3B', shape='box', style='rounded,filled')
        remote.node('web', 'Web Interface\n(HTML/JS)', fillcolor='#FFEB3B', shape='box', style='rounded,filled')
    
    # ========== NOTIFICATION LAYER ==========
    with dot.subgraph(name='cluster_notify') as notify:
        notify.attr(label='Notification System', style='filled', fillcolor='#FFE0B2', color='#E65100', fontsize='14', fontname='Arial Bold')
        notify.node('an', 'Alarm Notification\nManager', fillcolor='#FFCC80', shape='box', style='rounded,filled,bold')
        notify.node('webhook', 'Webhook\nPOST', fillcolor='#FFB74D', shape='box', style='rounded,filled')
        notify.node('desktop', 'Desktop\nNotification', fillcolor='#FFB74D', shape='box', style='rounded,filled')
    
    # ========== ALARM PROCESSING ==========
    dot.node('alarm_event', 'Create\nAlarmEvent', fillcolor='#FF5252', shape='box', style='rounded,filled,bold')
    
    # ========== CONNECTIONS - STARTUP FLOW ==========
    dot.edge('start', 'sim1', label='', style='invis')
    dot.edge('start', 'sim2', label='', style='invis')
    dot.edge('start', 'sim5', label='', style='invis')
    dot.edge('start', 'tcp_server1', label='Start', color='#0277BD', penwidth='2', style='dashed')
    dot.edge('start', 'tcp_server2', label='Start', color='#0277BD', penwidth='2', style='dashed')
    dot.edge('start', 'app', label='', color='#2E7D32', penwidth='2')
    
    # TCP Clients connect to Servers
    dot.edge('client3', 'tcp_server1', label='Connect', style='dashed', color='#558B2F', arrowhead='none')
    dot.edge('client4', 'tcp_server1', label='Connect', style='dashed', color='#558B2F', arrowhead='none')
    dot.edge('client6', 'tcp_server2', label='Connect', style='dashed', color='#558B2F', arrowhead='none')
    
    # Data Flow from TCP Clients to Servers
    dot.edge('client3', 'tcp_server1', label='JSON Data', color='#4CAF50', penwidth='2')
    dot.edge('client4', 'tcp_server1', label='JSON Data', color='#4CAF50', penwidth='2')
    dot.edge('client6', 'tcp_server2', label='JSON Data', color='#4CAF50', penwidth='2')
    
    # App initialization
    dot.edge('app', 'config', label='', color='#1565C0', penwidth='2')
    dot.edge('config', 'init', label='', color='#1565C0', penwidth='2')
    dot.edge('init', 'sm', label='', color='#880E4F', penwidth='2')
    dot.edge('init', 'gui', label='', color='#283593', penwidth='2')
    dot.edge('init', 'rc', label='', color='#F57F17', penwidth='2')
    dot.edge('init', 'an', label='', color='#E65100', penwidth='2')
    
    # Sensor Manager to Communicators
    dot.edge('sm', 'sc1', label='', color='#6A1B9A', penwidth='2')
    dot.edge('sm', 'sc2', label='', color='#6A1B9A', penwidth='2')
    dot.edge('sm', 'tc1', label='', color='#6A1B9A', penwidth='2')
    dot.edge('sm', 'tc2', label='', color='#6A1B9A', penwidth='2')
    dot.edge('sm', 'mc1', label='', color='#6A1B9A', penwidth='2')
    
    # Communicators to Simulators/Servers (connection)
    dot.edge('sc1', 'sim1', label='Connect PTY', style='dashed', color='#1976D2', arrowhead='none')
    dot.edge('sc2', 'sim2', label='Connect PTY', style='dashed', color='#1976D2', arrowhead='none')
    dot.edge('tc1', 'tcp_server1', label='Connect', style='dashed', color='#1976D2', arrowhead='none')
    dot.edge('tc2', 'tcp_server2', label='Connect', style='dashed', color='#1976D2', arrowhead='none')
    dot.edge('mc1', 'sim5', label='Connect', style='dashed', color='#1976D2', arrowhead='none')
    
    # Data Flow from Simulators to Communicators
    dot.edge('sim1', 'sc1', label='JSON Data', color='#4CAF50', penwidth='2')
    dot.edge('sim2', 'sc2', label='JSON Data', color='#4CAF50', penwidth='2')
    dot.edge('tcp_server1', 'tc1', label='Relay Data', color='#4CAF50', penwidth='2')
    dot.edge('tcp_server2', 'tc2', label='Relay Data', color='#4CAF50', penwidth='2')
    dot.edge('sim5', 'mc1', label='Modbus Data', color='#4CAF50', penwidth='2')
    
    # Communicators to Sensor Manager
    dot.edge('sc1', 'sm', label='SensorReading', color='#E91E63', penwidth='2', style='dashed')
    dot.edge('sc2', 'sm', label='SensorReading', color='#E91E63', penwidth='2', style='dashed')
    dot.edge('tc1', 'sm', label='SensorReading', color='#E91E63', penwidth='2', style='dashed')
    dot.edge('tc2', 'sm', label='SensorReading', color='#E91E63', penwidth='2', style='dashed')
    dot.edge('mc1', 'sm', label='SensorReading', color='#E91E63', penwidth='2', style='dashed')
    
    # Sensor Manager Processing
    dot.edge('sm', 'check', label='Check', color='#880E4F', penwidth='2')
    dot.edge('check', 'alarm_event', label='Alarm?', color='#D32F2F', penwidth='2', style='dashed')
    dot.edge('check', 'gui', label='OK', color='#4CAF50', penwidth='2')
    
    # Alarm Processing
    dot.edge('alarm_event', 'an', label='Trigger', color='#FF5252', penwidth='2')
    dot.edge('alarm_event', 'rc', label='Log', color='#FF5252', penwidth='2')
    dot.edge('alarm_event', 'gui', label='Update', color='#FF5252', penwidth='2')
    
    # GUI Components
    dot.edge('gui', 'dash', label='', color='#283593', penwidth='1.5')
    dot.edge('gui', 'alarm', label='', color='#283593', penwidth='1.5')
    dot.edge('gui', 'tools', label='', color='#283593', penwidth='1.5')
    
    # Remote Console Components
    dot.edge('rc', 'ws', label='', color='#F57F17', penwidth='1.5')
    dot.edge('rc', 'http', label='', color='#F57F17', penwidth='1.5')
    dot.edge('http', 'web', label='Serve', color='#F57F17', penwidth='1.5')
    dot.edge('ws', 'web', label='Real-time', color='#F57F17', penwidth='1.5', style='dashed')
    
    # Notifications
    dot.edge('an', 'webhook', label='', color='#E65100', penwidth='1.5')
    dot.edge('an', 'desktop', label='', color='#E65100', penwidth='1.5')
    
    # Sensor Manager to GUI and RC (signals)
    dot.edge('sm', 'gui', label='Signal', color='#9C27B0', penwidth='2', style='dashed')
    dot.edge('sm', 'rc', label='Update', color='#9C27B0', penwidth='2', style='dashed')
    
    return dot

def create_data_flow_diagram():
    """Create organized data flow sequence diagram with new TCP architecture"""
    
    dot = Digraph(comment='Data Flow', format='png')
    dot.attr(rankdir='LR', size='20,10', dpi='300', splines='ortho')
    dot.attr('node', shape='box', style='rounded,filled', fontsize='10', fontname='Arial')
    dot.attr('edge', fontsize='9', fontname='Arial')
    
    # Group components
    with dot.subgraph(name='cluster_source') as source:
        source.attr(label='Data Source (Serial/Modbus)', style='filled', fillcolor='#FFF3E0', color='#E65100', fontsize='12', fontname='Arial Bold')
        source.node('sim1', 'Sensor 1\nPTY/Serial', fillcolor='#FFE4B5', style='filled')
        source.node('sim2', 'Sensor 2\nPTY/Serial', fillcolor='#FFE4B5', style='filled')
        source.node('sim5', 'Sensor 5\nModbus/TCP', fillcolor='#FFE4B5', style='filled')
    
    with dot.subgraph(name='cluster_tcp') as tcp:
        tcp.attr(label='TCP Architecture', style='filled', fillcolor='#E1F5FE', color='#0277BD', fontsize='12', fontname='Arial Bold')
        tcp.node('client3', 'Sensor 3\nClient', fillcolor='#DCEDC8', style='filled')
        tcp.node('client4', 'Sensor 4\nClient', fillcolor='#DCEDC8', style='filled')
        tcp.node('client6', 'Sensor 6\nClient', fillcolor='#DCEDC8', style='filled')
        tcp.node('server1', 'TCP Server\nPort 5000', fillcolor='#B3E5FC', style='filled,bold')
        tcp.node('server2', 'TCP Server\nPort 5001', fillcolor='#B3E5FC', style='filled,bold')
    
    with dot.subgraph(name='cluster_processing') as proc:
        proc.attr(label='Data Processing (Main App)', style='filled', fillcolor='#F3E5F5', color='#6A1B9A', fontsize='12', fontname='Arial Bold')
        proc.node('sc1', 'Serial\nComm 1', fillcolor='#E1BEE7', style='filled')
        proc.node('sc2', 'Serial\nComm 2', fillcolor='#E1BEE7', style='filled')
        proc.node('tc1', 'TCP Comm\n:5000', fillcolor='#E1BEE7', style='filled')
        proc.node('tc2', 'TCP Comm\n:5001', fillcolor='#E1BEE7', style='filled')
        proc.node('mc1', 'Modbus\nComm', fillcolor='#E1BEE7', style='filled')
        proc.node('sm', 'Sensor\nManager', fillcolor='#F8BBD0', style='filled,bold')
    
    with dot.subgraph(name='cluster_output') as output:
        output.attr(label='Output & Display', style='filled', fillcolor='#E3F2FD', color='#1565C0', fontsize='12', fontname='Arial Bold')
        output.node('gui', 'GUI\nApplication', fillcolor='#C5CAE9', style='filled')
        output.node('rc', 'Remote\nConsole', fillcolor='#FFF59D', style='filled')
        output.node('web', 'Web\nInterface', fillcolor='#FFEB3B', style='filled')
    
    with dot.subgraph(name='cluster_notify') as notify:
        notify.attr(label='Notifications', style='filled', fillcolor='#FFE0B2', color='#E65100', fontsize='12', fontname='Arial Bold')
        notify.node('an', 'Alarm\nNotification', fillcolor='#FFCC80', style='filled')
    
    # Serial/Modbus Data Flow
    dot.edge('sim1', 'sc1', label='1. JSON', color='#4CAF50', penwidth='2')
    dot.edge('sim2', 'sc2', label='1. JSON', color='#4CAF50', penwidth='2')
    dot.edge('sim5', 'mc1', label='1. Modbus', color='#4CAF50', penwidth='2')
    
    # TCP Data Flow (Client -> Server -> Main App)
    dot.edge('client3', 'server1', label='1. JSON', color='#558B2F', penwidth='2')
    dot.edge('client4', 'server1', label='1. JSON', color='#558B2F', penwidth='2')
    dot.edge('client6', 'server2', label='1. JSON', color='#558B2F', penwidth='2')
    dot.edge('server1', 'tc1', label='2. Relay', color='#0277BD', penwidth='2')
    dot.edge('server2', 'tc2', label='2. Relay', color='#0277BD', penwidth='2')
    
    # Processing Flow
    dot.edge('sc1', 'sm', label='3. Parse', color='#9C27B0', penwidth='2')
    dot.edge('sc2', 'sm', label='3. Parse', color='#9C27B0', penwidth='2')
    dot.edge('tc1', 'sm', label='3. Parse', color='#9C27B0', penwidth='2')
    dot.edge('tc2', 'sm', label='3. Parse', color='#9C27B0', penwidth='2')
    dot.edge('mc1', 'sm', label='3. Parse', color='#9C27B0', penwidth='2')
    
    # Output Flow
    dot.edge('sm', 'gui', label='4. Update', color='#2196F3', penwidth='2.5', style='bold')
    dot.edge('sm', 'an', label='4. Trigger', color='#FF9800', penwidth='2.5', style='bold')
    dot.edge('sm', 'rc', label='4. Update', color='#FBC02D', penwidth='2.5', style='bold')
    dot.edge('rc', 'web', label='5. Broadcast', color='#FBC02D', penwidth='2.5', style='bold')
    
    return dot

def create_startup_flowchart():
    """Create organized startup sequence flowchart with new architecture"""
    
    dot = Digraph(comment='Startup Sequence', format='png')
    dot.attr(rankdir='TB', size='18,14', dpi='300', splines='ortho')
    dot.attr('node', fontsize='10', fontname='Arial')
    dot.attr('edge', fontsize='9', fontname='Arial')
    
    # Phases
    with dot.subgraph(name='cluster_phase0') as p0:
        p0.attr(label='Phase 0: Start Simulators', style='filled', fillcolor='#FFF3E0', color='#E65100', fontsize='13', fontname='Arial Bold')
        p0.node('start_sims', 'Start Sensor Simulators', fillcolor='#FFE4B5', shape='ellipse', style='filled,bold')
        p0.node('start_serial', 'Start Serial Sensors\n(Sensor 1 & 2)', fillcolor='#FFCC80', shape='box', style='rounded,filled')
        p0.node('start_tcp', 'Start TCP System\n(start_tcp_system.py)', fillcolor='#FFCC80', shape='box', style='rounded,filled')
        p0.node('start_modbus', 'Start Modbus Sensor\n(Sensor 5)', fillcolor='#FFCC80', shape='box', style='rounded,filled')
    
    with dot.subgraph(name='cluster_phase1') as p1:
        p1.attr(label='Phase 1: System Initialization', style='filled', fillcolor='#E8F5E9', color='#2E7D32', fontsize='13', fontname='Arial Bold')
        p1.node('start', 'User Runs\nmain.py', fillcolor='#90EE90', shape='ellipse', style='filled,bold')
        p1.node('load', 'Load config.json', fillcolor='#C8E6C9', shape='box', style='rounded,filled')
        p1.node('init', 'Initialize\nComponents', fillcolor='#C8E6C9', shape='box', style='rounded,filled')
    
    with dot.subgraph(name='cluster_phase2') as p2:
        p2.attr(label='Phase 2: Component Setup', style='filled', fillcolor='#E3F2FD', color='#1565C0', fontsize='13', fontname='Arial Bold')
        p2.node('sm', 'Sensor Manager\n(Create Communicators)', fillcolor='#BBDEFB', shape='box', style='rounded,filled')
        p2.node('gui', 'GUI Application', fillcolor='#BBDEFB', shape='box', style='rounded,filled')
        p2.node('rc', 'Remote Console', fillcolor='#BBDEFB', shape='box', style='rounded,filled')
    
    with dot.subgraph(name='cluster_phase3') as p3:
        p3.attr(label='Phase 3: Server Startup', style='filled', fillcolor='#FFF9C4', color='#F57F17', fontsize='13', fontname='Arial Bold')
        p3.node('ws', 'WebSocket Server\nPort 8765', fillcolor='#FFF59D', shape='box', style='rounded,filled')
        p3.node('http', 'HTTP Server\nPort 8080', fillcolor='#FFF59D', shape='box', style='rounded,filled')
    
    with dot.subgraph(name='cluster_phase4') as p4:
        p4.attr(label='Phase 4: User Interaction', style='filled', fillcolor='#FCE4EC', color='#880E4F', fontsize='13', fontname='Arial Bold')
        p4.node('show', 'Show GUI Window', fillcolor='#F8BBD0', shape='box', style='rounded,filled')
        p4.node('connect', 'User Clicks\nConnect', fillcolor='#F8BBD0', shape='box', style='rounded,filled')
        p4.node('connect_comm', 'Connect to All\nServers', fillcolor='#F8BBD0', shape='box', style='rounded,filled')
        p4.node('running', 'System Running\n(Real-time Updates)', fillcolor='#C2185B', shape='ellipse', style='filled,bold', fontcolor='white')
    
    # Flow
    dot.edge('start_sims', 'start_serial', label='', color='#E65100', penwidth='2')
    dot.edge('start_sims', 'start_tcp', label='', color='#E65100', penwidth='2')
    dot.edge('start_sims', 'start_modbus', label='', color='#E65100', penwidth='2')
    
    dot.edge('start', 'load', label='', color='#2E7D32', penwidth='2.5')
    dot.edge('load', 'init', label='', color='#2E7D32', penwidth='2.5')
    dot.edge('init', 'sm', label='', color='#1565C0', penwidth='2.5')
    dot.edge('init', 'gui', label='', color='#1565C0', penwidth='2.5')
    dot.edge('init', 'rc', label='', color='#1565C0', penwidth='2.5')
    dot.edge('rc', 'ws', label='', color='#F57F17', penwidth='2.5')
    dot.edge('rc', 'http', label='', color='#F57F17', penwidth='2.5')
    dot.edge('http', 'show', label='', color='#880E4F', penwidth='2.5')
    dot.edge('show', 'connect', label='', color='#880E4F', penwidth='2.5')
    dot.edge('connect', 'connect_comm', label='', color='#880E4F', penwidth='2.5')
    dot.edge('connect_comm', 'running', label='', color='#C2185B', penwidth='3', style='bold')
    
    return dot

def main():
    """Generate all flowcharts"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print("=" * 60)
    print("Generating Organized Graphical Flowcharts")
    print("=" * 60)
    
    # System Architecture
    print("\n1. Creating System Architecture Flowchart...")
    dot1 = create_system_flowchart()
    output_file1 = project_root / "SYSTEM_ARCHITECTURE"
    dot1.render(output_file1, cleanup=True)
    print(f"   ✓ Created: {output_file1}.png")
    
    # Data Flow
    print("\n2. Creating Data Flow Diagram...")
    dot2 = create_data_flow_diagram()
    output_file2 = project_root / "DATA_FLOW"
    dot2.render(output_file2, cleanup=True)
    print(f"   ✓ Created: {output_file2}.png")
    
    # Startup Sequence
    print("\n3. Creating Startup Sequence Flowchart...")
    dot3 = create_startup_flowchart()
    output_file3 = project_root / "STARTUP_SEQUENCE"
    dot3.render(output_file3, cleanup=True)
    print(f"   ✓ Created: {output_file3}.png")
    
    print("\n" + "=" * 60)
    print("All flowcharts generated successfully!")
    print("=" * 60)
    print(f"\nFiles created:")
    print(f"  - {output_file1}.png (System Architecture)")
    print(f"  - {output_file2}.png (Data Flow)")
    print(f"  - {output_file3}.png (Startup Sequence)")
    print(f"\nLocation: {project_root}")

if __name__ == "__main__":
    main()
