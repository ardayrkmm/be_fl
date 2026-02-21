import 'package:camera/camera.dart';
import 'package:equatable/equatable.dart';
import 'package:flutter/material.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';
import 'package:frontend_fisio/features/Models/JadwalModels.dart'; // Changed Import
import 'package:frontend_fisio/features/Models/pose_result.dart';

enum ExerciseSession { initial, resting, mainExercise, completed }

class ExerciseHistoryItem {
  final DateTime timestamp;
  final String predictedLabel;
  final double confidence;
  final bool isCorrect;

  ExerciseHistoryItem({
    required this.timestamp,
    required this.predictedLabel,
    required this.confidence,
    required this.isCorrect,
  });
}

class ExerciseState extends Equatable {
  final CameraController? cameraController;
  final JadwalDetailModel? latihanData; // Changed type
  final List<JadwalDetailModel> allExercises; // Changed type
  final int currentIndex;
  final int repetition;
  final int set;
  final double timer;
  // ... other fields unchanged ...
  final bool isCameraReady;
  final bool isRunning;
  final bool isPaused;
  final String status;
  
  // Session Management
  final ExerciseSession session;
  final bool isUiVisible;
  
  // Pose & AI properties
  final PoseResult? poseResult;
  final bool isPoseDetectionEnabled;
  final String? poseError;
  
  // Feedback & Display
  final String predictedLabel;
  final String feedback;
  final Color feedbackColor;

  // Accuracy & History
  final double currentAccuracy;
  final double averageAccuracy;
  final List<ExerciseHistoryItem> history;
  final int correctPoseCount;
  final int totalPoseCount;
  
  // Camera control
  final int currentCameraIndex;
  
  // Detection status
  final String detectionStatus;

  // Image Size for Painter
  final Size? imageSize;
  final InputImageRotation rotation;

  final DateTime? startTime;
  final int socketCorrectCount;
  final int socketWrongCount;
  final bool isSocketValid;

  const ExerciseState({
    this.cameraController,
    this.latihanData,
    this.allExercises = const [],
    this.currentIndex = 0,
    this.repetition = 0,
    this.set = 0,
    this.timer = 0,
    this.isCameraReady = false,
    this.isRunning = false,
    this.isPaused = false,
    this.status = 'idle',
    this.session = ExerciseSession.initial,
    this.isUiVisible = true,
    this.poseResult,
    this.isPoseDetectionEnabled = true,
    this.poseError,
    this.predictedLabel = '',
    this.feedback = '',
    this.feedbackColor = Colors.white,
    this.currentAccuracy = 0.0,
    this.averageAccuracy = 0.0,
    this.history = const [],
    this.correctPoseCount = 0,
    this.totalPoseCount = 0,
    this.currentCameraIndex = 1,
    this.detectionStatus = 'idle',
    this.imageSize,
    this.rotation = InputImageRotation.rotation0deg,
    this.startTime,
    this.socketCorrectCount = 0,
    this.socketWrongCount = 0,
    this.isSocketValid = false,
  });

  ExerciseState copyWith({
    CameraController? cameraController,
    JadwalDetailModel? latihanData, // Changed type
    List<JadwalDetailModel>? allExercises, // Changed type
    int? currentIndex,
    int? repetition,
    int? set,
    double? timer,
    bool? isCameraReady,
    bool? isRunning,
    bool? isPaused,
    String? status,
    ExerciseSession? session,
    bool? isUiVisible,
    PoseResult? poseResult,
    bool? isPoseDetectionEnabled,
    String? poseError,
    String? predictedLabel,
    String? feedback,
    Color? feedbackColor,
    double? currentAccuracy,
    double? averageAccuracy,
    List<ExerciseHistoryItem>? history,
    int? correctPoseCount,
    int? totalPoseCount,
    int? currentCameraIndex,
    String? detectionStatus,
    Size? imageSize,
    InputImageRotation? rotation,
    DateTime? startTime,
    int? socketCorrectCount,
    int? socketWrongCount,
    bool? isSocketValid,
  }) {
    return ExerciseState(
      cameraController: cameraController ?? this.cameraController,
      latihanData: latihanData ?? this.latihanData,
      allExercises: allExercises ?? this.allExercises,
      currentIndex: currentIndex ?? this.currentIndex,
      repetition: repetition ?? this.repetition,
      set: set ?? this.set,
      timer: timer ?? this.timer,
      isCameraReady: isCameraReady ?? this.isCameraReady,
      isRunning: isRunning ?? this.isRunning,
      isPaused: isPaused ?? this.isPaused,
      status: status ?? this.status,
      session: session ?? this.session,
      isUiVisible: isUiVisible ?? this.isUiVisible,
      poseResult: poseResult ?? this.poseResult,
      isPoseDetectionEnabled: isPoseDetectionEnabled ?? this.isPoseDetectionEnabled,
      poseError: poseError ?? this.poseError,
      predictedLabel: predictedLabel ?? this.predictedLabel,
      feedback: feedback ?? this.feedback,
      feedbackColor: feedbackColor ?? this.feedbackColor,
      currentAccuracy: currentAccuracy ?? this.currentAccuracy,
      averageAccuracy: averageAccuracy ?? this.averageAccuracy,
      history: history ?? this.history,
      correctPoseCount: correctPoseCount ?? this.correctPoseCount,
      totalPoseCount: totalPoseCount ?? this.totalPoseCount,
      currentCameraIndex: currentCameraIndex ?? this.currentCameraIndex,
      detectionStatus: detectionStatus ?? this.detectionStatus,
      imageSize: imageSize ?? this.imageSize,
      rotation: rotation ?? this.rotation,
      startTime: startTime ?? this.startTime,
      socketCorrectCount: socketCorrectCount ?? this.socketCorrectCount,
      socketWrongCount: socketWrongCount ?? this.socketWrongCount,
      isSocketValid: isSocketValid ?? this.isSocketValid,
    );
  }

  @override
  List<Object?> get props => [
        cameraController,
        latihanData,
        allExercises,
        currentIndex,
        repetition,
        set,
        timer,
        isCameraReady,
        isRunning,
        isPaused,
        status,
        session,
        isUiVisible,
        poseResult,
        isPoseDetectionEnabled,
        poseError,
        predictedLabel,
        feedback,
        feedbackColor,
        currentAccuracy,
        averageAccuracy,
        history,
        correctPoseCount,
        totalPoseCount,
        currentCameraIndex,
        detectionStatus,
        imageSize,
        rotation,
        startTime,
        socketCorrectCount,
        socketWrongCount,
        isSocketValid,
      ];
}
