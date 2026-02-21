import 'dart:io';
import 'dart:ui';
import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';

class RealtimePoseService {
  final PoseDetector _poseDetector = PoseDetector(options: PoseDetectorOptions());

  Future<void> close() async {
    await _poseDetector.close();
  }

  // 🔥 7. RETURN STRUCTURE
  Future<Map<String, dynamic>?> detectPose(CameraImage image, int sensorOrientation, CameraLensDirection lensDirection) async {
    try {
      final InputImage? inputImage = _createInputImage(image, sensorOrientation, lensDirection);
      if (inputImage == null) return null;

      final List<Pose> poses = await _poseDetector.processImage(inputImage);
      if (poses.isEmpty) return null;

      final firstPose = poses.first;
      final imageSize = Size(image.width.toDouble(), image.height.toDouble());
      final landmarks = getNormalizedLandmarks(firstPose, imageSize);

      return {
        'pose': firstPose,
        'imageSize': Size(image.width.toDouble(), image.height.toDouble()),
        'landmarks': landmarks,
        'rotation': inputImage.metadata?.rotation ?? InputImageRotation.rotation0deg,
      };
    } catch (e) {
      debugPrint('Error detecting pose: $e');
      return null;
    }
  }

  InputImage? _createInputImage(CameraImage image, int sensorOrientation, CameraLensDirection lensDirection) {
    final WriteBuffer allBytes = WriteBuffer();
    for (final Plane plane in image.planes) {
      allBytes.putUint8List(plane.bytes);
    }
    final bytes = allBytes.done().buffer.asUint8List();

    final Size imageSize = Size(image.width.toDouble(), image.height.toDouble());

    // 🔥 2. ROTATION WAJIB BENAR (ANDROID) - Formula Resmi MLKit
    final InputImageRotation imageRotation =
        InputImageRotationValue.fromRawValue(sensorOrientation) ??
            InputImageRotation.rotation0deg;

    // 🔥 6. IMAGE FORMAT ANDROID WAJIB NV21
    final InputImageFormat inputImageFormat =
        InputImageFormatValue.fromRawValue(image.format.raw) ??
            InputImageFormat.nv21;

    final inputImageMetadata = InputImageMetadata(
      size: imageSize,
      rotation: imageRotation,
      format: inputImageFormat,
      bytesPerRow: image.planes[0].bytesPerRow,
    );

    return InputImage.fromBytes(bytes: bytes, metadata: inputImageMetadata);
  }


  
  List<double> getNormalizedLandmarks(Pose pose, Size imageSize) {
      final List<double> landmarks = [];
      for (final type in PoseLandmarkType.values) {
        final landmark = pose.landmarks[type];
        if (landmark != null) {
            landmarks.add(landmark.x / imageSize.width);
            landmarks.add(landmark.y / imageSize.height);
            landmarks.add(landmark.z); // Z is not easily normalized same way
            landmarks.add(landmark.likelihood);
        } else {
            landmarks.addAll([0.0, 0.0, 0.0, 0.0]);
        }
      }
      return landmarks;
  }
}
