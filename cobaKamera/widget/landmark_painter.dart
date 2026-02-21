import 'package:flutter/material.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';

class LandmarkPainter extends CustomPainter {
  final Pose? pose;
  final Size imageSize;
  final Size canvasSize; 
  final bool isFrontCamera;
  final InputImageRotation rotation;

  LandmarkPainter({
    required this.pose,
    required this.imageSize,
    required this.canvasSize,
    required this.isFrontCamera,
    required this.rotation,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (pose == null) return;

    final skeletonPaint = Paint()
      ..color = Colors.green
      ..strokeWidth = 3
      ..style = PaintingStyle.stroke;

    final pointPaint = Paint()
      ..color = Colors.red
      ..style = PaintingStyle.fill;

    // CENTER OF TRANSFORM (Single Source of Truth Logic)
    Offset transformPoint(double x, double y) {
      // 1. Normalize to 0..1 (Based on Buffer Size)
      double nx = x / imageSize.width;
      double ny = y / imageSize.height;

      // 2. Rotate in 0..1 space
      double rx, ry;
      switch (rotation) {
        case InputImageRotation.rotation90deg:
          // Rotate 90 CW
          rx = 1 - ny;
          ry = nx;
          break;
        case InputImageRotation.rotation180deg:
          rx = 1 - nx;
          ry = 1 - ny;
          break;
        case InputImageRotation.rotation270deg:
          // Rotate 270 CW (90 CCW)
          rx = ny;
          ry = 1 - nx;
          break;
        default:
          rx = nx;
          ry = ny;
          break;
      }

      // 3. Mirror (Horizontal Flip) if Front Camera
      // Mirroring happens AFTER rotation in the viewfinder space (canvas space)
      if (isFrontCamera) {
        rx = 1 - rx;
      }

      // 4. Scale to Canvas Size
      return Offset(rx * size.width, ry * size.height);
    }

    Offset getLandmarkOffset(PoseLandmark landmark) {
      return transformPoint(landmark.x, landmark.y);
    }

    final connections = [
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

    // DRAW SKELETON
    for (final c in connections) {
      final l1 = pose!.landmarks[c.$1];
      final l2 = pose!.landmarks[c.$2];

      if (l1 != null && l2 != null && l1.likelihood > 0.6 && l2.likelihood > 0.6) {
        canvas.drawLine(
            getLandmarkOffset(l1), getLandmarkOffset(l2), skeletonPaint);
      }
    }

    // DRAW LANDMARK POINTS
    for (final landmark in pose!.landmarks.values) {
      if (landmark.likelihood > 0.6) {
         canvas.drawCircle(getLandmarkOffset(landmark), 4, pointPaint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant LandmarkPainter oldDelegate) {
    return oldDelegate.pose != pose || 
           oldDelegate.imageSize != imageSize || 
           oldDelegate.rotation != rotation || 
           oldDelegate.canvasSize != canvasSize ||
           oldDelegate.isFrontCamera != isFrontCamera;
  }
}
