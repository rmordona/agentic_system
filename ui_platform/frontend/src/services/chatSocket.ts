// src/services/chatSocket.ts

export type ChatSocketMessage = {
  type: string;
  event?: any;
  content?: string;
  error?: string;
};

export class ChatSocket {
  private socket: WebSocket | null = null;
  private threadId: string;
  private token: string;

  constructor(threadId: string, token: string) {
    this.threadId = threadId;
    this.token = token;
  }

  connect(onMessage: (data: ChatSocketMessage) => void) {
    this.socket = new WebSocket(
      `ws://localhost:8000/api/v1/ws/${this.threadId}?token=${this.token}`
    );

    this.socket.onopen = () => {
      console.log("WS connected");
    };

    this.socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    this.socket.onerror = (err) => {
      console.error("WS error:", err);
    };

    this.socket.onclose = (event) => {
      console.log("WS closed", event.code);

      if (event.code === 1011) {
        onMessage({
          type: "internal_error",
          error: "An internal server error occurred.",
        });
      }

      if (event.code === 1006) {
        onMessage({
          type: "connection_lost",
          error: "Connection lost unexpectedly.",
        });
      }
    };


  }

  send(payload: any) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.warn("WebSocket not ready");
      return;
    }

    this.socket.send(JSON.stringify(payload));
  }

  close() {
    this.socket?.close();
  }
}