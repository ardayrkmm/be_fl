import 'dart:io';
import 'dart:typed_data';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart'; // 🔥 Tambahkan ini untuk DeviceOrientation
import 'package:google_mlkit_pose_detection/google_mlkit_pose_detection.dart';

import 'package:google_mlkit_commons/google_mlkit_commons.dart'; // Add this import

class RealtimePoseDetector {
  final PoseDetector _poseDetector = PoseDetector(
    options: PoseDetectorOptions(
      mode: PoseDetectionMode.stream,
    ),
  );

  bool _isProcessing = false;
  bool _isRunning = false;

  /// ============================
  /// START STREAM
  /// ============================
  void start(
    CameraController controller,
    CameraDescription description,
    void Function(Pose pose, Size imageSize, InputImageRotation rotation) onPose, // Changed int to InputImageRotation
  ) {
    if (_isRunning) return;
    _isRunning = true;

    controller.startImageStream((CameraImage image) async {
      if (_isProcessing) return;
      _isProcessing = true;

      try {
        // 🔥 Kirim controller ke fungsi konversi untuk baca orientasi HP
        final inputImage = _cameraImageToInputImage(image, description, controller);

        if (inputImage == null) {
          _isProcessing = false;
          return;
        }

        final poses = await _poseDetector.processImage(inputImage);

        if (poses.isNotEmpty) {
          // 🔥 Dapatkan rotasi aktual yang dipakai ML Kit
          final InputImageRotation rotation = inputImage.metadata?.rotation ?? InputImageRotation.rotation0deg;
          final int rotationVal = rotation.rawValue;
          
          // 🔥 Penyesuaian Size: Jika Landscape (90/270), Tukar Lebar dan Tinggi
          final bool isLandscape = rotationVal == 90 || rotationVal == 270;
          final size = isLandscape 
              ? Size(image.height.toDouble(), image.width.toDouble()) 
              : Size(image.width.toDouble(), image.height.toDouble());

          onPose(poses.first, size, rotation);
        }
      } catch (e) {
        debugPrint('❌ Pose detection error: $e');
      } finally {
        _isProcessing = false;
      }
    });
  }

  /// ============================
  /// STOP STREAM
  /// ============================
  Future<void> stop() async {
    if (!_isRunning) return;
    _isRunning = false;
    await _poseDetector.close();
  }

  /// ============================
  /// CAMERA → INPUT IMAGE (DYNAMIC ROTATION)
  /// ============================
  InputImage? _cameraImageToInputImage(
      CameraImage image, 
      CameraDescription description, 
      CameraController controller) {
    try {
      final WriteBuffer allBytes = WriteBuffer();
      for (final Plane plane in image.planes) {
        allBytes.putUint8List(plane.bytes);
      }
      final bytes = allBytes.done().buffer.asUint8List();

      // 🔥 1. LOGIKA ANTI-GRAVITY: Hitung Rotasi Aktual
      final sensorOrientation = description.sensorOrientation;
      int deviceOffset = 0;
      switch (controller.value.deviceOrientation) {
        case DeviceOrientation.portraitUp: deviceOffset = 0; break;
        case DeviceOrientation.landscapeLeft: deviceOffset = 90; break;
        case DeviceOrientation.portraitDown: deviceOffset = 180; break;
        case DeviceOrientation.landscapeRight: deviceOffset = 270; break;
      }

      int finalRotation;
      if (description.lensDirection == CameraLensDirection.front) {
        finalRotation = (sensorOrientation + deviceOffset) % 360;
      } else {
        finalRotation = (sensorOrientation - deviceOffset + 360) % 360;
      }

      final rotation = InputImageRotationValue.fromRawValue(finalRotation) 
          ?? InputImageRotation.rotation0deg;

      // 2. Deteksi Format
      final format = Platform.isAndroid 
          ? InputImageFormat.nv21 
          : (InputImageFormatValue.fromRawValue(image.format.raw) ?? InputImageFormat.bgra8888);

      // 3. Build InputImageMetadata
      return InputImage.fromBytes(
        bytes: bytes,
        metadata: InputImageMetadata(
          size: Size(image.width.toDouble(), image.height.toDouble()),
          rotation: rotation, // 🔥 ML Kit sekarang tahu orientasi HP-nya
          format: format,
          bytesPerRow: image.planes.first.bytesPerRow,
        ),
      );
    } catch (e) {
      debugPrint("Error converting image: $e");
      return null;
    }
  }
}