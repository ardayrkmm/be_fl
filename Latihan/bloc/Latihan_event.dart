import 'package:equatable/equatable.dart';
import 'package:flutter/material.dart';
import 'package:frontend_fisio/features/Models/JadwalModels.dart'; // Changed Import
import 'package:frontend_fisio/features/Models/pose_result.dart';
import 'package:google_mlkit_commons/google_mlkit_commons.dart';

abstract class ExerciseEvent extends Equatable {
  @override
  List<Object?> get props => [];
}

class InitCamera extends ExerciseEvent {
  final JadwalDetailModel latihanData; // Changed type
  final List<JadwalDetailModel> allExercises; // Changed type
  final int currentIndex;

  InitCamera({
    required this.latihanData,
    this.allExercises = const [],
    this.currentIndex = 0,
  });

  @override
  List<Object?> get props => [latihanData, allExercises, currentIndex];
}

class StartRest extends ExerciseEvent {}

class CompleteRest extends ExerciseEvent {}

class DisposeCamera extends ExerciseEvent {}

class NextExercise extends ExerciseEvent {}

class StartExercise extends ExerciseEvent {}

class PauseExercise extends ExerciseEvent {}

class ResumeExercise extends ExerciseEvent {}

class IncrementRepetition extends ExerciseEvent {}

class IncrementSet extends ExerciseEvent {}

class UpdateTimer extends ExerciseEvent {
  final double newTime;

  UpdateTimer({required this.newTime});

  @override
  List<Object?> get props => [newTime];
}

class CompleteExercise extends ExerciseEvent {}

class FailExercise extends ExerciseEvent {
  final String reason;

  FailExercise({required this.reason});

  @override
  List<Object?> get props => [reason];
}

class PoseDetected extends ExerciseEvent {
  final PoseResult poseResult;
  final Size imageSize;
  final InputImageRotation rotation;

  PoseDetected({
    required this.poseResult,
    required this.imageSize,
    required this.rotation,
  });

  @override
  List<Object?> get props => [poseResult, imageSize, rotation];
}

class TogglePoseDetection extends ExerciseEvent {}

class ToggleUI extends ExerciseEvent {}

// 🆕 Event to update data from WebSocket
class UpdateSocketData extends ExerciseEvent {
  final String predictedLabel;
  final double confidence;
  final String feedback;
  final Color feedbackColor;
  final bool isValid;

  UpdateSocketData({
    required this.predictedLabel,
    required this.confidence,
    required this.feedback,
    required this.feedbackColor,
    this.isValid = false,
  });

  @override
  List<Object?> get props => [predictedLabel, confidence, feedback, feedbackColor, isValid];
}

class FlipCamera extends ExerciseEvent {}

// 🆕 Event when exercise summary received from Socket
class SessionSummaryReceived extends ExerciseEvent {
  final int totalBenar;
  final int totalSalah;
  final double akurasi;

  SessionSummaryReceived({
    required this.totalBenar,
    required this.totalSalah,
    required this.akurasi,
  });

  @override
  List<Object?> get props => [totalBenar, totalSalah, akurasi];
}
