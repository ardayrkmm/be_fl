import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'dart:async';

class PoseWebSocketService {
  late IO.Socket _socket;
  final _messageController = StreamController<Map<String, dynamic>>.broadcast();

  // Expose stream for BLoC to listen
  Stream<Map<String, dynamic>> get messages => _messageController.stream;

  // Connection status getter
  bool get isConnected => _socket.connected;

  Future<void> connect([String? url]) async {
    // Default URL or passed URL
    final targetUrl = url ?? 'http://192.168.1.5:5000'; 
    
    _socket = IO.io(
      targetUrl,
      IO.OptionBuilder()
          .setTransports(['websocket'])
          .enableAutoConnect()
          .build(),
    );

    _socket.connect();

    _socket.onConnect((_) {
      print('✅ WebSocket Connected to $targetUrl');
    });

    _socket.onDisconnect((_) {
      print('❌ WebSocket Disconnected');
    });

    _socket.on('inference_result', (data) {
      if (data is Map) {
        _messageController.add(Map<String, dynamic>.from(data));
      }
    });
  }

  void sendPoseData(List<double> landmarks) {
    if (_socket.connected) {
      _socket.emit(
        'send_pose_data',
        {
          'landmarks': landmarks,
        },
      );
    }
  }

  void disconnect() {
    _socket.disconnect();
  }

  void dispose() {
    _socket.dispose();
    _messageController.close();
  }
}
