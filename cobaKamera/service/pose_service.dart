import 'dart:io';
import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';

class PoseService {
  final PoseDetector _poseDetector =
      PoseDetector(options: PoseDetectorOptions());

  Future<void> initialize() async {}

  Future<void> close() async {
    await _poseDetector.close();
  }

  // ============================
  // 🔥 FIXED ROTATION HANDLING
  // ============================

  InputImageRotation _getImageRotation(CameraDescription camera) {
    final sensorOrientation = camera.sensorOrientation;

    switch (sensorOrientation) {
      case 90:
        return InputImageRotation.rotation90deg;
      case 180:
        return InputImageRotation.rotation180deg;
      case 270:
        return InputImageRotation.rotation270deg;
      case 0:
      default:
        return InputImageRotation.rotation0deg;
    }
  }

  InputImage? processCameraImage(
      CameraImage image, CameraDescription camera) {
    try {
      final WriteBuffer allBytes = WriteBuffer();

      for (final Plane plane in image.planes) {
        allBytes.putUint8List(plane.bytes);
      }

      final bytes = allBytes.done().buffer.asUint8List();

      final Size imageSize =
          Size(image.width.toDouble(), image.height.toDouble());

      final rotation = _getImageRotation(camera);

      final format =
          InputImageFormatValue.fromRawValue(image.format.raw) ??
              InputImageFormat.nv21;

      final metadata = InputImageMetadata(
        size: imageSize,
        rotation: rotation,
        format: format,
        bytesPerRow: image.planes.first.bytesPerRow,
      );

      return InputImage.fromBytes(
        bytes: bytes,
        metadata: metadata,
      );
    } catch (e) {
      debugPrint("❌ Error converting image: $e");
      return null;
    }
  }

  Future<Map<String, dynamic>?> detectPose(
      InputImage inputImage) async {
    try {
      final poses = await _poseDetector.processImage(inputImage);
      if (poses.isEmpty) return null;

      final pose = poses.first;

      return {
        'pose': pose,
        'normalizedLandmarks': _extractLandmarks(pose),
      };
    } catch (e) {
      debugPrint("❌ Pose detection error: $e");
      return null;
    }
  }

  List<double> _extractLandmarks(Pose pose) {
    final landmarks = <double>[];

    for (final type in PoseLandmarkType.values) {
      final landmark = pose.landmarks[type];

      if (landmark != null) {
        landmarks.add(landmark.x);
        landmarks.add(landmark.y);
        landmarks.add(landmark.z);
        landmarks.add(landmark.likelihood);
      } else {
        landmarks.addAll([0.0, 0.0, 0.0, 0.0]);
      }
    }

    return landmarks;
  }
}
