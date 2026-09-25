// Связь с сервером по WebSocket — постоянный канал в обе стороны.
// Если сервер перезапустили, переподключаемся сами.

export class Net {
  constructor() {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    this.url = `${protocol}://${location.host}/ws`;
    this.stateListeners = new Set();
    this.statusListeners = new Set();
    this.connected = false;
    this.connect();
  }

  connect() {
    this.socket = new WebSocket(this.url);
    this.socket.onopen = () => this.setConnected(true);
    this.socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'state') this.stateListeners.forEach((fn) => fn(message));
    };
    this.socket.onclose = () => {
      this.setConnected(false);
      setTimeout(() => this.connect(), 1500);
    };
  }

  setConnected(value) {
    this.connected = value;
    this.statusListeners.forEach((fn) => fn(value));
  }

  send(message) {
    if (this.connected) this.socket.send(JSON.stringify(message));
  }

  // Подписки возвращают функцию отписки — её вызывают, когда сцена закрывается.
  onState(fn) {
    this.stateListeners.add(fn);
    return () => this.stateListeners.delete(fn);
  }

  onStatus(fn) {
    this.statusListeners.add(fn);
    fn(this.connected);
    return () => this.statusListeners.delete(fn);
  }
}
