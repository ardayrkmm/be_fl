import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';
import 'package:flutter/material.dart';
import 'package:meta/meta.dart';

@immutable
abstract class PoseEvent {
  const PoseEvent();
}

class StartCamera extends PoseEvent {
  const StartCamera();
}

class StopCamera extends PoseEvent {
  const StopCamera();
}

class OnPoseDetected extends PoseEvent {
  final Pose pose;
  final Size imageSize;
  final List<double> normalizedLandmarks;
  final InputImageRotation rotation;

  const OnPoseDetected({
    required this.pose,
    required this.imageSize,
    required this.normalizedLandmarks,
    required this.rotation,
  });
}

class OnInferenceResultReceived extends PoseEvent {
  final String label;
  final double confidence;
  final String feedback;
  final Color feedbackColor;

  const OnInferenceResultReceived(
    this.label,
    this.confidence,
    this.feedback,
    this.feedbackColor,
  );
}
