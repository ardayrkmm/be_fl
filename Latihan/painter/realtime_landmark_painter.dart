import 'package:flutter/material.dart';
import 'dart:io';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';

class RealtimeLandmarkPainter extends CustomPainter {
  final Pose pose;
  final Size imageSize;
  final Size canvasSize;
  final InputImageRotation rotation;
  final bool isFrontCamera;

  RealtimeLandmarkPainter({
    required this.pose,
    required this.imageSize,
    required this.canvasSize,
    required this.rotation,
    required this.isFrontCamera,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paintLine = Paint()
      ..color = Colors.green
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke;

    final paintPoint = Paint()
      ..color = Colors.red
      ..style = PaintingStyle.fill;

    // Define connections (bones)
    final List<(PoseLandmarkType, PoseLandmarkType)> connections = [
      (PoseLandmarkType.nose, PoseLandmarkType.leftEye),
      (PoseLandmarkType.leftEye, PoseLandmarkType.leftEar),
      (PoseLandmarkType.nose, PoseLandmarkType.rightEye),
      (PoseLandmarkType.rightEye, PoseLandmarkType.rightEar),
      (PoseLandmarkType.leftShoulder, PoseLandmarkType.rightShoulder),
      (PoseLandmarkType.leftShoulder, PoseLandmarkType.leftElbow),
      (PoseLandmarkType.leftElbow, PoseLandmarkType.leftWrist),
      (PoseLandmarkType.rightShoulder, PoseLandmarkType.rightElbow),
      (PoseLandmarkType.rightElbow, PoseLandmarkType.rightWrist),
      (PoseLandmarkType.leftShoulder, PoseLandmarkType.leftHip),
      (PoseLandmarkType.rightShoulder, PoseLandmarkType.rightHip),
      (PoseLandmarkType.leftHip, PoseLandmarkType.rightHip),
      (PoseLandmarkType.leftHip, PoseLandmarkType.leftKnee),
      (PoseLandmarkType.leftKnee, PoseLandmarkType.leftAnkle),
      (PoseLandmarkType.rightHip, PoseLandmarkType.rightKnee),
      (PoseLandmarkType.rightKnee, PoseLandmarkType.rightAnkle),
    ];

    // 1. Draw Lines First
    for (final connection in connections) {
      final startLandmark = pose.landmarks[connection.$1];
      final endLandmark = pose.landmarks[connection.$2];

      if (startLandmark != null && endLandmark != null) {
        // Use ML Kit Commons built-in translation functions
        // translateX/Y handles the rotation mapping from buffer to canvas
        double x1 = translateX(
          startLandmark.x,
          rotation,
          size,
          imageSize,
        );
        double y1 = translateY(
          startLandmark.y,
          rotation,
          size,
          imageSize,
        );

        double x2 = translateX(
          endLandmark.x,
          rotation,
          size,
          imageSize,
        );
        double y2 = translateY(
          endLandmark.y,
          rotation,
          size,
          imageSize,
        );

        // Handle Front Camera Mirroring Mathematically
        if (isFrontCamera) {
          x1 = size.width - x1;
          x2 = size.width - x2;
        }

        canvas.drawLine(Offset(x1, y1), Offset(x2, y2), paintLine);
      }
    }

    // 2. Draw Points on Top
    for (final landmark in pose.landmarks.values) {
      // Draw all landmarks or filter by likelihood if needed
      // ML Kit Commons usually handles likelihood check internally or we do it here
      // Assuming we draw all valid landmarks
      
      double x = translateX(
        landmark.x,
        rotation,
        size,
        imageSize,
      );
      double y = translateY(
        landmark.y,
        rotation,
        size,
        imageSize,
      );

      // Handle Front Camera Mirroring
      if (isFrontCamera) {
        x = size.width - x;
      }

      // Draw with reduced radius of 2.5
      canvas.drawCircle(Offset(x, y), 2.5, paintPoint);
    }
  }

  @override
  bool shouldRepaint(covariant RealtimeLandmarkPainter oldDelegate) {
    return oldDelegate.pose != pose ||
        oldDelegate.imageSize != imageSize ||
        oldDelegate.rotation != rotation ||
        oldDelegate.isFrontCamera != isFrontCamera;
  }
}

double translateX(double x, InputImageRotation rotation, Size size, Size absoluteImageSize) {
  switch (rotation) {
    case InputImageRotation.rotation90deg:
      return x * size.width / (Platform.isIOS ? absoluteImageSize.width : absoluteImageSize.height);
    case InputImageRotation.rotation270deg:
      return size.width - x * size.width / (Platform.isIOS ? absoluteImageSize.width : absoluteImageSize.height);
    default:
      return x * size.width / absoluteImageSize.width;
  }
}

double translateY(double y, InputImageRotation rotation, Size size, Size absoluteImageSize) {
  switch (rotation) {
    case InputImageRotation.rotation90deg:
    case InputImageRotation.rotation270deg:
      return y * size.height / (Platform.isIOS ? absoluteImageSize.height : absoluteImageSize.width);
    default:
      return y * size.height / absoluteImageSize.height;
  }
}
