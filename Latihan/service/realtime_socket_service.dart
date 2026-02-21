

import 'dart:async';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:flutter/foundation.dart';

class RealtimeSocketService {
  IO.Socket? _socket;
  final _messageController = StreamController<Map<String, dynamic>>.broadcast();
  final _summaryController = StreamController<Map<String, dynamic>>.broadcast();

  Stream<Map<String, dynamic>> get messages => _messageController.stream;
  Stream<Map<String, dynamic>> get summaryStream => _summaryController.stream;

  // Replace with your backend IP
  static const String _baseUrl = 'http://192.168.1.5:5000';

  bool get isConnected => _socket?.connected ?? false;

  void connect() {
    if (_socket != null && _socket!.connected) return;

    debugPrint('🔌 Connecting to $_baseUrl using Socket.IO');

    // Create Socket Instance
    _socket = IO.io(
      _baseUrl,
      IO.OptionBuilder()
          .setTransports(['websocket']) // Force WebSocket
          .disableAutoConnect() // Connect manually
          .build(),
    );

    // --- Events ---
    _socket!.onConnect((_) {
      debugPrint('✅ Socket.IO Connected');
    });

    _socket!.onDisconnect((_) {
      debugPrint('⚠️ Socket.IO Disconnected');
    });

    _socket!.onConnectError((data) {
      debugPrint('❌ Socket.IO Connect Error: $data');
    });
    
    _socket!.onError((data) {
       debugPrint('❌ Socket.IO Error: $data');
    });

    // Listen for Inference Results
    _socket!.on('inference_result', (data) {
      try {
        if (data is Map<String, dynamic>) {
          _messageController.add(data);
        } else if (data is String) {
             // Handle if data comes as string (shouldn't with socket.io usually)
             debugPrint("⚠️ Received String instead of Map: $data");
        }
      } catch (e) {
        debugPrint('❌ Parse Error in inference_result: $e');
      }
    });

    // Listen for Exercise Summary
    _socket!.on('exercise_summary', (data) {
      try {
        if (data is Map<String, dynamic>) {
          debugPrint("📊 [SOCKET] Received Summary: $data");
          _summaryController.add(data);
        }
      } catch (e) {
        debugPrint('❌ Parse Error in exercise_summary: $e');
      }
    });
    
    _socket!.connect();
  }


  void sendPoseData(List<double> normalizedLandmarks) {
    if (_socket == null || !_socket!.connected) return;

    final payload = {
      'landmarks': normalizedLandmarks,
      // 'timestamp': DateTime.now().millisecondsSinceEpoch // Optional if backend needs it
    };
    
    // Emit event directly using Socket.IO
    _socket!.emit('send_pose_data', payload);
  }

  void startSession(String idLatihan, {String? sisi}) {
    if (_socket == null || !_socket!.connected) return;
    _socket!.emit('start_session', {
      'id_latihan': idLatihan,
      'sisi': sisi
    });
    debugPrint("🚀 [SOCKET] Session started for: $idLatihan (Sisi: $sisi)");
  }

  void endExercise() {
    if (_socket == null || !_socket!.connected) return;
    _socket!.emit('end_exercise');
    debugPrint("🏁 [SOCKET] End Exercise emitted");
  }

  void disconnect() {
    _socket?.disconnect();
  }

  void dispose() {
    disconnect();
    _messageController.close();
    _summaryController.close();
    _socket?.dispose();
  }
}
