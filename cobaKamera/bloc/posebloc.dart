import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'dart:async';

import 'poseEvent_bloc.dart';
import 'posestate.dart';
import '../service/pose_service.dart';
import '../service/pose_websocket_service.dart';
import '../service/realtime_pose_detector.dart';

class PoseBloc extends Bloc<PoseEvent, PoseState> {
  final PoseService poseService;
  final PoseWebSocketService ws;
  final RealtimePoseDetector detector = RealtimePoseDetector();

  CameraDescription? _cameraDescription;

  PoseBloc(this.poseService, this.ws) : super(PoseState()) {
    on<StartCamera>(_onStartCamera);
    on<StopCamera>(_onStopCamera);
    on<OnPoseDetected>(_onPoseDetected);
    on<OnInferenceResultReceived>(_onInference);

    _initWS();
  }

  /// ============================
  /// WEBSOCKET
  /// ============================
  StreamSubscription? _socketSubscription;

  void _initWS() {
    ws.connect('http://192.168.1.3:5000');
    
    _socketSubscription = ws.messages.listen((data) {
      add(OnInferenceResultReceived(
        data['label'],
        (data['confidence'] as num).toDouble(),
        data['feedback'],
        Color(
          int.parse(data['color'].replaceAll('#', ''), radix: 16) +
              0xFF000000,
        ),
      ));
    });
  }

  @override
  Future<void> close() async {
    await detector.stop();
    await _socketSubscription?.cancel();
    ws.dispose();
    await poseService.dispose();
    return super.close();
  }

  /// ============================
  /// START CAMERA
  /// ============================
  Future<void> _onStartCamera(
    StartCamera e,
    Emitter<PoseState> emit,
  ) async {
    final CameraController controller =
        await poseService.initCamera();

    _cameraDescription = controller.description;

    emit(state.copyWith(
      camera: controller,
      isRunning: true,
    ));

    /// 🔥 HUBUNGKAN DETECTOR → BLOC
    detector.start(
      controller,
      _cameraDescription!,
      (pose, imageSize, rotation) { // rotation is now InputImageRotation
        final normalized =
            poseService.normalizePose(pose);

        add(OnPoseDetected(
          pose: pose,
          imageSize: imageSize,
          normalizedLandmarks: normalized,
          rotation: rotation,
          
        ));
      },
    );
  }

  /// ============================
  /// STOP CAMERA
  /// ============================
  Future<void> _onStopCamera(
    StopCamera e,
    Emitter<PoseState> emit,
  ) async {
    await detector.stop();
    await poseService.dispose();

    emit(state.copyWith(
      camera: null,
      isRunning: false,
      pose: null,
    ));
  }

  /// ============================
  /// POSE DETECTED
  /// ============================
  void _onPoseDetected(
    OnPoseDetected e,
    Emitter<PoseState> emit,
  ) {
    emit(state.copyWith(
      pose: e.pose,
      imageSize: e.imageSize,
    ));

    ws.sendPoseData(e.normalizedLandmarks);
  }

  /// ============================
  /// INFERENCE RESULT
  /// ============================
  void _onInference(
    OnInferenceResultReceived e,
    Emitter<PoseState> emit,
  ) {
    emit(state.copyWith(
      predictedLabel: e.label,
      confidence: e.confidence,
      feedback: e.feedback,
      feedbackColor: e.feedbackColor,
    ));
  }

}

