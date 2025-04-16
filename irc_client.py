import argparse
import irc.client
import irc.connection
import ssl

message_buffer = []

def connect_to_irc(server, port, password):
    """Connect to an IRC server and print messages as they arrive."""
    def on_connect(connection, event):
        print(f"Connected: {event}")

    def on_disconnect(connection, event):
        print(f"Disconnected: {event}")

    def on_message(connection, event):
        print(f"Message: {event}")

        if event.target == "#arrakis":
            sender = event.source.split("!")[0]  # Extract the sender's nickname
            message = event.arguments[0]  # Extract the message text
            message_buffer.append({"sender": sender, "message": message})

    client = irc.client.Reactor()
    try:
        ssl_context = ssl.create_default_context()
        ssl_factory = irc.connection.Factory(wrapper=lambda sock: ssl_context.wrap_socket(sock, server_hostname=server))
        connection = client.server().connect(server, port, "luv", password=password, connect_factory=ssl_factory)
        connection.add_global_handler("welcome", on_connect)
        connection.add_global_handler("disconnect", on_disconnect)
        connection.add_global_handler("pubmsg", on_message)
        client.process_forever()
    except irc.client.ServerConnectionError as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect to an IRC server and print messages.")
    parser.add_argument("password", help="The password for the IRC server.")
    args = parser.parse_args()

    SERVER = "bnc.irccloud.com"
    PORT = 6697

    connect_to_irc(SERVER, PORT, args.password)
