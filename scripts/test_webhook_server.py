#!/usr/bin/env python3
"""
Simple Webhook Test Server
Receives POST requests from webhook and displays the data

Author: Mohammed Ismail AbdElmageid
"""
import http.server
import socketserver
import json
from datetime import datetime
from urllib.parse import urlparse


# Global storage for webhook data (in production, use a database)
webhook_data = []
MAX_RECORDS = 50  # Keep last 50 webhook requests


class WebhookHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler for webhook testing"""
    
    def log_message(self, format, *args):
        """Override to customize log format"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format % args}")
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests (webhook)"""
        try:
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            
            # Read request body
            if content_length > 0:
                body = self.rfile.read(content_length)
                
                # Try to parse as JSON
                try:
                    data = json.loads(body.decode('utf-8'))
                    received_time = datetime.now()
                    
                    # Store webhook data
                    webhook_record = {
                        "received_at": received_time.isoformat(),
                        "client": f"{self.client_address[0]}:{self.client_address[1]}",
                        "path": self.path,
                        "data": data
                    }
                    webhook_data.insert(0, webhook_record)  # Add to beginning
                    if len(webhook_data) > MAX_RECORDS:
                        webhook_data.pop()  # Remove oldest if exceeds limit
                    
                    print("\n" + "=" * 60)
                    print("WEBHOOK POST REQUEST RECEIVED")
                    print("=" * 60)
                    print(f"Time: {received_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"Path: {self.path}")
                    print(f"Client: {self.client_address[0]}:{self.client_address[1]}")
                    print("\nJSON Payload:")
                    print(json.dumps(data, indent=2))
                    print("\nParsed Data:")
                    print(f"  Event Type: {data.get('event_type', 'N/A')}")
                    print(f"  Sensor ID: {data.get('sensor_id', 'N/A')}")
                    print(f"  Sensor Name: {data.get('sensor_name', 'N/A')}")
                    print(f"  Alarm Type: {data.get('alarm_type', 'N/A')}")
                    print(f"  Value: {data.get('value', 'N/A')} {data.get('unit', '')}")
                    print(f"  Timestamp: {data.get('timestamp', 'N/A')}")
                    print("=" * 60 + "\n")
                except json.JSONDecodeError:
                    print("\n" + "=" * 60)
                    print("WEBHOOK POST REQUEST RECEIVED (Non-JSON)")
                    print("=" * 60)
                    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"Path: {self.path}")
                    print(f"Client: {self.client_address[0]}:{self.client_address[1]}")
                    print("\nRaw Body:")
                    print(body.decode('utf-8', errors='ignore'))
                    print("=" * 60 + "\n")
            else:
                print("\n" + "=" * 60)
                print("WEBHOOK POST REQUEST RECEIVED (Empty Body)")
                print("=" * 60)
                print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Path: {self.path}")
                print(f"Client: {self.client_address[0]}:{self.client_address[1]}")
                print("=" * 60 + "\n")
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "status": "success",
                "message": "Webhook received",
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            print(f"Error handling POST request: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                "status": "error",
                "message": str(e)
            }
            self.wfile.write(json.dumps(error_response).encode('utf-8'))
    
    def do_GET(self):
        """Handle GET requests - show server info and webhook data"""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        
        # Generate webhook data HTML
        webhook_list_html = ""
        if webhook_data:
            for i, record in enumerate(webhook_data):
                data = record['data']
                received_at = datetime.fromisoformat(record['received_at']).strftime('%Y-%m-%d %H:%M:%S')
                webhook_list_html += f"""
                <div class="webhook-item">
                    <div class="webhook-header">
                        <span class="webhook-number">#{len(webhook_data) - i}</span>
                        <span class="webhook-time">{received_at}</span>
                    </div>
                    <div class="webhook-details">
                        <div class="detail-row">
                            <span class="label">Event Type:</span>
                            <span class="value">{data.get('event_type', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Sensor ID:</span>
                            <span class="value">{data.get('sensor_id', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Sensor Name:</span>
                            <span class="value">{data.get('sensor_name', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Alarm Type:</span>
                            <span class="value alarm-type">{data.get('alarm_type', 'N/A')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Value:</span>
                            <span class="value">{data.get('value', 'N/A')} {data.get('unit', '')}</span>
                        </div>
                        <div class="detail-row">
                            <span class="label">Timestamp:</span>
                            <span class="value">{data.get('timestamp', 'N/A')}</span>
                        </div>
                        <details class="json-details">
                            <summary>View JSON</summary>
                            <pre class="json-content">{json.dumps(data, indent=2, ensure_ascii=False)}</pre>
                        </details>
                    </div>
                </div>
                """
        else:
            webhook_list_html = '<div class="no-data">No webhook requests received yet. Send a test request to see data here.</div>'
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Webhook Test Server</title>
            <meta http-equiv="refresh" content="5">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); max-width: 1200px; margin: 0 auto; }}
                h1 {{ color: #333; margin-top: 0; }}
                .info {{ background: #e3f2fd; padding: 15px; border-radius: 4px; margin: 20px 0; }}
                code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }}
                .webhook-list {{ margin-top: 30px; }}
                .webhook-item {{ background: #f9f9f9; border: 1px solid #ddd; border-radius: 4px; padding: 15px; margin-bottom: 15px; }}
                .webhook-header {{ display: flex; justify-content: space-between; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid #ddd; }}
                .webhook-number {{ font-weight: bold; color: #2196F3; }}
                .webhook-time {{ color: #666; font-size: 0.9em; }}
                .webhook-details {{ margin-top: 10px; }}
                .detail-row {{ display: flex; margin: 8px 0; }}
                .label {{ font-weight: bold; width: 120px; color: #555; }}
                .value {{ color: #333; }}
                .alarm-type {{ color: #d32f2f; font-weight: bold; }}
                .json-details {{ margin-top: 10px; }}
                .json-details summary {{ cursor: pointer; color: #2196F3; font-weight: bold; }}
                .json-content {{ background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 0.85em; }}
                .no-data {{ text-align: center; padding: 40px; color: #999; }}
                .count-badge {{ background: #4CAF50; color: white; padding: 5px 10px; border-radius: 12px; font-size: 0.9em; margin-left: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Webhook Test Server</h1>
                <div class="info">
                    <p><strong>Status:</strong> Running</p>
                    <p><strong>Endpoint:</strong> <code>POST /webhook</code></p>
                    <p><strong>Port:</strong> <code>3000</code></p>
                    <p><strong>URL:</strong> <code>http://localhost:3000/webhook</code></p>
                    <p><strong>Total Requests:</strong> <span class="count-badge">{len(webhook_data)}</span></p>
                </div>
                <p>This server receives POST requests and displays the data below. Page auto-refreshes every 5 seconds.</p>
                <p>Configure your webhook URL in <code>config/config.json</code>:</p>
                <pre style="background: #f5f5f5; padding: 15px; border-radius: 4px;">"webhook_url": "http://localhost:3000/webhook"</pre>
                
                <div class="webhook-list">
                    <h2>Received Webhook Requests</h2>
                    {webhook_list_html}
                </div>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))


def main():
    """Start the webhook test server"""
    PORT = 3000
    
    print("=" * 60)
    print("Webhook Test Server")
    print("=" * 60)
    print(f"Starting server on http://localhost:{PORT}")
    print(f"Webhook endpoint: http://localhost:{PORT}/webhook")
    print("\nThe server will display all POST requests in this terminal.")
    print("Press Ctrl+C to stop the server.\n")
    print("=" * 60 + "\n")
    
    try:
        with socketserver.TCPServer(("", PORT), WebhookHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\nERROR: Port {PORT} is already in use!")
            print(f"   Another server might be running on port {PORT}")
            print(f"   Try using a different port or stop the other server")
        else:
            print(f"\nERROR: Error starting server: {e}")
    except Exception as e:
        print(f"\nERROR: {e}")


if __name__ == "__main__":
    main()

