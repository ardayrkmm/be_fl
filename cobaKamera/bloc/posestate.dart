import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';

class PoseState {
  final CameraController? camera;
  final Pose? pose;
  final Size? imageSize;
  final InputImageRotation rotation; // Changed from int
  final String predictedLabel;
  final double confidence;
  final String feedback;
  final Color feedbackColor;

  final bool isRunning;

  PoseState({
    this.camera,
    this.pose,
    this.imageSize,
    this.rotation = InputImageRotation.rotation0deg,
    this.predictedLabel = "-",
    this.confidence = 0.0,
    this.feedback = "",
    this.feedbackColor = Colors.white,
    this.isRunning = false,
  });

  PoseState copyWith({
    CameraController? camera,
    Pose? pose,
    Size? imageSize,
    String? predictedLabel,
    double? confidence,
    String? feedback,
    Color? feedbackColor,
    bool? isRunning,
    InputImageRotation? rotation,
  }) {
    return PoseState(
      camera: camera ?? this.camera,
      pose: pose ?? this.pose,
      imageSize: imageSize ?? this.imageSize,
      predictedLabel: predictedLabel ?? this.predictedLabel,
      confidence: confidence ?? this.confidence,
      feedback: feedback ?? this.feedback,
      rotation: rotation ?? this.rotation,
      feedbackColor: feedbackColor ?? this.feedbackColor,
      isRunning: isRunning ?? this.isRunning,
    );
  }
}
