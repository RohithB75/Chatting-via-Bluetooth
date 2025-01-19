import socket
import sys
import threading

def receive_messages(client_socket):
    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                break
            message = data.decode('utf-8')
            print(f"Server: {message}")
            sys.stdout.flush()
        except Exception as e:
            print(f"Error receiving: {e}")
            break

def send_message(client_socket, message):
    try:
        client_socket.send(message.encode('utf-8'))
        print(f"You: {message}")
        sys.stdout.flush()
    except Exception as e:
        print(f"Error sending: {e}")

client = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
print("Connecting to server...")
client.connect(("A8:7E:EA:F6:52:A6", 6))
print("Connected to server!")

# Start receive thread
receive_thread = threading.Thread(target=receive_messages, args=(client,))
receive_thread.daemon = True
receive_thread.start()

try:
    while True:
        message = input()
        if message.lower() == 'quit':
            break
        send_message(client, message)
except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
    print("Connection closed")